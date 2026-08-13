import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE1_CONTRACT = (
    BASE / "structured_table_facts" / "stage061_structured_data_quality_contract.json"
)
PHASE2 = BASE / "STAGE061_PHASE2_STRUCTURED_DATA_QUALITY_CONTROL_SLICE.md"
CONTRACT = (
    BASE / "structured_table_facts" / "stage061_structured_data_quality_slice_contract.json"
)
SLICE = BASE / "structured_table_facts" / "stage061_structured_data_quality_slice.py"
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-14-stage061-p2-local.json"


class Stage061StructuredDataQualityPhase2Tests(unittest.TestCase):
    def _slice(self):
        spec = importlib.util.spec_from_file_location(
            "stage061_structured_data_quality_slice", SLICE
        )
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        return module

    def _contract(self):
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _control(self):
        return {
            "structured_data_quality_input_records": [
                {
                    "quality_request_ref": "quality-request:control:stage061-p2:production",
                    "source_identity_ref": "source:control:stage061-p2",
                    "source_document_ref": (
                        "source-document:control:stage061-p2:production"
                    ),
                    "file_format": "XLSX",
                    "workbook_ref": "workbook:control:stage061-p2:production",
                    "worksheet_ref": "worksheet:control:stage061-p2:production",
                    "header_row_ref": "header-row:control:stage061-p2:production",
                    "row_range_ref": "row-range:control:stage061-p2:production",
                    "column_range_ref": "column-range:control:stage061-p2:production",
                    "schema_profile_ref": (
                        "schema-profile:control:stage061-p2:production"
                    ),
                    "fact_set_ref": "fact-set:control:stage061-p2:production",
                    "field_candidate_ref": (
                        "field-candidate:control:stage061-p2:production"
                    ),
                    "primary_key_ref": "primary-key:control:stage061-p2:production",
                    "record_type": "PRODUCTION_RECORD",
                    "evidence_ref": "evidence:control:stage061-p2:production",
                    "quality_profile_ref": (
                        "quality-profile:control:stage061-p2:production"
                    ),
                },
                {
                    "quality_request_ref": "quality-request:control:stage061-p2:quality",
                    "source_identity_ref": "source:control:stage061-p2",
                    "source_document_ref": (
                        "source-document:control:stage061-p2:quality"
                    ),
                    "file_format": "CSV",
                    "workbook_ref": "workbook:control:stage061-p2:quality",
                    "worksheet_ref": "worksheet:control:stage061-p2:quality",
                    "header_row_ref": "header-row:control:stage061-p2:quality",
                    "row_range_ref": "row-range:control:stage061-p2:quality",
                    "column_range_ref": "column-range:control:stage061-p2:quality",
                    "schema_profile_ref": "schema-profile:control:stage061-p2:quality",
                    "fact_set_ref": "fact-set:control:stage061-p2:quality",
                    "field_candidate_ref": (
                        "field-candidate:control:stage061-p2:quality"
                    ),
                    "primary_key_ref": "primary-key:control:stage061-p2:quality",
                    "record_type": "QUALITY_INSPECTION_RECORD",
                    "evidence_ref": "evidence:control:stage061-p2:quality",
                    "quality_profile_ref": "quality-profile:control:stage061-p2:quality",
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
            "ids.stage061.structured_data_quality.phase2.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE061-P2", contract["task_id"])
        self.assertTrue(contract["slice_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE061-P3-GATE", contract["next_gate"])
        self.assertFalse(contract["source_authority"]["second_authoritative_source_created"])
        self.assertEqual(
            16,
            contract["reference_only_quality_input_control_contract"]["field_count"],
        )
        self.assertEqual(
            2,
            contract["reference_only_quality_input_control_contract"][
                "control_record_count"
            ],
        )
        self.assertEqual(18, contract["quality_result_candidate_contract"]["field_count"])
        self.assertEqual(
            10,
            contract["quality_result_candidate_contract"][
                "control_quality_result_candidate_count"
            ],
        )
        self.assertEqual(
            5,
            contract["quality_dimension_control_contract"]["quality_dimension_count"],
        )
        self.assertFalse(contract["runtime_boundary"]["xlsx_or_csv_parse_performed"])
        self.assertFalse(contract["runtime_boundary"]["production_runtime_activation_performed"])

    def test_control_slice_projects_ten_unassessed_quality_candidates_from_p1_input(self):
        result = self._slice().execute_structured_data_quality_control_slice(
            self._control()
        )
        self.assertTrue(result["input_accepted"])
        self.assertEqual(
            "COMPLETED_IN_MEMORY_STRUCTURED_DATA_QUALITY_CANDIDATE_CONTROL_SLICE",
            result["execution_state"],
        )
        self.assertEqual(2, result["control_quality_input_record_count"])
        self.assertEqual(0, result["actual_quality_input_record_count"])
        self.assertEqual(10, result["quality_result_candidate_count"])
        self.assertEqual(
            [
                "FIELD_COMPLETENESS",
                "UNIT_CONSISTENCY",
                "DATE_VALIDITY",
                "PRIMARY_KEY_DUPLICATION",
                "OUTLIER_REVIEW",
            ],
            result["quality_dimensions_covered"],
        )
        self.assertEqual(5, result["quality_dimension_count"])
        self.assertEqual(
            {
                "FIELD_COMPLETENESS": 2,
                "UNIT_CONSISTENCY": 2,
                "DATE_VALIDITY": 2,
                "PRIMARY_KEY_DUPLICATION": 2,
                "OUTLIER_REVIEW": 2,
            },
            result["quality_dimension_candidate_counts"],
        )
        self.assertTrue(result["control_quality_input_reference_validation_performed"])
        self.assertTrue(result["control_source_location_reference_validation_performed"])
        self.assertTrue(result["control_quality_result_candidate_projection_performed"])

    def test_candidates_have_exact_p1_result_shape_and_control_references(self):
        result = self._slice().execute_structured_data_quality_control_slice(
            self._control()
        )
        candidate = result["quality_result_candidates"][0]
        self.assertEqual(
            {
                "quality_result_ref",
                "quality_request_ref",
                "quality_dimension",
                "quality_state",
                "field_candidate_ref",
                "primary_key_ref",
                "source_identity_ref",
                "source_document_ref",
                "workbook_ref",
                "worksheet_ref",
                "header_row_ref",
                "row_range_ref",
                "column_range_ref",
                "fact_set_ref",
                "evidence_ref",
                "human_review_state",
                "statistical_conclusion_state",
                "remediation_state",
            },
            set(candidate),
        )
        self.assertEqual("UNASSESSED", candidate["quality_state"])
        self.assertEqual(
            "REQUIRED_WHEN_UNVERIFIED", candidate["human_review_state"]
        )
        self.assertEqual(
            "BLOCKED_UNVERIFIED_REFERENCE_ONLY",
            candidate["statistical_conclusion_state"],
        )
        self.assertTrue(
            all(
                ":control:" in value
                for field, value in candidate.items()
                if field.endswith("_ref")
            )
        )
        self.assertEqual(10, result["source_location_binding_candidate_count"])
        self.assertTrue(result["source_location_references_preserved"])
        self.assertFalse(result["source_body_or_header_or_cell_content_retained"])

    def test_quality_and_numeric_conclusions_remain_closed_pending_human_review(self):
        result = self._slice().execute_structured_data_quality_control_slice(
            self._control()
        )
        self.assertTrue(result["all_quality_states_unassessed"])
        self.assertTrue(result["all_human_review_required"])
        self.assertTrue(result["all_statistical_conclusions_blocked"])
        for field in (
            "field_completeness_evaluation_performed",
            "unit_consistency_evaluation_performed",
            "date_validity_evaluation_performed",
            "primary_key_duplication_evaluation_performed",
            "outlier_evaluation_performed",
            "quality_gate_evaluation_performed",
            "numeric_statistic_computation_performed",
            "actual_structured_fact_created",
            "actual_quality_result_created",
            "actual_quality_result_persisted",
        ):
            with self.subTest(field=field):
                self.assertFalse(result[field])
        self.assertFalse(result["model_direct_text_guessing_allowed"])
        self.assertFalse(result["unverified_numeric_value_as_definitive_fact_allowed"])
        self.assertFalse(result["summary_can_replace_structured_fact"])
        self.assertFalse(result["summary_can_become_numeric_statistical_evidence"])

    def test_phase2_historical_evidence_and_current_governance_preserve_a_legal_successor(self):
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
            if item.get("event_id") == "EVT-IDS-V0_1-STAGE061-P2-20260814-001"
        )

        self.assertIn(
            (status["phase"], status["next_gate"]),
            (
                ("IDS-V0_1-STAGE061-P2", "IDS-STAGE061-P3-GATE"),
                ("IDS-V0_1-STAGE061-P3", "IDS-STAGE061-P4-GATE"),
                ("IDS-V0_1-STAGE061-P4", "IDS-STAGE061-REVIEW-GATE"),
                ("IDS-V0_1-STAGE061-REVIEW", "IDS-STAGE062-P1-GATE"),
                ("IDS-V0_1-STAGE062-P1", "IDS-STAGE062-P2-GATE"),
                ("IDS-V0_1-STAGE062-P2", "IDS-STAGE062-P3-GATE"),
                ("IDS-V0_1-STAGE062-P3", "IDS-STAGE062-P4-GATE"),
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertIn(
            plan["task"],
            (
                "IDS-V0_1-STAGE061-P2",
                "IDS-V0_1-STAGE061-P3",
                "IDS-V0_1-STAGE061-P4",
                "IDS-V0_1-STAGE061-REVIEW",
                "IDS-V0_1-STAGE062-P1",
                "IDS-V0_1-STAGE062-P2",
                "IDS-V0_1-STAGE062-P3",
            ),
        )
        self.assertIn(status["next_gate"], plan["stop_condition"])
        self.assertIn("OVH", plan["stop_condition"])
        self.assertEqual("IDS-V0_1-STAGE061-P2", run["task_id"])
        self.assertEqual("RUN-IDS-STAGE061-P2-LOCAL-20260814-001", run["run_id"])
        self.assertEqual("IDS-STAGE061-P3-GATE", run["next_gate"])
        self.assertEqual(
            "PASS_LOCAL_PHASE2_STRUCTURED_DATA_QUALITY_CONTROL_SLICE_RUNTIME_DISABLED",
            run["result"],
        )
        self.assertEqual("phase_completed", event["event_type"])
        self.assertEqual("IDS-V0_1-STAGE061-P2", event["task_id"])
        self.assertEqual(["ACC-STAGE-061"], event["acceptance_ids"])
        self.assertTrue(
            {
                "ACC-STAGE061-P2-01",
                "ACC-STAGE061-P2-02",
                "ACC-STAGE061-P2-03",
                "ACC-STAGE061-P2-04",
            }.issubset({item["id"] for item in acceptance["items"]})
        )
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        self.assertIn('status: "stage061_phase2_completed"', batch)
        self.assertIn('current_task_id: "IDS-V0_1-STAGE061-P2"', batch)
        self.assertIn('next_gate: "IDS-STAGE061-P3-GATE"', batch)
        self.assertIn('current_phase_id: "IDS-STAGE061-P2"', roadmap)
        self.assertIn('next_gate_id: "IDS-STAGE061-P3-GATE"', roadmap)

    def test_invalid_control_input_rejects_without_candidates_or_reference_output(self):
        control = self._control()
        control["unexpected"] = "not accepted"
        result = self._slice().execute_structured_data_quality_control_slice(control)
        self.assertFalse(result["input_accepted"])
        self.assertEqual("REJECTED", result["execution_state"])
        self.assertIsNone(result["source_identity_ref"])
        self.assertEqual([], result["quality_result_candidates"])
        self.assertEqual(0, result["quality_result_candidate_count"])
        self.assertFalse(result["control_quality_result_candidate_projection_performed"])

    def test_reordered_or_tampered_control_input_rejects(self):
        reordered = self._control()
        reordered["structured_data_quality_input_records"].reverse()
        reordered_result = self._slice().execute_structured_data_quality_control_slice(
            reordered
        )
        self.assertFalse(reordered_result["input_accepted"])

        tampered = self._control()
        tampered["structured_data_quality_input_records"][0]["quality_profile_ref"] = (
            "quality-profile:control:stage061-p2:unexpected"
        )
        tampered_result = self._slice().execute_structured_data_quality_control_slice(
            tampered
        )
        self.assertFalse(tampered_result["input_accepted"])

    def test_chinese_feedback_is_present_without_business_content(self):
        result = self._slice().execute_structured_data_quality_control_slice(
            self._control()
        )
        self.assertEqual(4, len(result["chinese_feedback"]))
        self.assertTrue(
            all(
                any("\u4e00" <= char <= "\u9fff" for char in message)
                for message in result["chinese_feedback"]
            )
        )
        self.assertFalse(result["source_body_or_header_or_cell_content_retained"])
        self.assertFalse(result["actual_quality_result_persisted"])

    def test_real_data_storage_and_external_actions_remain_disabled(self):
        result = self._slice().execute_structured_data_quality_control_slice(
            self._control()
        )
        for field in (
            "ids_business_source_read_performed",
            "authorized_fixture_access_performed",
            "source_file_open_performed",
            "file_type_detection_performed",
            "xlsx_or_csv_parse_performed",
            "table_schema_inference_performed",
            "field_identification_performed",
            "structured_fact_extraction_performed",
            "typed_value_extraction_performed",
            "table_summary_generation_performed",
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
