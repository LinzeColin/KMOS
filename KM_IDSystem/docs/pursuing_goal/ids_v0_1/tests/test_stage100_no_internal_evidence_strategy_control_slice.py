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
SCOPE = BASE / "STAGE100_PHASE2_NO_INTERNAL_EVIDENCE_STRATEGY_CONTROL_SLICE.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage100_no_internal_evidence_strategy_control_slice_contract.json"
)
MODULE = (
    BASE
    / "index_version_schema"
    / "stage100_no_internal_evidence_strategy_control_slice.py"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-100_无内部依据策略.md"
)
PHASE1_SCOPE = BASE / "STAGE100_PHASE1_NO_INTERNAL_EVIDENCE_STRATEGY_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = (
    BASE / "index_version_schema" / "stage100_no_internal_evidence_strategy_contract.json"
)
PHASE1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage100-p1-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE099_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage099_internal_evidence_external_augmentation_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage099-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage100-p2-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "stage100_no_internal_evidence_strategy_control_slice", MODULE
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Stage100 P2 control-slice module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage100NoInternalEvidenceStrategyPhase2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_module()
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.phase1_contract = json.loads(PHASE1_CONTRACT.read_text(encoding="utf-8"))
        cls.predecessor = json.loads(PREDECESSOR_CONTRACT.read_text(encoding="utf-8"))
        cls.control_input = cls.module.build_control_input()
        cls.result = cls.module.execute_no_internal_evidence_strategy_control_slice(
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

    def test_identity_authority_and_phase_boundary_are_exact(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage100.no_internal_evidence_strategy.phase2.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-100", contract["stage"])
        self.assertEqual("IDS-STAGE100-P2", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE100-P2", contract["task_id"])
        self.assertEqual("ACC-STAGE-100", contract["acceptance_id"])
        self.assertEqual(
            "PHASE2_NO_INTERNAL_EVIDENCE_STRATEGY_CONTROL_SLICE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE100-P2-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE100-P3-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE100_TASKPACK_STAGE100_PHASE1_AND_STAGE099_REVIEWED_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_CONTROL_ARTIFACTS_ONLY",
            source["authority"],
        )
        self.assertTrue(source["source_document_remains_authoritative"])
        self.assertTrue(source["business_line_whitebox_human_review_remains_authoritative"])
        for field, value in source.items():
            if field.endswith("_performed") or field.endswith("_allowed") or field.startswith(
                "second_"
            ) or field.endswith("can_replace_source_document"):
                with self.subTest(field=field):
                    self.assertFalse(value)
        predecessor = contract["predecessor_contract"]
        self.assertTrue(predecessor["stage099_review_required"])
        self.assertTrue(predecessor["stage100_phase1_required"])
        self.assertEqual(
            "PASS_REVIEWED_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_RUNTIME_DISABLED",
            predecessor["stage099_review_result"],
        )
        self.assertEqual(
            "PHASE1_NO_INTERNAL_EVIDENCE_STRATEGY_RUNTIME_DISABLED",
            predecessor["stage100_phase1_result"],
        )
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage099_review_evidence_declared",
            "stage100_started",
            "stage100_entry_authorized",
            "phase1_completed",
            "phase2_started",
            "phase2_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field, value in boundary.items():
            if field not in {
                "stage099_review_evidence_declared",
                "stage100_started",
                "stage100_entry_authorized",
                "phase1_completed",
                "phase2_started",
                "phase2_completed",
            }:
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_fixed_control_input_carries_required_reference_shapes(self):
        requests = self.control_input[self.module.CONTROL_FIELDS[0]]
        self.assertEqual(6, len(requests))
        self.assertEqual(
            set(self.module.CONTROL_SCENARIOS),
            {request["control_scenario"] for request in requests},
        )
        self.assertEqual(21, len(self.module.INPUT_FIELDS))
        for request in requests:
            with self.subTest(scenario=request["control_scenario"]):
                self.assertEqual(set(self.module.INPUT_FIELDS), set(request))
                for field, value in request.items():
                    if field == "control_scenario" or value is None:
                        continue
                    self.assertTrue(
                        value.startswith(":control:stage100-p2:")
                        or value.startswith("CONTROL_"),
                        field,
                    )
                for field in (
                    "query_ref",
                    "index_version_ref",
                    "prompt_version_ref",
                    "model_version_ref",
                    "selected_evidence_ref",
                    "no_internal_evidence_policy_ref",
                ):
                    self.assertTrue(request[field].startswith(":control:stage100-p2:"))
                self.assertTrue(
                    request["retrieval_document_instruction_precedence_state"].endswith(
                        "IDS_RULES_PREVAIL"
                    )
                )

    def test_accepted_control_slice_projects_exact_record_shape(self):
        result = self.result
        self.assertTrue(result["input_accepted"])
        self.assertEqual(
            "PASS_IN_MEMORY_NO_INTERNAL_EVIDENCE_STRATEGY_CONTROL_SLICE_RUNTIME_DISABLED",
            result["execution_state"],
        )
        self.assertIsNone(result["failure_state"])
        self.assertEqual(6, result["control_input_count"])
        self.assertEqual(4, result["control_projection_group_count"])
        self.assertEqual(38, result["control_projection_field_total_per_request"])
        self.assertEqual(228, result["control_projection_field_total"])
        for prefix, fields in self.module.PROJECTION_FIELDS:
            with self.subTest(prefix=prefix):
                projections = result[f"{prefix}_control_projections"]
                self.assertEqual(6, result[f"{prefix}_control_projection_count"])
                self.assertEqual(6, len(projections))
                for projection in projections:
                    self.assertEqual(set(fields), set(projection))

    def test_query_version_selected_evidence_and_no_internal_policy_remain_reference_only(self):
        requests = self.control_input[self.module.CONTROL_FIELDS[0]]
        bindings = self.result["answer_contract_and_policy_binding_control_projections"]
        records = self.result[
            "query_index_version_and_selected_evidence_record_control_projections"
        ]
        for request, binding, record in zip(requests, bindings, records):
            with self.subTest(scenario=request["control_scenario"]):
                self.assertEqual(
                    self.module.PHASE1_NO_INTERNAL_EVIDENCE_STRATEGY_CONTROL_REF,
                    binding[
                        "stage100_phase1_no_internal_evidence_strategy_contract_ref"
                    ],
                )
                self.assertEqual(
                    self.module.STAGE099_REVIEW_INTERNAL_EVIDENCE_EXTERNAL_AUGMENTATION_CONTROL_REF,
                    binding[
                        "stage099_review_internal_evidence_external_augmentation_control_ref"
                    ],
                )
                for field in (
                    "query_ref",
                    "index_version_ref",
                    "prompt_version_ref",
                    "model_version_ref",
                    "selected_evidence_ref",
                ):
                    self.assertEqual(request[field], record[field])
                self.assertEqual(
                    request["no_internal_evidence_policy_ref"],
                    binding["no_internal_evidence_policy_ref"],
                )
                self.assertEqual(
                    request["internal_evidence_insufficiency_state"],
                    binding["internal_evidence_insufficiency_state"],
                )
                self.assertEqual(
                    "CONTROL_QUERY_INDEX_PROMPT_MODEL_AND_SELECTED_EVIDENCE_RECORDS_REFERENCE_ONLY",
                    record["record_shape_state"],
                )

    def test_evidence_gap_and_external_augmentation_keep_source_types_separated(self):
        requests = self.control_input[self.module.CONTROL_FIELDS[0]]
        projections = self.result[
            "source_type_and_external_augmentation_opinion_display_control_projections"
        ]
        for request, projection in zip(requests, projections):
            with self.subTest(scenario=request["control_scenario"]):
                for field in (
                    "source_type_ref",
                    "source_type_separation_state",
                    "internal_evidence_ref",
                    "external_public_reference_ref",
                    "model_reasoning_ref",
                    "evidence_gap_ref",
                    "external_augmentation_ref",
                ):
                    self.assertEqual(request[field], projection[field])
                self.assertEqual("internal_evidence", projection["internal_evidence_source_type"])
                self.assertEqual(
                    "external_public_reference",
                    projection["external_public_reference_source_type"],
                )
                self.assertEqual("model_reasoning", projection["model_reasoning_source_type"])
                self.assertEqual("evidence_gap", projection["evidence_gap_source_type"])
                self.assertEqual(
                    "external_augmentation_opinion",
                    projection["external_augmentation_display_label"],
                )
                self.assertEqual(
                    "CONTROL_EXTERNAL_AUGMENTATION_OPINION_COMPOSED_FROM_EXTERNAL_PUBLIC_REFERENCE_AND_MODEL_REASONING",
                    projection["external_augmentation_display_state"],
                )
                self.assertEqual(
                    "CONTROL_EXTERNAL_AUGMENTATION_DOES_NOT_CLOSE_EVIDENCE_GAP",
                    projection[
                        "external_augmentation_does_not_close_evidence_gap_state"
                    ],
                )
        gap_index = self.module.CONTROL_SCENARIOS.index(
            "evidence_gap_with_external_augmentation_opinion_reference_only"
        )
        self.assertIsNone(requests[gap_index]["internal_evidence_ref"])
        self.assertIsNotNone(requests[gap_index]["evidence_gap_ref"])
        self.assertEqual(
            "CONTROL_INTERNAL_EVIDENCE_INSUFFICIENT_EVIDENCE_GAP_DECLARED",
            requests[gap_index]["internal_evidence_insufficiency_state"],
        )

    def test_prompt_injection_and_output_permissions_preserve_whitebox_gate(self):
        projections = self.result[
            "prompt_injection_and_output_permission_control_projections"
        ]
        for projection in projections:
            self.assertEqual(
                "CONTROL_RETRIEVAL_DOCUMENT_EVIDENCE_ONLY_IDS_RULES_PREVAIL",
                projection["retrieval_document_instruction_precedence_state"],
            )
            self.assertEqual(
                "CONTROL_FINAL_CONCLUSION_NOT_PUBLISHED",
                projection["final_conclusion_state"],
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
            "contract_commitment_confirmation_required_reference_only",
            "production_writeback_confirmation_required_reference_only",
        ):
            index = self.module.CONTROL_SCENARIOS.index(scenario)
            self.assertEqual(
                "CONTROL_HUMAN_WHITEBOX_CONFIRMATION_REQUIRED_NO_AUTO_FINALIZATION",
                projections[index]["output_permission_state"],
            )

    def test_nonfixed_control_input_produces_no_projection(self):
        invalid_input = copy.deepcopy(self.control_input)
        invalid_input[self.module.CONTROL_FIELDS[0]][0][
            "no_internal_evidence_policy_ref"
        ] = ":control:stage100-p2:altered:reference-only"
        invalid_input["unexpected"] = []
        rejected = self.module.execute_no_internal_evidence_strategy_control_slice(
            invalid_input
        )
        self.assertFalse(rejected["input_accepted"])
        self.assertEqual(
            "REJECTED_IN_MEMORY_NO_INTERNAL_EVIDENCE_STRATEGY_CONTROL_SLICE",
            rejected["execution_state"],
        )
        self.assertEqual("CONTROL_INPUT_MISMATCH", rejected["failure_state"])
        self.assertEqual(0, rejected["control_input_count"])
        self.assertEqual(0, rejected["control_projection_field_total"])
        for prefix, _fields in self.module.PROJECTION_FIELDS:
            self.assertEqual([], rejected[f"{prefix}_control_projections"])
            self.assertEqual(0, rejected[f"{prefix}_control_projection_count"])

    def test_runtime_boundary_failure_contract_and_local_code_remain_closed(self):
        self.assertFalse(self.result["persistent_record_created"])
        for field, value in self.result.items():
            if field.startswith("actual_") and field.endswith("_count"):
                with self.subTest(field=field):
                    self.assertEqual(0, value)
        self.assertEqual(
            set(self.module.RUNTIME_CLOSED_FIELDS),
            set(self.result["runtime_boundary"]),
        )
        for field, value in self.result["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)
        for section in ("runtime_boundary", "protected_surface_boundary"):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertFalse(value)
        local_code = self.contract["local_code"]
        self.assertTrue(local_code["control_slice_module_created"])
        self.assertTrue(local_code["control_slice_is_pure_memory"])
        for field, value in local_code.items():
            if field not in {"control_slice_module_created", "control_slice_is_pure_memory"}:
                with self.subTest(field=field):
                    self.assertFalse(value)
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(
            failures["failure_state_count"], len(failures["declared_failure_states"])
        )
        for state in (
            "CONTROL_INPUT_MISMATCH",
            "NO_INTERNAL_EVIDENCE_POLICY_REFERENCE_MISSING",
            "INTERNAL_EVIDENCE_INSUFFICIENCY_UNDECLARED",
            "EVIDENCE_GAP_RECLASSIFIED_AS_INTERNAL_EXPERIENCE",
            "EXTERNAL_AUGMENTATION_USED_TO_ERASE_EVIDENCE_GAP",
            "RETRIEVED_DOCUMENT_TREATED_AS_SYSTEM_INSTRUCTION",
            "PROMPT_INJECTION_DEFENSE_MISSING",
            "HIGH_RISK_ENGINEERING_ADVICE_AUTO_FINALIZED",
            "CONTRACT_COMMITMENT_AUTO_FINALIZED",
            "PRODUCTION_WRITEBACK_AUTO_FINALIZED",
        ):
            with self.subTest(state=state):
                self.assertIn(state, failures["declared_failure_states"])

    def test_scope_rollback_and_successor_governance_keep_phase3_gate_explicit(self):
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "reference-only",
            "21 个字段",
            "38 个投影字段",
            "external_augmentation_opinion",
            "提示注入",
            "业务线白箱人工确认",
            "模型 Token",
            "IDS-STAGE100-P3-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PHASE1_NO_INTERNAL_EVIDENCE_STRATEGY_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        for field in (
            "preserve_stage100_phase1_evidence",
            "preserve_stage099_review_evidence",
            "preserve_stage099_phase1_to_phase4_evidence",
        ):
            with self.subTest(field=field):
                self.assertTrue(rollback[field])
        for field in (
            "source_or_raw_data_change_allowed",
            "database_or_persistent_state_change_allowed",
            "github_or_ovh_change_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(rollback[field])

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        current = (status["stage"], status["phase"], status["task"], status["next_gate"])
        phase2_current = (
            "IDS-STAGE100",
            "IDS-STAGE100-P2",
            "IDS-V0_1-STAGE100-P2",
            "IDS-STAGE100-P3-GATE",
        )
        is_current_projection = assert_legacy_or_current_projection(
            self,
            current,
            {phase2_current},
            status,
            plan,
            ROADMAP,
        )
        self.assertEqual(status["task"], plan["task"])
        self.assertTrue(RECEIPT.is_file())
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        for acceptance_id in (
            "ACC-STAGE100-P2-01",
            "ACC-STAGE100-P2-02",
            "ACC-STAGE100-P2-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE100-P2-04"])
        self.assertIn("EVT-IDS-V0_1-STAGE100-P2-20260825-001", event_ids)
        self.assertEqual("IDS-STAGE100-P3-GATE", receipt["next_gate"])
        self.assertEqual(
            "PASS_NO_INTERNAL_EVIDENCE_STRATEGY_CONTROL_SLICE_RUNTIME_DISABLED",
            receipt["result"],
        )
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        self.assertTrue(all(value is False for value in receipt["runtime_flags"].values()))
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        self.assertIn("stage100_phase2_state:", roadmap_text)
        if current == phase2_current:
            self.assertFalse(is_current_projection)
            self.assertEqual("P2 纯内存控制切片已完成", acceptance_by_id["ACC-STAGE-100"])
            for phrase in (
                'current_phase_id: "IDS-STAGE100-P2"',
                'next_gate_id: "IDS-STAGE100-P3-GATE"',
                'stage_id: "IDS-STAGE100"',
            ):
                with self.subTest(phrase=phrase):
                    self.assertIn(phrase, roadmap_text)
        else:
            self.assertTrue(is_current_projection)


if __name__ == "__main__":
    unittest.main()
