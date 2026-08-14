import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = (
    BASE / "structured_table_facts" / "stage062_table_evidence_binding_contract.json"
)
PHASE2 = BASE / "STAGE062_PHASE2_TABLE_EVIDENCE_BINDING_CONTROL_SLICE.md"
CONTRACT = (
    BASE / "structured_table_facts" / "stage062_table_evidence_binding_slice_contract.json"
)
SLICE = BASE / "structured_table_facts" / "stage062_table_evidence_binding_slice.py"
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-14-stage062-p2-local.json"


class Stage062TableEvidenceBindingPhase2Tests(unittest.TestCase):
    def _slice(self):
        spec = importlib.util.spec_from_file_location(
            "stage062_table_evidence_binding_slice", SLICE
        )
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        return module

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _control(self):
        return {
            "table_evidence_binding_requests": [
                {
                    "binding_request_ref": "binding-request:control:stage062-p2:production",
                    "fact_ref": "fact:control:stage062-p2:production",
                    "evidence_id": "evidence-id:control:stage062-p2:production",
                    "document_id": "document-id:control:stage062-p2:production",
                    "sheet": "sheet:control:stage062-p2:production",
                    "row": "row:control:stage062-p2:production",
                    "column": "column:control:stage062-p2:production",
                    "source_uri": "source-uri:control:stage062-p2:production",
                    "file_format": "XLSX",
                    "record_type": "PRODUCTION_RECORD",
                    "workbook_ref": "workbook:control:stage062-p2:production",
                    "schema_profile_ref": "schema-profile:control:stage062-p2:production",
                    "field_candidate_ref": "field-candidate:control:stage062-p2:production",
                    "primary_key_ref": "primary-key:control:stage062-p2:production",
                    "quality_result_ref": "quality-result:control:stage062-p2:production",
                    "measurement_value_ref": "measurement-value:control:stage062-p2:production",
                    "unit_ref": "unit:control:stage062-p2:production",
                    "record_date_ref": "record-date:control:stage062-p2:production",
                    "fact_type": "MEASUREMENT_FACT",
                },
                {
                    "binding_request_ref": "binding-request:control:stage062-p2:quality",
                    "fact_ref": "fact:control:stage062-p2:quality",
                    "evidence_id": "evidence-id:control:stage062-p2:quality",
                    "document_id": "document-id:control:stage062-p2:quality",
                    "sheet": "sheet:control:stage062-p2:quality",
                    "row": "row:control:stage062-p2:quality",
                    "column": "column:control:stage062-p2:quality",
                    "source_uri": "source-uri:control:stage062-p2:quality",
                    "file_format": "CSV",
                    "record_type": "QUALITY_INSPECTION_RECORD",
                    "workbook_ref": "workbook:control:stage062-p2:quality",
                    "schema_profile_ref": "schema-profile:control:stage062-p2:quality",
                    "field_candidate_ref": "field-candidate:control:stage062-p2:quality",
                    "primary_key_ref": "primary-key:control:stage062-p2:quality",
                    "quality_result_ref": "quality-result:control:stage062-p2:quality",
                    "measurement_value_ref": "measurement-value:control:stage062-p2:quality",
                    "unit_ref": "unit:control:stage062-p2:quality",
                    "record_date_ref": "record-date:control:stage062-p2:quality",
                    "fact_type": "QUALITY_RESULT_FACT",
                },
            ]
        }

    def test_phase2_artifacts_exist(self):
        for artifact in (
            PHASE1_CONTRACT,
            PHASE2,
            CONTRACT,
            SLICE,
            BATCH,
            ROADMAP,
            EVENTS,
            STATUS,
            PLAN,
            ACCEPTANCE,
            RUN,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_contract_is_executable_but_real_input_and_runtime_remain_disabled(self):
        contract = self._contract()
        self.assertEqual(
            "ids.stage062.table_evidence_binding.phase2.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE062-P2", contract["task_id"])
        self.assertTrue(contract["slice_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE062-P3-GATE", contract["next_gate"])
        self.assertFalse(contract["source_authority"]["second_authoritative_source_created"])
        input_contract = contract["reference_only_binding_input_control_contract"]
        self.assertEqual(19, input_contract["field_count"])
        self.assertEqual(2, input_contract["control_request_count"])
        self.assertEqual(6, input_contract["binding_dimension_count"])
        self.assertEqual(12, input_contract["control_binding_dimension_reference_count"])
        candidate_contract = contract["table_evidence_binding_candidate_contract"]
        self.assertEqual(17, candidate_contract["field_count"])
        self.assertEqual(2, candidate_contract["control_binding_candidate_count"])
        self.assertFalse(contract["runtime_boundary"]["xlsx_or_csv_parse_performed"])
        self.assertFalse(contract["runtime_boundary"]["production_runtime_activation_performed"])

    def test_control_slice_projects_two_unbound_candidates_from_phase1_shape(self):
        result = self._slice().execute_table_evidence_binding_control_slice(self._control())
        self.assertTrue(result["input_accepted"])
        self.assertEqual(
            "COMPLETED_IN_MEMORY_TABLE_EVIDENCE_BINDING_CANDIDATE_CONTROL_SLICE",
            result["execution_state"],
        )
        self.assertEqual(2, result["control_binding_request_count"])
        self.assertEqual(0, result["actual_input_record_count"])
        self.assertEqual(2, result["table_evidence_binding_candidate_count"])
        self.assertEqual(
            ["evidence_id", "document_id", "sheet", "row", "column", "source_uri"],
            result["binding_dimensions_covered"],
        )
        self.assertEqual(6, result["binding_dimension_count"])
        self.assertEqual(12, result["control_binding_dimension_reference_count"])
        self.assertEqual(
            ["PRODUCTION_RECORD", "QUALITY_INSPECTION_RECORD"],
            result["record_types_covered"],
        )
        self.assertEqual(["XLSX", "CSV"], result["file_formats_covered"])
        self.assertTrue(result["control_binding_request_reference_validation_performed"])
        self.assertTrue(result["control_binding_candidate_projection_performed"])

    def test_candidates_keep_exact_output_shape_and_control_traceability(self):
        result = self._slice().execute_table_evidence_binding_control_slice(self._control())
        candidate = result["table_evidence_binding_candidates"][0]
        self.assertEqual(
            {
                "table_evidence_binding_ref",
                "binding_request_ref",
                "fact_ref",
                "evidence_id",
                "document_id",
                "sheet",
                "row",
                "column",
                "source_uri",
                "field_candidate_ref",
                "schema_profile_ref",
                "quality_result_ref",
                "fact_type",
                "binding_state",
                "human_review_state",
                "numeric_authority_state",
                "remediation_state",
            },
            set(candidate),
        )
        self.assertEqual("UNBOUND_REFERENCE_ONLY", candidate["binding_state"])
        self.assertEqual("REQUIRED_WHEN_UNVERIFIED", candidate["human_review_state"])
        self.assertEqual(
            "BLOCKED_UNVERIFIED_REFERENCE_ONLY", candidate["numeric_authority_state"]
        )
        self.assertEqual(
            "HUMAN_SOURCE_AND_EVIDENCE_CONFIRMATION_REQUIRED",
            candidate["remediation_state"],
        )
        for field in (
            "evidence_id",
            "document_id",
            "sheet",
            "row",
            "column",
            "source_uri",
        ):
            with self.subTest(field=field):
                self.assertIn(":control:", candidate[field])
        self.assertTrue(result["source_location_reference_shape_preserved"])
        self.assertFalse(result["source_body_or_header_or_cell_content_retained"])

    def test_binding_and_numeric_conclusions_remain_closed_pending_human_review(self):
        result = self._slice().execute_table_evidence_binding_control_slice(self._control())
        self.assertTrue(result["all_binding_states_unbound"])
        self.assertTrue(result["all_human_review_required"])
        self.assertTrue(result["all_numeric_authority_blocked"])
        for field in (
            "table_schema_inference_performed",
            "field_identification_performed",
            "structured_fact_extraction_performed",
            "typed_value_extraction_performed",
            "table_summary_generation_performed",
            "numeric_statistic_computation_performed",
            "quality_gate_evaluation_performed",
            "source_location_binding_performed",
            "evidence_binding_performed",
            "actual_structured_fact_created",
            "actual_table_evidence_binding_created",
            "actual_table_evidence_binding_persisted",
            "actual_evidence_record_created",
        ):
            with self.subTest(field=field):
                self.assertFalse(result[field])
        self.assertFalse(result["model_direct_text_guessing_allowed"])
        self.assertFalse(result["unverified_numeric_value_as_definitive_fact_allowed"])
        self.assertFalse(result["summary_can_replace_structured_fact"])
        self.assertFalse(result["summary_can_become_numeric_statistical_evidence"])

    def test_current_governance_preserves_phase2_evidence_or_legal_successor(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        run = json.loads(RUN.read_text(encoding="utf-8"))
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        event = next(
            item
            for item in events
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE062-P2-20260814-001"
        )

        self.assertIn(status["stage"], ("IDS-STAGE062", "IDS-STAGE063", "IDS-STAGE064", "IDS-STAGE065", "IDS-STAGE066", "IDS-STAGE067", "IDS-STAGE068"))
        self.assertIn(
            (status["phase"], status["task"], status["next_gate"]),
            (
                ("IDS-V0_1-STAGE062-P2", "IDS-V0_1-STAGE062-P2", "IDS-STAGE062-P3-GATE"),
                ("IDS-V0_1-STAGE062-P3", "IDS-V0_1-STAGE062-P3", "IDS-STAGE062-P4-GATE"),
                ("IDS-V0_1-STAGE062-P4", "IDS-V0_1-STAGE062-P4", "IDS-STAGE062-REVIEW-GATE"),
                ("IDS-STAGE062-REVIEW", "IDS-V0_1-STAGE062-REVIEW", "IDS-STAGE063-P1-GATE"),
                ("IDS-V0_1-STAGE063-P1", "IDS-V0_1-STAGE063-P1", "IDS-STAGE063-P2-GATE"),
                ("IDS-V0_1-STAGE063-P2", "IDS-V0_1-STAGE063-P2", "IDS-STAGE063-P3-GATE"),
                ("IDS-V0_1-STAGE063-P3", "IDS-V0_1-STAGE063-P3", "IDS-STAGE063-P4-GATE"),
                ("IDS-V0_1-STAGE063-P4", "IDS-V0_1-STAGE063-P4", "IDS-STAGE063-REVIEW-GATE"),
                ("IDS-V0_1-STAGE063-REVIEW", "IDS-V0_1-STAGE063-REVIEW", "IDS-STAGE064-P1-GATE"),
                ("IDS-V0_1-STAGE064-P1", "IDS-V0_1-STAGE064-P1", "IDS-STAGE064-P2-GATE"),
                ("IDS-V0_1-STAGE064-P2", "IDS-V0_1-STAGE064-P2", "IDS-STAGE064-P3-GATE"),
                ("IDS-V0_1-STAGE064-P3", "IDS-V0_1-STAGE064-P3", "IDS-STAGE064-P4-GATE"),
                ("IDS-V0_1-STAGE064-P4", "IDS-V0_1-STAGE064-P4", "IDS-STAGE064-REVIEW-GATE"),
                ("IDS-V0_1-STAGE064-REVIEW", "IDS-V0_1-STAGE064-REVIEW", "IDS-STAGE065-P1-GATE"),
                ("IDS-V0_1-STAGE065-P1", "IDS-V0_1-STAGE065-P1", "IDS-STAGE065-P2-GATE"),
                ("IDS-V0_1-STAGE065-P2", "IDS-V0_1-STAGE065-P2", "IDS-STAGE065-P3-GATE"),
                ("IDS-V0_1-STAGE065-P3", "IDS-V0_1-STAGE065-P3", "IDS-STAGE065-P4-GATE"),
                ("IDS-V0_1-STAGE065-P4", "IDS-V0_1-STAGE065-P4", "IDS-STAGE065-REVIEW-GATE"),
                ("IDS-V0_1-STAGE065-REVIEW", "IDS-V0_1-STAGE065-REVIEW", "IDS-STAGE066-P1-GATE"),
                ("IDS-V0_1-STAGE066-P1", "IDS-V0_1-STAGE066-P1", "IDS-STAGE066-P2-GATE"),
                ("IDS-V0_1-STAGE066-P2", "IDS-V0_1-STAGE066-P2", "IDS-STAGE066-P3-GATE"),
                ("IDS-V0_1-STAGE066-P3", "IDS-V0_1-STAGE066-P3", "IDS-STAGE066-P4-GATE"),
                ("IDS-V0_1-STAGE066-P4", "IDS-V0_1-STAGE066-P4", "IDS-STAGE066-REVIEW-GATE"),
                ("IDS-STAGE066-REVIEW", "IDS-V0_1-STAGE066-REVIEW", "IDS-STAGE067-P1-GATE"),
                ("IDS-V0_1-STAGE067-P1", "IDS-V0_1-STAGE067-P1", "IDS-STAGE067-P2-GATE"), ("IDS-V0_1-STAGE067-P2", "IDS-V0_1-STAGE067-P2", "IDS-STAGE067-P3-GATE"),
            ("IDS-V0_1-STAGE067-P3", "IDS-V0_1-STAGE067-P3", "IDS-STAGE067-P4-GATE"),
            ("IDS-V0_1-STAGE067-P4", "IDS-V0_1-STAGE067-P4", "IDS-STAGE067-REVIEW-GATE"),
                ("IDS-V0_1-STAGE067-REVIEW", "IDS-V0_1-STAGE067-REVIEW", "IDS-STAGE068-P1-GATE"),
                ("IDS-V0_1-STAGE068-P1", "IDS-V0_1-STAGE068-P1", "IDS-STAGE068-P2-GATE"),
                ("IDS-V0_1-STAGE068-P2", "IDS-V0_1-STAGE068-P2", "IDS-STAGE068-P3-GATE"),
                ("IDS-V0_1-STAGE068-P3", "IDS-V0_1-STAGE068-P3", "IDS-STAGE068-P4-GATE"),
                ("IDS-V0_1-STAGE068-P4", "IDS-V0_1-STAGE068-P4", "IDS-STAGE068-REVIEW-GATE"),
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertIn(plan["stage"], ("IDS-STAGE062", "IDS-STAGE063", "IDS-STAGE064", "IDS-STAGE065", "IDS-STAGE066", "IDS-STAGE067", "IDS-STAGE068"))
        self.assertIn(
            plan["task"],
            ("IDS-V0_1-STAGE062-P2", "IDS-V0_1-STAGE062-P3", "IDS-V0_1-STAGE062-P4", "IDS-V0_1-STAGE062-REVIEW", "IDS-V0_1-STAGE063-P1", "IDS-V0_1-STAGE063-P2", "IDS-V0_1-STAGE063-P3", "IDS-V0_1-STAGE063-P4", "IDS-V0_1-STAGE063-REVIEW", "IDS-V0_1-STAGE064-P1", "IDS-V0_1-STAGE064-P2", "IDS-V0_1-STAGE064-P3", "IDS-V0_1-STAGE064-P4", "IDS-V0_1-STAGE064-REVIEW", "IDS-V0_1-STAGE065-P1", "IDS-V0_1-STAGE065-P2", "IDS-V0_1-STAGE065-P3", "IDS-V0_1-STAGE065-P4", "IDS-V0_1-STAGE065-REVIEW", "IDS-V0_1-STAGE066-P1", "IDS-V0_1-STAGE066-P2", "IDS-V0_1-STAGE066-P3", "IDS-V0_1-STAGE066-P4", "IDS-V0_1-STAGE066-REVIEW", "IDS-V0_1-STAGE067-P1", "IDS-V0_1-STAGE067-P2", "IDS-V0_1-STAGE067-P3", "IDS-V0_1-STAGE067-P4", "IDS-V0_1-STAGE067-REVIEW", "IDS-V0_1-STAGE068-P1", "IDS-V0_1-STAGE068-P2", "IDS-V0_1-STAGE068-P3", "IDS-V0_1-STAGE068-P4"),
        )
        self.assertTrue(
            "IDS-STAGE062-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE062-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE062-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE063-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE063-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE063-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE063-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE064-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE063-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE064-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE064-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE064-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE064-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE065-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE065-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE065-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE065-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE065-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE066-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE066-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE066-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE066-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE066-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE067-P1-GATE" in plan["stop_condition"]
            or ("IDS-STAGE067-P2-GATE" in plan["stop_condition"] or "IDS-STAGE067-P3-GATE" in plan["stop_condition"] or "IDS-STAGE067-P4-GATE" in plan["stop_condition"] or "IDS-STAGE067-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE068-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE068-P2-GATE" in plan["stop_condition"] or "IDS-STAGE068-P3-GATE" in plan["stop_condition"])
            or "IDS-STAGE068-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE068-REVIEW-GATE" in plan["stop_condition"]
        )
        self.assertIn("OVH", plan["stop_condition"])
        acceptance_ids = {item["id"] for item in acceptance["items"]}
        self.assertTrue(
            {
                "ACC-STAGE062-P2-01",
                "ACC-STAGE062-P2-02",
                "ACC-STAGE062-P2-03",
                "ACC-STAGE062-P2-04",
            }.issubset(acceptance_ids)
        )
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        self.assertTrue(
            (
                'current_phase_id: "IDS-STAGE062-P2"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE062-P3-GATE"' in roadmap_text
            )
            or (
                'current_phase_id: "IDS-STAGE062-P3"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE062-P4-GATE"' in roadmap_text
            )
            or (
                'current_phase_id: "IDS-STAGE062-REVIEW"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE063-P1-GATE"' in roadmap_text
            )
            or (
                'current_stage_id: "IDS-STAGE063"' in roadmap_text
                and 'current_phase_id: "IDS-STAGE063-P1"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE063-P2-GATE"' in roadmap_text
            )
            or (
                'current_stage_id: "IDS-STAGE063"' in roadmap_text
                and 'current_phase_id: "IDS-STAGE063-P2"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE063-P3-GATE"' in roadmap_text
            )
            or (
                'current_stage_id: "IDS-STAGE063"' in roadmap_text
                and 'current_phase_id: "IDS-STAGE063-P3"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE063-P4-GATE"' in roadmap_text
            )
            or (
                'current_stage_id: "IDS-STAGE063"' in roadmap_text
                and 'current_phase_id: "IDS-STAGE063-P4"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE063-REVIEW-GATE"' in roadmap_text
            )
            or (
                'current_stage_id: "IDS-STAGE063"' in roadmap_text
                and 'current_phase_id: "IDS-V0_1-STAGE063-REVIEW"' in roadmap_text
                and 'next_gate_id: "IDS-STAGE064-P1-GATE"' in roadmap_text
            )
        )
        self.assertEqual("phase_completed", event["event_type"])
        self.assertEqual("IDS-V0_1-STAGE062-P2", event["task_id"])
        self.assertEqual(["ACC-STAGE-062"], event["acceptance_ids"])
        self.assertEqual("IDS-V0_1-STAGE062-P2", run["task_id"])
        self.assertEqual("RUN-IDS-STAGE062-P2-LOCAL-20260814-001", run["run_id"])
        self.assertEqual("IDS-STAGE062", run["stage"])
        self.assertEqual("IDS-STAGE062-P3-GATE", run["next_gate"])
        self.assertTrue(run["result"].startswith("PASS_LOCAL_"))

    def test_invalid_reordered_or_tampered_control_input_rejects(self):
        slice_module = self._slice()
        unexpected = self._control()
        unexpected["unexpected"] = "not accepted"
        rejected = slice_module.execute_table_evidence_binding_control_slice(unexpected)
        self.assertFalse(rejected["input_accepted"])
        self.assertEqual("REJECTED", rejected["execution_state"])
        self.assertEqual([], rejected["table_evidence_binding_candidates"])
        self.assertEqual(0, rejected["table_evidence_binding_candidate_count"])
        self.assertFalse(rejected["control_binding_candidate_projection_performed"])

        reordered = self._control()
        reordered["table_evidence_binding_requests"].reverse()
        self.assertFalse(
            slice_module.execute_table_evidence_binding_control_slice(reordered)[
                "input_accepted"
            ]
        )

        tampered = self._control()
        tampered["table_evidence_binding_requests"][0]["source_uri"] = (
            "source-uri:control:stage062-p2:unexpected"
        )
        self.assertFalse(
            slice_module.execute_table_evidence_binding_control_slice(tampered)[
                "input_accepted"
            ]
        )

    def test_chinese_feedback_and_external_actions_remain_disabled(self):
        result = self._slice().execute_table_evidence_binding_control_slice(self._control())
        self.assertEqual(4, len(result["chinese_feedback"]))
        self.assertTrue(
            all(
                any("\u4e00" <= char <= "\u9fff" for char in message)
                for message in result["chinese_feedback"]
            )
        )
        for field in (
            "ids_business_source_read_performed",
            "raw_metadata_content_accessed",
            "authorized_fixture_access_performed",
            "source_file_open_performed",
            "file_type_detection_performed",
            "xlsx_or_csv_parse_performed",
            "database_connection_performed",
            "database_schema_migration_performed",
            "structured_fact_write_performed",
            "quality_result_write_performed",
            "persistent_state_write_performed",
            "agent_execution_performed",
            "model_call_performed",
            "model_token_consumption_performed",
            "local_service_start_performed",
            "ovh_deployment_performed",
            "production_runtime_activation_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(result[field])


if __name__ == "__main__":
    unittest.main()
