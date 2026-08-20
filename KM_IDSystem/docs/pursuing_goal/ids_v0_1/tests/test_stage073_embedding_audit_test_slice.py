import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE073_PHASE2_EMBEDDING_AUDIT_TEST_CONTROL_SLICE.md"
CONTRACT = (
    BASE
    / "embedding_audit_test"
    / "stage073_embedding_audit_test_slice_contract.json"
)
MODULE = (
    BASE
    / "embedding_audit_test"
    / "stage073_embedding_audit_test_slice.py"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-073_Embedding审计测试.md"
)
PHASE1_CONTRACT = (
    BASE
    / "embedding_audit_test"
    / "stage073_embedding_audit_test_contract.json"
)
PREDECESSOR_REVIEW = BASE / "STAGE072_STAGE_REVIEW.md"
PREDECESSOR_MODEL_CONTRACT = (
    BASE
    / "embedding_model_version"
    / "stage072_embedding_model_version_contract.json"
)
PREDECESSOR_AUDIT_CONTRACT = (
    BASE
    / "embedding_cost_governor"
    / "stage071_embedding_cost_governor_contract.json"
)
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"


def _load_module():
    spec = importlib.util.spec_from_file_location("stage073_slice", MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Stage073 P2 control slice")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage073EmbeddingAuditTestPhase2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.phase1_contract = json.loads(PHASE1_CONTRACT.read_text(encoding="utf-8"))
        cls.module = _load_module()

    def test_control_artifacts_exist(self):
        for artifact in (
            SCOPE,
            CONTRACT,
            MODULE,
            TASKPACK,
            PHASE1_CONTRACT,
            PREDECESSOR_REVIEW,
            PREDECESSOR_MODEL_CONTRACT,
            PREDECESSOR_AUDIT_CONTRACT,
            BATCH,
        ):
            with self.subTest(artifact=artifact):
                self.assertTrue(artifact.is_file())

    def test_contract_preserves_single_authority_and_zero_runtime(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage073.embedding_audit_test.phase2.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE073-P2", contract["task_id"])
        self.assertEqual(
            "PHASE2_EMBEDDING_AUDIT_TEST_CONTROL_SLICE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertTrue(contract["slice_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE073-P3-GATE", contract["next_gate"])
        for field in (
            "second_authoritative_source_created",
            "source_body_or_path_allowed",
            "raw_metadata_content_access_allowed",
            "live_source_read_performed",
            "authorized_fixture_access_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(contract["source_authority"][field])
        for field, value in contract["runtime_boundary"].items():
            with self.subTest(field=field):
                self.assertFalse(value)

    def test_contract_shapes_preserve_phase1_policy_and_audit_boundary(self):
        phase1_policy = self.phase1_contract["policy_inheritance_contract"]
        policy = self.contract["policy_inheritance_control_contract"]
        self.assertEqual(
            phase1_policy["allowed_external_api_policy_values"],
            policy["allowed_external_api_policy_values"],
        )
        self.assertEqual(
            phase1_policy["inheritance_path"], policy["inheritance_path"]
        )
        self.assertEqual(2, policy["inheritance_hop_count"])
        self.assertFalse(policy["document_may_widen_data_source_policy"])
        self.assertFalse(policy["chunk_manual_policy_assignment_allowed"])

        input_contract = self.contract[
            "reference_only_embedding_audit_test_input_control_contract"
        ]
        self.assertEqual(20, input_contract["field_count"])
        self.assertEqual(5, input_contract["control_request_count"])
        self.assertFalse(input_contract["source_or_document_body_allowed"])
        self.assertFalse(input_contract["summary_body_allowed"])
        self.assertFalse(input_contract["chunk_text_allowed"])
        self.assertFalse(input_contract["physical_path_or_actual_uri_allowed"])

        dependencies = self.contract["embedding_queue_cache_retry_control_contract"]
        self.assertEqual(12, dependencies["future_queue_field_count"])
        self.assertEqual(10, dependencies["future_cache_field_count"])
        self.assertEqual(7, dependencies["future_failed_retry_field_count"])
        self.assertEqual(5, dependencies["control_projection_count"])

        self.assertEqual(6, self.contract["model_version_control_contract"]["field_count"])
        self.assertEqual(8, self.contract["cost_control_contract"]["field_count"])
        audit = self.contract["external_api_audit_control_contract"]
        self.assertEqual(18, audit["field_count"])
        for field in (
            "provider_ref",
            "model_ref",
            "token_count",
            "chunk_id",
            "policy_inheritance_reason",
        ):
            with self.subTest(field=field):
                self.assertIn(field, audit["required_fields"])
        self.assertTrue(audit["chunk_id_is_an_opaque_control_alias_of_chunk_ref"])
        self.assertFalse(audit["actual_external_api_audit_record_created"])

    def test_fixed_input_is_non_business_and_projection_has_exact_shapes(self):
        control_input = self.module.build_control_input()
        requests = control_input["embedding_audit_test_requests"]
        self.assertEqual(5, len(requests))
        self.assertEqual(
            list(self.module.CONTROL_SCENARIOS),
            self.contract[
                "reference_only_embedding_audit_test_input_control_contract"
            ]["control_request_order"],
        )
        for request in requests:
            self.assertEqual(set(self.module.REFERENCE_INPUT_FIELDS), set(request))
            self.assertEqual(0, request["estimated_token_count"])
            self.assertEqual(0, request["estimated_cost"])
            self.assertFalse(request["sent_to_external_api"])
            self.assertTrue(
                all(
                    isinstance(value, str) and ":control:stage073-p2:" in value
                    for key, value in request.items()
                    if key.endswith("_ref")
                    or key in {"model_version", "dimension", "created_at"}
                )
            )

        result = self.module.execute_embedding_audit_test_control_slice(control_input)
        self.assertTrue(result["input_accepted"])
        self.assertEqual(5, result["control_request_count"])
        self.assertEqual(0, result["actual_input_request_count"])
        self.assertEqual(5, result["policy_resolution_count"])
        self.assertEqual(5, result["embedding_queue_record_count"])
        self.assertEqual(5, result["cache_record_count"])
        self.assertEqual(5, result["failed_retry_record_count"])
        self.assertEqual(5, result["model_version_control_projection_count"])
        self.assertEqual(5, result["cost_control_projection_count"])
        self.assertEqual(5, result["external_api_audit_projection_count"])
        self.assertTrue(result["all_control_records_keep_required_shapes"])
        self.assertTrue(result["all_model_version_sent_statuses_are_false"])
        self.assertTrue(result["control_output_is_not_actual_queue_cache_model_version_cost_or_audit"])

    def test_policy_inheritance_blocks_unauthorized_egress_and_keeps_text_out(self):
        result = self.module.execute_embedding_audit_test_control_slice(
            self.module.build_control_input()
        )
        resolutions = result["policy_resolutions"]
        self.assertEqual("denied", resolutions[0]["effective_external_api_policy"])
        self.assertEqual("summary_only", resolutions[1]["effective_external_api_policy"])
        self.assertEqual("summary_only", resolutions[2]["effective_external_api_policy"])
        self.assertEqual("full_text_allowed", resolutions[3]["effective_external_api_policy"])
        self.assertEqual(
            "CONTROL_INHERITED_FROM_DATA_SOURCE",
            resolutions[1]["policy_inheritance_reason"],
        )
        self.assertEqual(
            "CONTROL_DOCUMENT_POLICY_RESTRICTED_EFFECTIVE",
            resolutions[2]["policy_inheritance_reason"],
        )
        self.assertEqual(
            "NO_EXTERNAL_PAYLOAD_POLICY_DENIED",
            resolutions[0]["external_payload_mode"],
        )
        self.assertEqual(
            "FUTURE_AUTHORIZED_SUMMARY_REFERENCE_ONLY",
            resolutions[1]["external_payload_mode"],
        )
        self.assertEqual(
            "FUTURE_AUTHORIZED_CHUNK_TEXT_REFERENCE_ONLY",
            resolutions[3]["external_payload_mode"],
        )
        self.assertEqual(1, result["control_queue_blocked_policy_denied_count"])
        self.assertEqual(1, result["control_queue_paused_budget_insufficient_count"])
        self.assertFalse(result["external_payload_created"])
        self.assertFalse(result["external_api_call_performed"])
        self.assertFalse(result["model_token_consumption_performed"])

    def test_model_cost_and_audit_control_projections_keep_values_non_actual(self):
        result = self.module.execute_embedding_audit_test_control_slice(
            self.module.build_control_input()
        )
        for record in result["model_version_control_projections"]:
            self.assertEqual(set(self.module.MODEL_VERSION_FIELDS), set(record))
            self.assertFalse(record["sent_to_external_api"])
            self.assertTrue(record["provider_ref"].startswith("provider:control:"))
            self.assertTrue(record["model_ref"].startswith("model:control:"))
        for record in result["cost_control_projections"]:
            self.assertEqual(set(self.module.COST_FIELDS), set(record))
            self.assertEqual(0, record["estimated_token_count"])
            self.assertEqual(0, record["estimated_cost"])
        for record in result["external_api_audit_projections"]:
            self.assertEqual(set(self.module.AUDIT_FIELDS), set(record))
            self.assertEqual(0, record["token_count"])
            self.assertTrue(record["chunk_id"].startswith("chunk:control:"))
            self.assertIn("CONTROL_", record["policy_inheritance_reason"])
        self.assertFalse(result["actual_model_version_record_created"])
        self.assertFalse(result["actual_external_api_audit_record_created"])
        self.assertFalse(result["persistent_state_write_performed"])

    def test_tampered_or_reordered_input_fails_closed(self):
        tampered = copy.deepcopy(self.module.build_control_input())
        tampered["embedding_audit_test_requests"][0]["provider_ref"] = "provider:tampered"
        result = self.module.execute_embedding_audit_test_control_slice(tampered)
        self.assertFalse(result["input_accepted"])
        self.assertEqual("REJECTED", result["execution_state"])
        self.assertEqual(0, result["embedding_queue_record_count"])
        self.assertEqual(0, result["external_api_audit_projection_count"])
        self.assertFalse(result["external_api_call_performed"])

        reordered = self.module.build_control_input()
        reordered["embedding_audit_test_requests"].reverse()
        self.assertFalse(
            self.module.execute_embedding_audit_test_control_slice(reordered)[
                "input_accepted"
            ]
        )

    def test_policy_parser_fails_closed_for_invalid_or_widened_values(self):
        self.assertEqual(
            ("denied", "CONTROL_SOURCE_POLICY_INVALID_FAIL_CLOSED"),
            self.module.resolve_effective_policy("unknown", None),
        )
        self.assertEqual(
            ("denied", "CONTROL_DOCUMENT_POLICY_INVALID_FAIL_CLOSED"),
            self.module.resolve_effective_policy("summary_only", "unknown"),
        )
        self.assertEqual(
            ("denied", "CONTROL_DOCUMENT_POLICY_WIDENING_BLOCKED"),
            self.module.resolve_effective_policy("summary_only", "full_text_allowed"),
        )

    def test_scope_explains_authority_and_next_gate(self):
        text = SCOPE.read_text(encoding="utf-8")
        for phrase in (
            "不建立第二权威事实源",
            "未授权 chunk 不会外发",
            "不调用外部 API",
            "IDS-STAGE073-P3-GATE",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
