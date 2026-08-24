import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE097_PHASE2_ANSWER_CONTRACT_CONTROL_SLICE.md"
CONTRACT = (
    BASE / "index_version_schema" / "stage097_answer_contract_control_slice_contract.json"
)
MODULE = BASE / "index_version_schema" / "stage097_answer_contract_control_slice.py"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-097_回答合同.md"
)
PHASE1_SCOPE = BASE / "STAGE097_PHASE1_ANSWER_CONTRACT_SCOPE_BOUNDARY.md"
PHASE1_CONTRACT = BASE / "index_version_schema" / "stage097_answer_contract.json"
PHASE1_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage097-p1-local.json"
PREDECESSOR_REVIEW = BASE / "STAGE096_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage096_knowledge_base_poisoning_defense_stage_review_contract.json"
)
PREDECESSOR_RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage096-review-local.json"
RECEIPT = ROOT / "machine" / "runs" / "2026-08-25-stage097-p2-local.json"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"


class Stage097AnswerContractPhase2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("stage097_answer_control_slice", MODULE)
        if spec is None or spec.loader is None:
            raise RuntimeError("无法加载 Stage097 P2 回答合同控制切片")
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.control_input = cls.module.build_control_input()
        cls.result = cls.module.execute_answer_contract_control_slice(cls.control_input)

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

    def test_identity_predecessors_and_phase_boundary_are_exact(self):
        contract = self.contract
        self.assertEqual("ids.stage097.answer_contract.phase2.v1", contract["schema_version"])
        self.assertEqual("STAGE-097", contract["stage"])
        self.assertEqual("IDS-STAGE097-P2", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE097-P2", contract["task_id"])
        self.assertEqual("ACC-STAGE-097", contract["acceptance_id"])
        self.assertEqual(
            "PHASE2_ANSWER_CONTRACT_CONTROL_SLICE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE097-P2-GATE", contract["entry_gate"])
        self.assertEqual("IDS-STAGE097-P3-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE097_TASKPACK_AND_STAGE097_PHASE1_STAGE096_REVIEWED_CONTROL_ARTIFACTS_ONLY",
            source["authority"],
        )
        for field, value in source.items():
            if field.endswith("_performed") or field.endswith("_allowed") or field.startswith(
                "second_"
            ):
                with self.subTest(field=field):
                    self.assertFalse(value)
        predecessor = contract["predecessor_contract"]
        self.assertTrue(predecessor["stage096_review_required"])
        self.assertTrue(predecessor["stage097_phase1_required"])
        self.assertEqual(
            "PASS_ANSWER_CONTRACT_RUNTIME_DISABLED",
            predecessor["stage097_phase1_result"],
        )
        boundary = contract["stage_and_phase_boundary"]
        for field in (
            "stage096_review_evidence_declared",
            "stage097_started",
            "stage097_entry_authorized",
            "phase1_completed",
            "phase2_started",
            "phase2_completed",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field, value in boundary.items():
            if field not in {
                "stage096_review_evidence_declared",
                "stage097_started",
                "stage097_entry_authorized",
                "phase1_completed",
                "phase2_started",
                "phase2_completed",
            }:
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_fixed_control_input_has_required_records_and_no_business_content(self):
        requests = self.control_input[self.module.CONTROL_FIELDS[0]]
        self.assertEqual(6, len(requests))
        self.assertEqual(set(self.module.CONTROL_SCENARIOS), {
            request["control_scenario"] for request in requests
        })
        self.assertEqual(20, len(self.module.INPUT_FIELDS))
        for request in requests:
            with self.subTest(scenario=request["control_scenario"]):
                self.assertEqual(set(self.module.INPUT_FIELDS), set(request))
                for field, value in request.items():
                    if field == "control_scenario" or value is None:
                        continue
                    self.assertTrue(
                        value.startswith(":control:stage097-p2:")
                        or value.startswith("CONTROL_"),
                        field,
                    )
                for field in (
                    "query_ref",
                    "index_version_ref",
                    "prompt_version_ref",
                    "model_version_ref",
                    "selected_evidence_ref",
                ):
                    self.assertTrue(request[field].startswith(":control:stage097-p2:"))
                self.assertTrue(
                    request["retrieval_document_instruction_precedence_state"].endswith(
                        "IDS_RULES_PREVAIL"
                    )
                )

    def test_accepted_control_slice_projects_exact_record_shape(self):
        result = self.result
        self.assertTrue(result["input_accepted"])
        self.assertEqual(
            "PASS_IN_MEMORY_ANSWER_CONTRACT_CONTROL_SLICE_RUNTIME_DISABLED",
            result["execution_state"],
        )
        self.assertIsNone(result["failure_state"])
        self.assertEqual(6, result["control_input_count"])
        self.assertEqual(4, result["control_projection_group_count"])
        self.assertEqual(35, result["control_projection_field_total_per_request"])
        self.assertEqual(210, result["control_projection_field_total"])
        for prefix, fields in self.module.PROJECTION_FIELDS:
            with self.subTest(prefix=prefix):
                projections = result[f"{prefix}_control_projections"]
                self.assertEqual(6, result[f"{prefix}_control_projection_count"])
                self.assertEqual(6, len(projections))
                for projection in projections:
                    self.assertEqual(set(fields), set(projection))

    def test_version_and_selected_evidence_records_remain_reference_only(self):
        requests = self.control_input[self.module.CONTROL_FIELDS[0]]
        bindings = self.result["answer_contract_binding_control_projections"]
        records = self.result[
            "version_and_selected_evidence_record_control_projections"
        ]
        for request, binding, record in zip(requests, bindings, records):
            with self.subTest(scenario=request["control_scenario"]):
                self.assertEqual(
                    self.module.PHASE1_ANSWER_CONTRACT_CONTROL_REF,
                    binding["stage097_phase1_answer_contract_ref"],
                )
                self.assertEqual(
                    self.module.STAGE096_REVIEW_CONTROL_REF,
                    binding["stage096_review_control_ref"],
                )
                for field in (
                    "query_ref",
                    "index_version_ref",
                    "prompt_version_ref",
                    "model_version_ref",
                    "selected_evidence_ref",
                ):
                    self.assertEqual(request[field], binding[field])
                    self.assertEqual(request[field], record[field])
                self.assertEqual(
                    "CONTROL_VERSION_AND_SELECTED_EVIDENCE_RECORDS_REFERENCE_ONLY",
                    record["record_shape_state"],
                )

    def test_source_types_remain_separated_when_external_augmentation_is_displayed(self):
        requests = self.control_input[self.module.CONTROL_FIELDS[0]]
        projections = self.result[
            "source_type_and_external_augmentation_display_control_projections"
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
                    "external_augmentation_display_ref",
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
                    "CONTROL_COMPOSED_FROM_EXTERNAL_PUBLIC_REFERENCE_AND_MODEL_REASONING",
                    projection["external_augmentation_display_state"],
                )
                self.assertEqual(
                    "CONTROL_DISPLAY_PRESERVES_BOTTOM_SOURCE_TYPES",
                    projection["display_does_not_replace_source_type_state"],
                )
        gap_index = self.module.CONTROL_SCENARIOS.index(
            "evidence_gap_with_external_augmentation_reference_only"
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
        invalid_input[self.module.CONTROL_FIELDS[0]][0]["prompt_version_ref"] = (
            ":control:stage097-p2:altered:reference-only"
        )
        invalid_input["unexpected"] = []
        rejected = self.module.execute_answer_contract_control_slice(invalid_input)
        self.assertFalse(rejected["input_accepted"])
        self.assertEqual(
            "REJECTED_IN_MEMORY_ANSWER_CONTRACT_CONTROL_SLICE",
            rejected["execution_state"],
        )
        self.assertEqual("CONTROL_INPUT_MISMATCH", rejected["failure_state"])
        self.assertEqual(0, rejected["control_input_count"])
        for prefix, _fields in self.module.PROJECTION_FIELDS:
            self.assertEqual([], rejected[f"{prefix}_control_projections"])
            self.assertEqual(0, rejected[f"{prefix}_control_projection_count"])

    def test_runtime_boundary_failure_contract_and_local_code_remain_closed(self):
        self.assertFalse(self.result["persistent_record_created"])
        for field, value in self.result.items():
            if field.startswith("actual_") and field.endswith("_count"):
                with self.subTest(field=field):
                    self.assertEqual(0, value)
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
            "QUERY_INDEX_PROMPT_MODEL_OR_SELECTED_EVIDENCE_REFERENCE_MISSING",
            "EXTERNAL_AUGMENTATION_DISPLAY_SOURCE_TYPE_LOST",
            "RETRIEVAL_DOCUMENT_TREATED_AS_SYSTEM_INSTRUCTION",
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
            "20 个字段",
            "35 个投影字段",
            "外部公开参考与模型推理",
            "提示注入",
            "业务线白箱人工确认",
            "模型 Token",
            "IDS-STAGE097-P3-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        rollback = self.contract["rollback_contract"]
        self.assertEqual("PHASE1_ANSWER_CONTRACT_RUNTIME_DISABLED", rollback["return_to"])
        for field in (
            "preserve_stage097_phase1_evidence",
            "preserve_stage096_review_evidence",
            "preserve_stage096_phase1_to_phase4_evidence",
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
            "IDS-STAGE097",
            "IDS-STAGE097-P2",
            "IDS-V0_1-STAGE097-P2",
            "IDS-STAGE097-P3-GATE",
        )
        phase3_current = (
            "IDS-STAGE097",
            "IDS-STAGE097-P3",
            "IDS-V0_1-STAGE097-P3",
            "IDS-STAGE097-P4-GATE",
        )
        phase4_current = (
            "IDS-STAGE097",
            "IDS-STAGE097-P4",
            "IDS-V0_1-STAGE097-P4",
            "IDS-STAGE097-REVIEW-GATE",
        )
        review_current = (
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
        stage098_phase2_current = (
            "IDS-STAGE098",
            "IDS-STAGE098-P2",
            "IDS-V0_1-STAGE098-P2",
            "IDS-STAGE098-P3-GATE",
        )
        stage098_phase3_current = (
            "IDS-STAGE098",
            "IDS-STAGE098-P3",
            "IDS-V0_1-STAGE098-P3",
            "IDS-STAGE098-P4-GATE",
        )
        self.assertIn(
            current,
            (
                phase2_current,
                phase3_current,
                phase4_current,
                review_current,
                stage098_phase1_current,
                stage098_phase2_current,
                stage098_phase3_current,
            ),
        )
        expected_task, expected_evidence_status, expected_acceptance_status = {
            phase2_current: (
                "IDS-V0_1-STAGE097-P2",
                "STAGE097_ANSWER_CONTRACT_CONTROL_SLICE_RUNTIME_DISABLED",
                "P2 受控最小切片已完成",
            ),
            phase3_current: (
                "IDS-V0_1-STAGE097-P3",
                "STAGE097_ANSWER_CONTRACT_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
                "P3 异常场景验证已完成",
            ),
            phase4_current: (
                "IDS-V0_1-STAGE097-P4",
                "STAGE097_ANSWER_CONTRACT_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
                "P4 交付证据已完成",
            ),
            review_current: (
                "IDS-V0_1-STAGE097-REVIEW",
                "STAGE097_ANSWER_CONTRACT_REVIEW_RUNTIME_DISABLED",
                "整阶段已复审",
            ),
            stage098_phase1_current: (
                "IDS-V0_1-STAGE098-P1",
                "STAGE098_PROMPT_VERSIONING_CONTRACT_RUNTIME_DISABLED",
                "整阶段已复审",
            ),
            stage098_phase2_current: (
                "IDS-V0_1-STAGE098-P2",
                "STAGE098_PROMPT_VERSIONING_CONTROL_SLICE_RUNTIME_DISABLED",
                "整阶段已复审",
            ),
            stage098_phase3_current: (
                "IDS-V0_1-STAGE098-P3",
                "STAGE098_PROMPT_VERSIONING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
                "整阶段已复审",
            ),
        }[current]
        self.assertEqual(expected_task, plan["task"])
        self.assertEqual(
            expected_evidence_status,
            status["evidence_status"],
        )
        acceptance_by_id = {item["id"]: item["status"] for item in acceptance["items"]}
        self.assertEqual(expected_acceptance_status, acceptance_by_id["ACC-STAGE-097"])
        for acceptance_id in (
            "ACC-STAGE097-P2-01",
            "ACC-STAGE097-P2-02",
            "ACC-STAGE097-P2-03",
        ):
            with self.subTest(acceptance_id=acceptance_id):
                self.assertEqual("已通过", acceptance_by_id[acceptance_id])
        self.assertEqual("已遵守", acceptance_by_id["ACC-STAGE097-P2-04"])
        self.assertIn("EVT-IDS-V0_1-STAGE097-P2-20260825-001", event_ids)
        self.assertTrue(RECEIPT.is_file())
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual("IDS-STAGE097-P3-GATE", receipt["next_gate"])
        self.assertEqual(
            "PASS_ANSWER_CONTRACT_CONTROL_SLICE_RUNTIME_DISABLED",
            receipt["result"],
        )
        self.assertTrue(all(value == 0 for value in receipt["runtime_counts"].values()))
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        self.assertIn("stage097_phase2_state:", roadmap_text)
        self.assertIn('current_phase_id: "IDS-STAGE097-P2"', roadmap_text)
        self.assertIn('next_gate_id: "IDS-STAGE097-P3-GATE"', roadmap_text)
        if current == phase3_current:
            self.assertIn("stage097_phase3_state:", roadmap_text)
            self.assertIn('current_phase_id: "IDS-STAGE097-P3"', roadmap_text)
            self.assertIn('next_gate_id: "IDS-STAGE097-P4-GATE"', roadmap_text)
        elif current == phase4_current:
            self.assertIn("stage097_phase4_state:", roadmap_text)
            self.assertIn('current_phase_id: "IDS-STAGE097-P4"', roadmap_text)
            self.assertIn('next_gate_id: "IDS-STAGE097-REVIEW-GATE"', roadmap_text)
        elif current == review_current:
            self.assertIn("stage097_review_state:", roadmap_text)
            self.assertIn('current_phase_id: "IDS-STAGE097-REVIEW"', roadmap_text)
            self.assertIn('next_gate_id: "IDS-STAGE098-P1-GATE"', roadmap_text)
        elif current == stage098_phase1_current:
            self.assertIn("stage097_review_state:", roadmap_text)
            self.assertIn("stage098_phase1_state:", roadmap_text)
            self.assertIn('current_phase_id: "IDS-STAGE098-P1"', roadmap_text)
            self.assertIn('next_gate_id: "IDS-STAGE098-P2-GATE"', roadmap_text)
        elif current == stage098_phase2_current:
            self.assertIn("stage097_review_state:", roadmap_text)
            self.assertIn("stage098_phase1_state:", roadmap_text)
            self.assertIn("stage098_phase2_state:", roadmap_text)
            self.assertIn('current_phase_id: "IDS-STAGE098-P2"', roadmap_text)
            self.assertIn('next_gate_id: "IDS-STAGE098-P3-GATE"', roadmap_text)
        else:
            self.assertIn("stage097_review_state:", roadmap_text)
            self.assertIn("stage098_phase1_state:", roadmap_text)
            self.assertIn("stage098_phase2_state:", roadmap_text)
            self.assertIn("stage098_phase3_state:", roadmap_text)
            self.assertIn('current_phase_id: "IDS-STAGE098-P3"', roadmap_text)
            self.assertIn('next_gate_id: "IDS-STAGE098-P4-GATE"', roadmap_text)


if __name__ == "__main__":
    unittest.main()
