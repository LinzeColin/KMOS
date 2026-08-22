import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
SCOPE = BASE / "STAGE077_PHASE2_BACKGROUND_INDEX_BUILD_CONTROL_SLICE.md"
CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage077_background_index_build_slice_contract.json"
)
MODULE = (
    BASE
    / "index_version_schema"
    / "stage077_background_index_build_slice.py"
)
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-077_后台索引构建.md"
)
PHASE1_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage077_background_index_build_contract.json"
)
PREDECESSOR_REVIEW = BASE / "STAGE076_STAGE_REVIEW.md"
PREDECESSOR_CONTRACT = (
    BASE
    / "index_version_schema"
    / "stage076_index_version_schema_contract.json"
)
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-21-stage077-p2-local.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("stage077_slice", MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Stage077 P2 control slice")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage077BackgroundIndexBuildPhase2Tests(unittest.TestCase):
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

    def test_contract_reuses_phase1_and_keeps_runtime_closed(self):
        contract = self.contract
        self.assertEqual(
            "ids.stage077.background_index_build.phase2.v1",
            contract["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE077-P2", contract["task_id"])
        self.assertEqual(
            "PHASE2_BACKGROUND_INDEX_BUILD_CONTROL_SLICE_RUNTIME_DISABLED",
            contract["contract_state"],
        )
        self.assertTrue(contract["slice_executable"])
        self.assertFalse(contract["execution_ready"])
        self.assertEqual("IDS-STAGE077-P3-GATE", contract["next_gate"])
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

        phase1_io = self.phase1_contract["background_build_input_output_contract"]
        reuse = contract["phase1_reuse_contract"]
        self.assertEqual(
            phase1_io["future_required_input_fields"],
            reuse["future_required_input_fields"],
        )
        self.assertEqual(
            phase1_io["future_required_output_fields"],
            reuse["future_required_output_fields"],
        )
        self.assertEqual(
            self.phase1_contract["smoke_and_atomic_switch_contract"][
                "required_conditions"
            ],
            reuse["required_smoke_test_conditions"],
        )
        self.assertFalse(
            self.phase1_contract["stage_and_phase_boundary"]["phase2_started"]
        )

    def test_fixed_control_input_and_projection_shapes(self):
        control_input = self.module.build_control_input()
        requests = control_input["background_index_build_requests"]
        self.assertEqual(5, len(requests))
        self.assertEqual(
            list(self.module.CONTROL_SCENARIOS),
            self.contract["reference_only_control_input_contract"][
                "control_request_order"
            ],
        )
        for request in requests:
            self.assertEqual(set(self.module.INPUT_FIELDS), set(request))
            self.assertEqual(0, request["chunk_count"])
            self.assertTrue(
                all(
                    ":control:stage077-p2:" in value
                    for key, value in request.items()
                    if key.endswith("_ref")
                )
            )

        result = self.module.execute_background_index_build_control_slice(control_input)
        self.assertTrue(result["input_accepted"])
        self.assertEqual(5, result["control_request_count"])
        self.assertEqual(0, result["actual_input_request_count"])
        for name in (
            "index_version_control_record_count",
            "building_version_control_record_count",
            "active_pointer_control_projection_count",
            "background_build_output_control_projection_count",
            "smoke_test_control_projection_count",
            "switch_control_projection_count",
            "rollback_control_projection_count",
        ):
            with self.subTest(name=name):
                self.assertEqual(5, result[name])
        self.assertTrue(result["all_control_records_keep_required_shapes"])
        self.assertTrue(
            result["control_output_is_not_actual_index_database_or_retrieval"]
        )

    def test_versions_building_outputs_and_active_pointer_keep_invariants(self):
        result = self.module.execute_background_index_build_control_slice(
            self.module.build_control_input()
        )
        for record in result["index_version_control_records"]:
            self.assertEqual(
                set(self.module.INDEX_VERSION_RECORD_FIELDS),
                set(record),
            )
            self.assertIn(record["index_kind"], self.module.INDEX_KINDS)
            self.assertEqual(0, record["chunk_count"])
        for record in result["building_version_control_records"]:
            self.assertEqual(set(self.module.BUILDING_VERSION_FIELDS), set(record))
            self.assertIn(":control:stage077-p2:", record["shadow_index_ref"])
        for record in result["background_build_output_control_projections"]:
            self.assertEqual(
                set(self.module.BACKGROUND_BUILD_OUTPUT_FIELDS),
                set(record),
            )
        for record in result["active_pointer_control_projections"]:
            self.assertEqual(set(self.module.ACTIVE_POINTER_FIELDS), set(record))
            self.assertEqual(
                "CONTROL_ACTIVE_POINTER_UNCHANGED_RUNTIME_DISABLED",
                record["pointer_state"],
            )
        self.assertTrue(result["all_candidate_versions_differ_from_active_versions"])
        self.assertTrue(result["all_shadow_candidates_are_isolated_from_active_service"])
        self.assertTrue(result["all_active_versions_continue_serving_during_control_build"])
        self.assertEqual(1, result["control_background_building_count"])

    def test_smoke_switch_and_rollback_controls_fail_closed(self):
        result = self.module.execute_background_index_build_control_slice(
            self.module.build_control_input()
        )
        smoke_tests = {
            projection["smoke_test_ref"].split(":")[-1]: projection
            for projection in result["smoke_test_control_projections"]
        }
        self.assertEqual(
            6,
            len(
                result["smoke_test_control_projections"][0]["required_conditions"]
            ),
        )
        self.assertFalse(
            smoke_tests["vector_background_building_keeps_active"]["switch_eligible"]
        )
        self.assertFalse(
            smoke_tests["hybrid_smoke_test_failure_blocks_switch"]["switch_eligible"]
        )
        self.assertTrue(result["all_failed_or_pending_smoke_tests_block_switch"])

        switches = {
            projection["control_scenario"]: projection
            for projection in result["switch_control_projections"]
        }
        self.assertEqual(
            "CONTROL_ATOMIC_SWITCH_PROJECTED_NOT_APPLIED",
            switches["fulltext_smoke_passed_switch_candidate"]["switch_outcome"],
        )
        self.assertEqual(
            "CONTROL_SWITCH_FAILED_ACTIVE_UNCHANGED",
            switches["fulltext_switch_failure_preserves_active"]["switch_outcome"],
        )
        self.assertTrue(
            all(not projection["switch_applied"] for projection in switches.values())
        )
        self.assertEqual(1, result["control_switch_failure_count"])
        self.assertTrue(result["all_switch_projections_keep_active_pointer_unchanged"])
        rollback = {
            projection["control_scenario"]: projection
            for projection in result["rollback_control_projections"]
        }["hybrid_rollback_candidate_retains_previous"]
        self.assertEqual(
            rollback["previous_active_index_version_ref"],
            rollback["rollback_target_index_version_ref"],
        )
        self.assertFalse(rollback["rollback_applied"])
        self.assertTrue(result["all_rollback_targets_reference_retained_previous_active"])

    def test_tampered_reordered_and_widened_input_is_rejected(self):
        tampered = copy.deepcopy(self.module.build_control_input())
        tampered["background_index_build_requests"][0]["embedding_model_ref"] = (
            "embedding-model:tampered"
        )
        result = self.module.execute_background_index_build_control_slice(tampered)
        self.assertFalse(result["input_accepted"])
        self.assertEqual("REJECTED", result["execution_state"])
        self.assertEqual(0, result["index_version_control_record_count"])
        self.assertFalse(result["actual_background_build_started"])

        reordered = self.module.build_control_input()
        reordered["background_index_build_requests"].reverse()
        self.assertFalse(
            self.module.execute_background_index_build_control_slice(reordered)[
                "input_accepted"
            ]
        )

        widened = self.module.build_control_input()
        widened["extra"] = "not-authorized"
        self.assertFalse(
            self.module.execute_background_index_build_control_slice(widened)[
                "input_accepted"
            ]
        )

    def test_runtime_remains_zero_and_chinese_feedback_is_present(self):
        result = self.module.execute_background_index_build_control_slice(
            self.module.build_control_input()
        )
        for field in self.module._runtime_closed_flags():
            with self.subTest(field=field):
                self.assertFalse(result[field])
        self.assertEqual(4, len(result["chinese_feedback"]))
        self.assertTrue(
            all(
                any("\u4e00" <= char <= "\u9fff" for char in message)
                for message in result["chinese_feedback"]
            )
        )

    def test_phase2_evidence_preserves_phase1_and_advances_only_to_p3_gate(self):
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
                    "IDS-STAGE077",
                    "IDS-V0_1-STAGE077-P2",
                    "IDS-V0_1-STAGE077-P2",
                    "IDS-STAGE077-P3-GATE",
                ),
                (
                    "IDS-STAGE077",
                    "IDS-V0_1-STAGE077-P3",
                    "IDS-V0_1-STAGE077-P3",
                    "IDS-STAGE077-P4-GATE",
                ),
                (
                    "IDS-STAGE077",
                    "IDS-V0_1-STAGE077-P4",
                    "IDS-V0_1-STAGE077-P4",
                    "IDS-STAGE077-REVIEW-GATE",
                ),
                (
                    "IDS-STAGE077",
                    "IDS-V0_1-STAGE077-REVIEW",
                    "IDS-V0_1-STAGE077-REVIEW",
                    "IDS-STAGE078-P1-GATE",
                ),
             ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P1', 'IDS-V0_1-STAGE078-P1', 'IDS-STAGE078-P2-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P2', 'IDS-V0_1-STAGE078-P2', 'IDS-STAGE078-P3-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P3', 'IDS-V0_1-STAGE078-P3', 'IDS-STAGE078-P4-GATE'), ('IDS-STAGE078', 'IDS-V0_1-STAGE078-P4', 'IDS-V0_1-STAGE078-P4', 'IDS-STAGE078-REVIEW-GATE'), ('IDS-STAGE078', 'IDS-STAGE078-REVIEW', 'IDS-V0_1-STAGE078-REVIEW', 'IDS-STAGE079-P1-GATE'),
                ("IDS-STAGE079", "IDS-V0_1-STAGE079-P1", "IDS-V0_1-STAGE079-P1", "IDS-STAGE079-P2-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P2", "IDS-STAGE079-P3-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P3", "IDS-STAGE079-P4-GATE"), ("IDS-STAGE079", "IDS-V0_1-STAGE079-P4", "IDS-V0_1-STAGE079-P4", "IDS-STAGE079-REVIEW-GATE"),
                    ('IDS-STAGE079', 'IDS-STAGE079-REVIEW', 'IDS-V0_1-STAGE079-REVIEW', 'IDS-STAGE080-P1-GATE'),

                ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P1', 'IDS-V0_1-STAGE080-P1', 'IDS-STAGE080-P2-GATE'),
                ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P2', 'IDS-V0_1-STAGE080-P2', 'IDS-STAGE080-P3-GATE'), ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P3', 'IDS-STAGE080-P4-GATE'), ('IDS-STAGE080', 'IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-P4', 'IDS-STAGE080-REVIEW-GATE'), ('IDS-STAGE080', 'IDS-STAGE080-REVIEW', 'IDS-V0_1-STAGE080-REVIEW', 'IDS-STAGE081-P1-GATE'), ("IDS-STAGE081", "IDS-STAGE081-P1", "IDS-V0_1-STAGE081-P1", "IDS-STAGE081-P2-GATE"), ("IDS-STAGE081", "IDS-STAGE081-P2", "IDS-V0_1-STAGE081-P2", "IDS-STAGE081-P3-GATE"), ("IDS-STAGE081", "IDS-STAGE081-P3", "IDS-V0_1-STAGE081-P3", "IDS-STAGE081-P4-GATE"), ("IDS-STAGE081", "IDS-STAGE081-P4", "IDS-V0_1-STAGE081-P4", "IDS-STAGE081-REVIEW-GATE"), ("IDS-STAGE081", "IDS-STAGE081-REVIEW", "IDS-V0_1-STAGE081-REVIEW", "IDS-STAGE082-P1-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P1", "IDS-V0_1-STAGE082-P1", "IDS-STAGE082-P2-GATE"),
                ("IDS-STAGE082", "IDS-STAGE082-P2", "IDS-V0_1-STAGE082-P2", "IDS-STAGE082-P3-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P3", "IDS-V0_1-STAGE082-P3", "IDS-STAGE082-P4-GATE"), ("IDS-STAGE082", "IDS-STAGE082-P4", "IDS-V0_1-STAGE082-P4", "IDS-STAGE082-REVIEW-GATE"),
                ("IDS-STAGE082", "IDS-STAGE082-REVIEW", "IDS-V0_1-STAGE082-REVIEW", "IDS-STAGE083-P1-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P1", "IDS-V0_1-STAGE083-P1", "IDS-STAGE083-P2-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P2", "IDS-V0_1-STAGE083-P2", "IDS-STAGE083-P3-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P3", "IDS-V0_1-STAGE083-P3", "IDS-STAGE083-P4-GATE"), ("IDS-STAGE083", "IDS-STAGE083-P4", "IDS-V0_1-STAGE083-P4", "IDS-STAGE083-REVIEW-GATE"), ("IDS-STAGE083", "IDS-STAGE083-REVIEW", "IDS-V0_1-STAGE083-REVIEW", "IDS-STAGE084-P1-GATE"), ("IDS-STAGE084", "IDS-STAGE084-P1", "IDS-V0_1-STAGE084-P1", "IDS-STAGE084-P2-GATE"), ("IDS-STAGE084", "IDS-STAGE084-P2", "IDS-V0_1-STAGE084-P2", "IDS-STAGE084-P3-GATE"), ('IDS-STAGE084', 'IDS-STAGE084-P3', 'IDS-V0_1-STAGE084-P3', 'IDS-STAGE084-P4-GATE'), ('IDS-STAGE084', 'IDS-STAGE084-P4', 'IDS-V0_1-STAGE084-P4', 'IDS-STAGE084-REVIEW-GATE'),
                    ('IDS-STAGE084', 'IDS-STAGE084-REVIEW', 'IDS-V0_1-STAGE084-REVIEW', 'IDS-STAGE085-P3-GATE'),

                ('IDS-STAGE085', 'IDS-STAGE085-P2', 'IDS-V0_1-STAGE085-P2', 'IDS-STAGE085-P3-GATE'), ("IDS-STAGE085", "IDS-STAGE085-P3", "IDS-V0_1-STAGE085-P3", "IDS-STAGE085-P4-GATE"), ("IDS-STAGE085", "IDS-STAGE085-P4", "IDS-V0_1-STAGE085-P4", "IDS-STAGE085-REVIEW-GATE"),
            ),
        )
        self.assertFalse(status["runtime_enabled"])
        self.assertFalse(status["push_allowed"])
        self.assertIn(
            plan["task"],
            (
                "IDS-V0_1-STAGE077-P2",
                "IDS-V0_1-STAGE077-P3",
                "IDS-V0_1-STAGE077-P4",
                "IDS-V0_1-STAGE077-REVIEW",
             "IDS-V0_1-STAGE078-P1", "IDS-V0_1-STAGE078-P2", "IDS-V0_1-STAGE078-P3", "IDS-V0_1-STAGE078-P4", "IDS-V0_1-STAGE078-REVIEW",
                "IDS-V0_1-STAGE079-P1",
                "IDS-V0_1-STAGE079-P2", "IDS-V0_1-STAGE079-P3", "IDS-V0_1-STAGE079-P4",
                    'IDS-V0_1-STAGE079-REVIEW',

                'IDS-V0_1-STAGE080-P1',

                'IDS-V0_1-STAGE080-P2',
                'IDS-V0_1-STAGE080-P3', 'IDS-V0_1-STAGE080-P4', 'IDS-V0_1-STAGE080-REVIEW', 'IDS-V0_1-STAGE081-P1', 'IDS-V0_1-STAGE081-P2', 'IDS-V0_1-STAGE081-P3', 'IDS-V0_1-STAGE081-P4', 'IDS-V0_1-STAGE081-REVIEW', 'IDS-V0_1-STAGE082-P1',
                'IDS-V0_1-STAGE082-P2',
                'IDS-V0_1-STAGE082-P3', 'IDS-V0_1-STAGE082-P4', "IDS-V0_1-STAGE082-REVIEW", "IDS-V0_1-STAGE083-P1", "IDS-V0_1-STAGE083-P2", "IDS-V0_1-STAGE083-P3", "IDS-V0_1-STAGE083-P4", "IDS-V0_1-STAGE083-REVIEW", "IDS-V0_1-STAGE084-P1", 'IDS-V0_1-STAGE084-P2', 'IDS-V0_1-STAGE084-P3', 'IDS-V0_1-STAGE084-P4',
                    'IDS-V0_1-STAGE084-REVIEW',

                'IDS-V0_1-STAGE085-P2',
             "IDS-V0_1-STAGE085-P3", "IDS-V0_1-STAGE085-P4"),
        )
        self.assertIn("不建立第二权威事实源", "\n".join(plan["scope"]))
        acceptance_ids = {item["id"] for item in acceptance["items"]}
        self.assertTrue(
            {
                "ACC-STAGE077-P1-01",
                "ACC-STAGE077-P1-02",
                "ACC-STAGE077-P1-03",
                "ACC-STAGE077-P1-04",
                "ACC-STAGE077-P2-01",
                "ACC-STAGE077-P2-02",
                "ACC-STAGE077-P2-03",
                "ACC-STAGE077-P2-04",
            }.issubset(acceptance_ids)
        )
        self.assertEqual("IDS-V0_1-STAGE077-P2", run["task_id"])
        self.assertEqual(
            "PASS_BACKGROUND_INDEX_BUILD_CONTROL_SLICE_RUNTIME_DISABLED",
            run["result"],
        )
        self.assertEqual(0, run["runtime_counts"]["actual_background_build_count"])
        self.assertEqual(0, run["runtime_counts"]["actual_model_token_count"])
        self.assertFalse(run["runtime_actions"]["ovh_deployment_performed"])
        self.assertIn("EVT-IDS-V0_1-STAGE077-P2-20260821-001", event_ids)


if __name__ == "__main__":
    unittest.main()
