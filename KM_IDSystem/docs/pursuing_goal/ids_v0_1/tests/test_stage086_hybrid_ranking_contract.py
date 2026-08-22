import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE086_PHASE1_HYBRID_RANKING_SCOPE_BOUNDARY.md"
CONTRACT = BASE / "index_version_schema" / "stage086_hybrid_ranking_contract.json"
TASKPACK = ROOT / "docs" / "taskpacks" / "IDS_v0_1_Final_Chinese_Revised" / "stages" / "STAGE-086_混合排序.md"
PREDECESSOR_REVIEW = BASE / "STAGE085_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = BASE / "index_version_schema" / "stage085_metadata_filter_contract.json"
PREDECESSOR_DELIVERY = BASE / "index_version_schema" / "stage085_metadata_filter_delivery_contract.json"


class Stage086HybridRankingPhase1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_scope_contract_taskpack_and_predecessor_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            TASKPACK,
            PREDECESSOR_REVIEW,
            PREDECESSOR_CONTRACT,
            PREDECESSOR_DELIVERY,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_identity_and_single_authority_boundary_are_explicit(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage086.hybrid_ranking_contract.phase1.v1",
            contract["schema_version"],
        )
        self.assertEqual("STAGE-086", contract["stage"])
        self.assertEqual("IDS-STAGE086-P1", contract["phase"])
        self.assertEqual("IDS-V0_1-STAGE086-P1", contract["task_id"])
        self.assertEqual("ACC-STAGE-086", contract["acceptance_id"])
        self.assertEqual(
            "PHASE1_HYBRID_RANKING_CONTRACT_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertEqual("IDS-STAGE086-P2-GATE", contract["next_gate"])
        source = contract["source_authority"]
        self.assertEqual(
            "FROZEN_STAGE086_TASKPACK_AND_STAGE085_REVIEWED_METADATA_FILTER_CONTRACTS_ONLY",
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

    def test_query_filter_candidate_selected_score_and_trace_shapes_are_fixed(self):
        shape = self.contract["query_filter_candidate_selected_score_and_trace_contract"]
        pairs = (
            ("query_field_count", "future_query_fields"),
            ("metadata_filter_field_count", "future_metadata_filter_fields"),
            ("candidate_field_count", "future_candidate_fields"),
            ("selected_result_field_count", "future_selected_result_fields"),
            ("hybrid_score_field_count", "future_hybrid_score_fields"),
            ("active_index_version_field_count", "future_active_index_version_fields"),
            ("retrieval_trace_field_count", "future_retrieval_trace_fields"),
        )
        for count_field, fields_field in pairs:
            with self.subTest(count_field=count_field):
                self.assertEqual(shape[count_field], len(shape[fields_field]))
        self.assertEqual(
            [
                "material_quality_score_ref",
                "freshness_score_ref",
                "business_module_score_ref",
            ],
            [
                item
                for item in shape["future_hybrid_score_fields"]
                if item.endswith("_score_ref")
                and item
                in {
                    "material_quality_score_ref",
                    "freshness_score_ref",
                    "business_module_score_ref",
                }
            ],
        )
        for field in (
            "keyword_retrieval_baseline_required",
            "vector_retrieval_baseline_required",
            "vector_similarity_only_prohibited",
            "metadata_filter_contract_required",
            "all_six_metadata_filter_dimensions_required",
            "material_quality_score_contract_required",
            "freshness_score_contract_required",
            "business_module_score_contract_required",
            "all_hybrid_ranking_input_scores_required",
            "hybrid_ranking_contract_required",
            "ranking_policy_contract_required",
            "active_index_version_record_contract_required",
            "retrieval_trace_contract_required",
            "candidate_selected_and_trace_must_reference_active_index_version",
            "selected_result_must_include_score_explanation_ref",
            "selected_result_and_trace_must_include_evidence_ledger_ref",
            "all_values_are_control_labels_only",
        ):
            with self.subTest(field=field):
                self.assertTrue(shape[field])
        self.assertIn(
            "active_index_version_ref",
            shape["future_selected_result_fields"],
        )

    def test_future_runtime_prerequisites_are_defined_without_runtime(self):
        prerequisite = self.contract["future_runtime_prerequisite_contract"]
        for field in (
            "postgresql_full_text_required_for_future_runtime",
            "bm25_style_keyword_scoring_required_for_future_runtime",
            "pgvector_compatible_integration_is_future_authorized_work_only",
            "metadata_filter_runtime_is_future_authorized_work_only",
            "material_quality_scoring_runtime_is_future_authorized_work_only",
            "freshness_scoring_runtime_is_future_authorized_work_only",
            "business_module_scoring_runtime_is_future_authorized_work_only",
            "hybrid_ranking_runtime_is_future_authorized_work_only",
            "future_evidence_ledger_binding_required",
        ):
            with self.subTest(field=field):
                self.assertTrue(prerequisite[field])
        for field, value in prerequisite.items():
            if (
                field.endswith("_created")
                or field.endswith("_performed")
                or field.endswith("_executed")
                or field.endswith("_persisted")
                or field.endswith("_selected")
                or field.endswith("_generated")
                or field.endswith("_evaluated")
            ):
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_failure_and_runtime_boundaries_remain_zero(self):
        failures = self.contract["failure_and_stop_contract"]
        self.assertEqual(failures["failure_state_count"], len(failures["declared_failure_states"]))
        for state in (
            "VECTOR_SIMILARITY_ONLY_NOT_ALLOWED",
            "MATERIAL_QUALITY_SCORE_REFERENCE_MISSING",
            "FRESHNESS_SCORE_REFERENCE_MISSING",
            "BUSINESS_MODULE_SCORE_REFERENCE_MISSING",
            "RANKING_POLICY_REFERENCE_MISSING",
            "CANDIDATE_HYBRID_INPUT_REFERENCE_MISMATCH",
            "EVIDENCE_LEDGER_REFERENCE_MISSING",
            "RETRIEVAL_TRACE_REFERENCE_MISSING",
            "PHASE1_HYBRID_RANKING_NOT_AUTHORIZED",
        ):
            with self.subTest(state=state):
                self.assertIn(state, failures["declared_failure_states"])
        for section in ("runtime_boundary", "protected_surface_boundary"):
            for field, value in self.contract[section].items():
                with self.subTest(section=section, field=field):
                    self.assertFalse(value)
        local_code = self.contract["local_code"]
        self.assertTrue(local_code["static_contract_only"])
        for field, value in local_code.items():
            if field != "static_contract_only":
                with self.subTest(field=field):
                    self.assertFalse(value)

    def test_stage_boundary_and_scope_keep_next_gate_explicit(self):
        boundary = self.contract["stage_and_phase_boundary"]
        for field in (
            "stage085_review_evidence_declared",
            "stage086_started",
            "stage086_entry_authorized",
            "phase1_started",
        ):
            with self.subTest(field=field):
                self.assertTrue(boundary[field])
        for field in (
            "phase2_started",
            "phase3_started",
            "phase4_started",
            "whole_stage_review_performed",
            "stage087_started",
            "github_upload_allowed",
            "push_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(boundary[field])
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "资料质量",
            "新鲜度",
            "业务模块",
            "不得只依赖向量相似度",
            "活动索引版本",
            "检索轨迹",
            "IDS-STAGE086-P2-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_rollback_preserves_predecessor_and_runtime_is_not_authorized(self):
        rollback = self.contract["rollback_contract"]
        self.assertEqual(
            "PASS_REVIEWED_METADATA_FILTER_RUNTIME_DISABLED",
            rollback["return_to"],
        )
        self.assertTrue(rollback["preserve_stage085_review_evidence"])
        for field in (
            "source_or_raw_data_change_allowed",
            "database_or_persistent_state_change_allowed",
            "github_or_ovh_change_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(rollback[field])


if __name__ == "__main__":
    unittest.main()
