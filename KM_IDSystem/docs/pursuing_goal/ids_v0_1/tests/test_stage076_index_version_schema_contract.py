import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE076_PHASE1_INDEX_VERSION_SCHEMA_SCOPE_BOUNDARY.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage076_index_version_schema_contract.json"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-076_索引版本Schema.md"
)
PREDECESSOR_REVIEW = BASE / "STAGE075_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "external_api_coverage_audit"
    / "stage075_external_api_coverage_audit_contract.json"
)
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-21-stage076-p1-local.json"


class Stage076IndexVersionSchemaPhase1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_scope_contract_and_governance_artifacts_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            TASKPACK,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
            ROADMAP,
            EVENTS,
            STATUS,
            PLAN,
            ACCEPTANCE,
            RUN,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_and_single_authority_boundary_are_explicit(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage076.index_version_schema.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-076", contract["stage"])
        self.assertEqual("IDS-STAGE076-P1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE076-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-076", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_INDEX_VERSION_SCHEMA_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE076-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE076_TASKPACK_STAGE075_REVIEW_AND_PREDECESSOR_CONTROL_CONTRACTS_ONLY",
            source["authority"],
        )
        for field in (
            "second_authoritative_source_created",
            "source_body_or_path_allowed",
            "raw_metadata_content_access_allowed",
            "live_source_read_performed",
            "authorized_fixture_access_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(source[field])

    def test_index_versions_active_pointer_and_building_version_are_fixed(self):
        version = self.contract["index_version_record_contract"]
        self.assertEqual(["fulltext", "vector", "hybrid"], version["supported_index_kinds"])
        self.assertEqual(8, version["field_count"])
        self.assertEqual(
            version["field_count"], len(version["future_index_versions_required_fields"])
        )
        for field in (
            "index_version",
            "document_scope_ref",
            "chunk_count",
            "embedding_model_ref",
        ):
            with self.subTest(field=field):
                self.assertIn(field, version["future_index_versions_required_fields"])
        self.assertFalse(version["additional_fields_allowed"])
        for field, value in version.items():
            if field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)

        pointer = self.contract["active_index_pointer_contract"]
        self.assertEqual(5, pointer["field_count"])
        self.assertEqual(pointer["field_count"], len(pointer["future_required_fields"]))
        self.assertTrue(pointer["one_active_version_per_index_kind_required"])
        self.assertTrue(pointer["future_atomic_switch_required"])
        self.assertFalse(pointer["active_pointer_read_allowed_in_phase1"])
        self.assertFalse(pointer["active_pointer_write_allowed_in_phase1"])

        building = self.contract["building_index_version_contract"]
        self.assertEqual(5, building["field_count"])
        self.assertEqual(building["field_count"], len(building["future_required_fields"]))
        self.assertTrue(building["every_bulk_import_requires_new_index_version"])
        self.assertTrue(building["building_version_must_not_equal_active_version"])
        self.assertTrue(building["active_index_must_continue_serving_during_build"])
        for field, value in building.items():
            if field.startswith("actual_"):
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_shadow_candidate_verification_and_rollback_fail_closed(self):
        shadow = self.contract["shadow_index_contract"]
        self.assertTrue(shadow["future_shadow_candidate_required"])
        self.assertTrue(shadow["candidate_isolated_from_active_serving"])
        self.assertTrue(shadow["candidate_must_not_serve_retrieval_before_switch"])
        self.assertFalse(shadow["shadow_index_build_allowed_in_phase1"])
        self.assertFalse(shadow["actual_shadow_index_created"])
        self.assertFalse(shadow["actual_shadow_index_queried"])

        verification = self.contract["future_switch_verification_contract"]
        self.assertEqual(6, verification["condition_count"])
        self.assertEqual(
            verification["condition_count"], len(verification["required_conditions"])
        )
        self.assertTrue(verification["passed_result_required_before_active_pointer_switch"])
        self.assertTrue(verification["failed_or_missing_result_blocks_switch"])
        self.assertFalse(verification["verification_execution_allowed_in_phase1"])
        self.assertFalse(verification["actual_verification_run_performed"])

        lifecycle = self.contract["future_index_lifecycle_contract"]
        self.assertEqual(7, lifecycle["state_count"])
        self.assertIn("ACTIVE", lifecycle["declared_states"])
        self.assertIn("FAILED", lifecycle["declared_states"])
        self.assertTrue(lifecycle["failed_candidate_must_not_replace_active_version"])
        self.assertTrue(lifecycle["old_active_index_must_remain_serving_until_successful_switch"])
        self.assertFalse(lifecycle["actual_lifecycle_transition_performed"])

        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(
            failures["failure_state_count"], len(failures["declared_failure_states"])
        )
        self.assertIn(
            "ACTIVE_POINTER_SWITCH_WITHOUT_PASSED_VERIFICATION",
            failures["declared_failure_states"],
        )
        self.assertIn(
            "PHASE1_INDEX_BUILD_OR_SWITCH_NOT_AUTHORIZED",
            failures["declared_failure_states"],
        )
        self.assertFalse(failures["automatic_business_write_allowed"])
        self.assertFalse(failures["automatic_active_pointer_switch_allowed"])
        self.assertFalse(failures["automatic_rollback_execution_allowed"])
        self.assertFalse(failures["actual_failure_record_created"])

        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "REVIEWED_EXTERNAL_API_COVERAGE_AUDIT_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        self.assertTrue(rollback["future_rollback_target_must_be_previous_active_index_version"])
        self.assertTrue(rollback["future_old_index_retention_required"])
        self.assertTrue(rollback["preserve_stage075_review_evidence"])
        self.assertFalse(rollback["github_or_ovh_change_allowed"])

    def test_runtime_and_phase_boundaries_remain_zero(self):
        for field, value in self.contract["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)
        local_code = self.contract["local_code"]
        self.assertTrue(local_code["static_contract_only"])
        self.assertFalse(local_code["runtime_module_created"])
        self.assertFalse(local_code["database_schema_created"])
        self.assertFalse(local_code["index_artifact_created"])
        boundary = self.contract["stage_and_phase_boundary"]
        for field in (
            "stage075_review_evidence_read",
            "stage076_started",
            "stage076_entry_authorized",
            "phase1_started",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase2_started",
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "stage077_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])
        for field, value in self.contract["protected_surface_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)

    def test_governance_projection_preserves_phase1_evidence(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        run = json.loads(RUN.read_text(encoding="utf-8"))
        event_ids = {
            json.loads(line)["event_id"]
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        self.assertIn(
            (status["stage"], status["phase"], status["task"], status["next_gate"]),
            (
                (
                    "IDS-STAGE076",
                    "IDS-V0_1-STAGE076-P1",
                    "IDS-V0_1-STAGE076-P1",
                    "IDS-STAGE076-P2-GATE",
                "IDS-STAGE076-P3-GATE",
                ),
                (
                    "IDS-STAGE076",
                    "IDS-V0_1-STAGE076-P2",
                    "IDS-V0_1-STAGE076-P2",
                    "IDS-STAGE076-P3-GATE",
                ),
                (
                    "IDS-STAGE076",
                    "IDS-V0_1-STAGE076-P3",
                    "IDS-V0_1-STAGE076-P3",
                    "IDS-STAGE076-P4-GATE",
                ),
                (
                    "IDS-STAGE076",
                    "IDS-V0_1-STAGE076-P4",
                    "IDS-V0_1-STAGE076-P4",
                    "IDS-STAGE076-REVIEW-GATE",
                ),
                (
                    "IDS-STAGE076",
                    "IDS-V0_1-STAGE076-REVIEW",
                    "IDS-V0_1-STAGE076-REVIEW",
                    "IDS-STAGE077-P1-GATE",
                ),
                ("IDS-STAGE077", "IDS-V0_1-STAGE077-P1", "IDS-V0_1-STAGE077-P1", "IDS-STAGE077-P2-GATE"),
                ("IDS-STAGE077", "IDS-V0_1-STAGE077-P2", "IDS-V0_1-STAGE077-P2", "IDS-STAGE077-P3-GATE"), ("IDS-STAGE077", "IDS-V0_1-STAGE077-P3", "IDS-V0_1-STAGE077-P3", "IDS-STAGE077-P4-GATE"), ("IDS-STAGE077", "IDS-V0_1-STAGE077-P4", "IDS-V0_1-STAGE077-P4", "IDS-STAGE077-REVIEW-GATE"), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-REVIEW', 'IDS-V0_1-STAGE077-REVIEW', 'IDS-STAGE078-P1-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P1', 'IDS-V0_1-STAGE078-P1', 'IDS-STAGE078-P2-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P2', 'IDS-V0_1-STAGE078-P2', 'IDS-STAGE078-P3-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P3', 'IDS-V0_1-STAGE078-P3', 'IDS-STAGE078-P4-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P4', 'IDS-V0_1-STAGE078-P4', 'IDS-STAGE078-REVIEW-GATE'), ('IDS-STAGE078', 'IDS-STAGE078-REVIEW', 'IDS-V0_1-STAGE078-REVIEW', 'IDS-STAGE079-P1-GATE'),
                (
                    "IDS-STAGE076",
                    "IDS-V0_1-STAGE076-REVIEW",
                    "IDS-V0_1-STAGE076-REVIEW",
                    "IDS-STAGE077-P1-GATE",
                ),
                ("IDS-STAGE077", "IDS-V0_1-STAGE077-P1", "IDS-V0_1-STAGE077-P1", "IDS-STAGE077-P2-GATE"),
                ("IDS-STAGE077", "IDS-V0_1-STAGE077-P2", "IDS-V0_1-STAGE077-P2", "IDS-STAGE077-P3-GATE"), ("IDS-STAGE077", "IDS-V0_1-STAGE077-P3", "IDS-V0_1-STAGE077-P3", "IDS-STAGE077-P4-GATE"), ("IDS-STAGE077", "IDS-V0_1-STAGE077-P4", "IDS-V0_1-STAGE077-P4", "IDS-STAGE077-REVIEW-GATE"), ('IDS-STAGE077', 'IDS-V0_1-STAGE077-REVIEW', 'IDS-V0_1-STAGE077-REVIEW', 'IDS-STAGE078-P1-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P1', 'IDS-V0_1-STAGE078-P1', 'IDS-STAGE078-P2-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P2', 'IDS-V0_1-STAGE078-P2', 'IDS-STAGE078-P3-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P3', 'IDS-V0_1-STAGE078-P3', 'IDS-STAGE078-P4-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P4', 'IDS-V0_1-STAGE078-P4', 'IDS-STAGE078-REVIEW-GATE'), ('IDS-STAGE078', 'IDS-STAGE078-REVIEW', 'IDS-V0_1-STAGE078-REVIEW', 'IDS-STAGE079-P1-GATE'),

                ("IDS-STAGE079", "IDS-V0_1-STAGE079-P1", "IDS-V0_1-STAGE079-P1", "IDS-STAGE079-P2-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P2", "IDS-STAGE079-P3-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P3", "IDS-STAGE079-P4-GATE")),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertIn(
            plan["task"],
            (
                "IDS-V0_1-STAGE076-P1",
                "IDS-V0_1-STAGE076-P2",
                "IDS-V0_1-STAGE076-P3",
                "IDS-V0_1-STAGE076-P4",
                "IDS-V0_1-STAGE076-REVIEW", "IDS-V0_1-STAGE077-P1",
                'IDS-V0_1-STAGE077-P2', 'IDS-V0_1-STAGE077-P3', 'IDS-V0_1-STAGE077-P4', "IDS-V0_1-STAGE077-REVIEW",
             "IDS-V0_1-STAGE078-P1", "IDS-V0_1-STAGE078-P2", "IDS-V0_1-STAGE078-P3", "IDS-V0_1-STAGE078-P4", "IDS-V0_1-STAGE078-REVIEW",
                "IDS-V0_1-STAGE079-P1",
                "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P3"),
        )
        self.assertIn("不建立第二权威事实源", "\n".join(plan["scope"]))
        acceptance_ids = {item["id"] for item in acceptance["items"]}
        self.assertTrue(
            {
                "ACC-STAGE076-P1-01",
                "ACC-STAGE076-P1-02",
                "ACC-STAGE076-P1-03",
                "ACC-STAGE076-P1-04",
            }.issubset(acceptance_ids)
        )
        self.assertEqual("IDS-V0_1-STAGE076-P1", run["task_id"])
        self.assertEqual(0, run["runtime_counts"]["actual_index_version_record_count"])
        self.assertEqual(0, run["runtime_counts"]["actual_index_build_count"])
        self.assertEqual(0, run["runtime_counts"]["actual_active_pointer_switch_count"])
        self.assertEqual(0, run["runtime_counts"]["actual_model_token_count"])
        self.assertFalse(run["runtime_actions"]["ovh_deployment_performed"])
        roadmap_text = ROADMAP.read_text(encoding="utf-8")
        self.assertIn('current_stage_id: "IDS-STAGE076"', roadmap_text)
        self.assertIn('current_phase_id: "IDS-STAGE076-P1"', roadmap_text)
        self.assertIn('current_task_id: "IDS-V0_1-STAGE076-P1"', roadmap_text)
        self.assertIn("EVT-IDS-V0_1-STAGE076-P1-20260821-001", event_ids)

    def test_scope_document_explains_boundary_and_next_gate(self):
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "旧索引在构建期间继续服务",
            "不得切换活动指针",
            "IDS-STAGE076-P2-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
