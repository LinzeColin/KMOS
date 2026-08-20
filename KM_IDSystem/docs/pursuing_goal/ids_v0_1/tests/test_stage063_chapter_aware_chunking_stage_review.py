import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
TASKPACK = (
    ROOT
    / "docs"
    / "taskpacks"
    / "IDS_v0_1_Final_Chinese_Revised"
    / "stages"
    / "STAGE-063_章节感知切块.md"
)
REVIEW_DOCUMENT = BASE / "STAGE063_STAGE_REVIEW.md"
MODULE = (
    BASE
    / "chapter_aware_chunking"
    / "stage063_chapter_aware_chunking_stage_review.py"
)
PHASE1_CONTRACT = (
    BASE / "chapter_aware_chunking" / "stage063_chapter_aware_chunking_contract.json"
)
PHASE2_CONTRACT = (
    BASE / "chapter_aware_chunking" / "stage063_chapter_aware_chunking_slice_contract.json"
)
PHASE3_CONTRACT = (
    BASE / "chapter_aware_chunking" / "stage063_chapter_aware_chunking_scenarios_contract.json"
)
PHASE4_CONTRACT = (
    BASE / "chapter_aware_chunking" / "stage063_chapter_aware_chunking_delivery_contract.json"
)
P3_MODULE = (
    BASE / "chapter_aware_chunking" / "stage063_chapter_aware_chunking_scenarios.py"
)
P4_MODULE = (
    BASE / "chapter_aware_chunking" / "stage063_chapter_aware_chunking_delivery.py"
)
BATCH = BASE / "BATCH061_070_UPLOAD_LOCK.yaml"
ROADMAP = ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = ROOT / "docs" / "governance" / "events.jsonl"
STATUS = ROOT / "machine" / "facts" / "status.json"
PLAN = ROOT / "machine" / "facts" / "plan.json"
ACCEPTANCE = ROOT / "machine" / "facts" / "acceptance.json"
RUN = ROOT / "machine" / "runs" / "2026-08-14-stage063-review-local.json"


class Stage063ChapterAwareChunkingStageReviewTests(unittest.TestCase):
    _module_value = None
    _report_value = None

    def _module(self):
        if self.__class__._module_value is None:
            spec = importlib.util.spec_from_file_location("stage063_review", MODULE)
            module = importlib.util.module_from_spec(spec)
            self.assertIsNotNone(spec.loader)
            spec.loader.exec_module(module)
            self.__class__._module_value = module
        return self.__class__._module_value

    def _report(self):
        if self.__class__._report_value is None:
            self.__class__._report_value = self._module().build_stage063_review_report()
        return self.__class__._report_value

    def test_review_artifacts_exist(self):
        for artifact in (
            TASKPACK,
            REVIEW_DOCUMENT,
            MODULE,
            PHASE1_CONTRACT,
            PHASE2_CONTRACT,
            PHASE3_CONTRACT,
            PHASE4_CONTRACT,
            P3_MODULE,
            P4_MODULE,
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

    def test_review_passes_all_phase_contracts(self):
        report = self._report()
        self.assertEqual(
            "ids.stage063.chapter_aware_chunking.stage_review.v1",
            report["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE063-REVIEW", report["task_id"])
        self.assertEqual("ACC-STAGE-063", report["acceptance_id"])
        self.assertTrue(report["review_valid"])
        self.assertEqual(
            "PASS_REVIEWED_LOCAL_CHAPTER_AWARE_CHUNKING_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual("IDS-STAGE064-P1-GATE", report["next_gate"])
        self.assertEqual({"P1": True, "P2": True, "P3": True, "P4": True}, report["phase_results"])

    def test_review_replays_fixed_control_counts(self):
        replay = self._report()["controlled_replay"]
        self.assertEqual(8, replay["phase1_reference_only_input_field_count"])
        self.assertEqual(14, replay["phase1_future_chunk_output_field_count"])
        self.assertEqual(3, replay["phase2_control_request_count"])
        self.assertEqual(3, replay["phase2_control_candidate_count"])
        self.assertEqual(18, replay["phase2_control_traceability_reference_count"])
        self.assertEqual(6, replay["phase3_controlled_scenario_count"])
        self.assertEqual(6, replay["phase3_explicit_disposition_count"])
        self.assertEqual(0, replay["phase3_silent_drop_count"])
        self.assertEqual(6, replay["phase4_chunk_jsonl_sample_count"])
        self.assertEqual(6, replay["phase4_low_quality_control_record_count"])
        self.assertEqual(3, replay["phase4_human_confirmation_prompt_count"])

    def test_review_preserves_boundaries_and_p4_to_p3_rollback(self):
        report = self._report()
        self.assertTrue(all(report["review_invariants"].values()))
        self.assertEqual(
            "PHASE3_CHAPTER_AWARE_CHUNKING_CONTROLLED_SCENARIOS_RUNTIME_DISABLED",
            report["controlled_replay"]["phase4_return_to"],
        )
        self.assertEqual(
            "PHASE4_CHAPTER_AWARE_CHUNKING_DELIVERY_EVIDENCE_RUNTIME_DISABLED",
            report["rollback"]["return_to"],
        )
        self.assertTrue(report["rollback"]["preserve_phase1_to_phase4_evidence"])
        self.assertFalse(report["rollback"]["github_or_ovh_change_allowed"])

    def test_review_keeps_runtime_and_stage064_closed(self):
        report = self._report()
        for field in (
            "ids_business_source_read_performed",
            "raw_metadata_content_accessed",
            "authorized_fixture_access_performed",
            "source_file_open_performed",
            "parser_execution_performed",
            "chapter_detection_performed",
            "chunking_execution_performed",
            "embedding_or_index_write_performed",
            "database_connection_performed",
            "persistent_state_write_performed",
            "agent_execution_performed",
            "model_call_performed",
            "model_token_consumption_performed",
            "local_service_start_performed",
            "ovh_deployment_performed",
            "production_runtime_activation_performed",
            "stage064_started",
            "stage064_entry_allowed",
            "github_upload_performed",
            "push_performed",
        ):
            with self.subTest(field=field):
                self.assertFalse(report[field])
        self.assertTrue(report["whole_stage_review_performed"])

    def test_invalid_phase1_contract_fails_closed(self):
        report = self._module().build_stage063_review_report(
            phase1_contract_provider=lambda: {"task_id": "tampered"}
        )
        self.assertFalse(report["review_valid"])
        self.assertEqual(
            "FAIL_REVIEWED_LOCAL_CHAPTER_AWARE_CHUNKING_RUNTIME_DISABLED",
            report["result"],
        )
        self.assertEqual("IDS-STAGE063-REVIEW-GATE", report["next_gate"])

    def test_invalid_phase4_contract_fails_closed(self):
        report = self._module().build_stage063_review_report(
            phase4_contract_provider=lambda: {"task_id": "tampered"}
        )
        self.assertFalse(report["review_valid"])
        self.assertFalse(report["phase_results"]["P4"])
        self.assertEqual("IDS-STAGE063-REVIEW-GATE", report["next_gate"])

    def test_governance_projection_records_stage_review(self):
        status = json.loads(STATUS.read_text(encoding="utf-8"))
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
        run = json.loads(RUN.read_text(encoding="utf-8"))
        events = [
            json.loads(line)
            for line in EVENTS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertIn(
            (status["stage"], status["phase"], status["task"], status["next_gate"]),
            (
                ("IDS-STAGE063", "IDS-V0_1-STAGE063-REVIEW", "IDS-V0_1-STAGE063-REVIEW", "IDS-STAGE064-P1-GATE"),
                ("IDS-STAGE064", "IDS-V0_1-STAGE064-P1", "IDS-V0_1-STAGE064-P1", "IDS-STAGE064-P2-GATE"),
                ("IDS-STAGE064", "IDS-V0_1-STAGE064-P2", "IDS-V0_1-STAGE064-P2", "IDS-STAGE064-P3-GATE"),
                ("IDS-STAGE064", "IDS-V0_1-STAGE064-P3", "IDS-V0_1-STAGE064-P3", "IDS-STAGE064-P4-GATE"),
                ("IDS-STAGE064", "IDS-V0_1-STAGE064-P4", "IDS-V0_1-STAGE064-P4", "IDS-STAGE064-REVIEW-GATE"),
                ("IDS-STAGE064", "IDS-V0_1-STAGE064-REVIEW", "IDS-V0_1-STAGE064-REVIEW", "IDS-STAGE065-P1-GATE"),
                ("IDS-STAGE065", "IDS-V0_1-STAGE065-P1", "IDS-V0_1-STAGE065-P1", "IDS-STAGE065-P2-GATE"),
                ("IDS-STAGE065", "IDS-V0_1-STAGE065-P2", "IDS-V0_1-STAGE065-P2", "IDS-STAGE065-P3-GATE"),
                ("IDS-STAGE065", "IDS-V0_1-STAGE065-P3", "IDS-V0_1-STAGE065-P3", "IDS-STAGE065-P4-GATE"),
                ("IDS-STAGE065", "IDS-V0_1-STAGE065-P4", "IDS-V0_1-STAGE065-P4", "IDS-STAGE065-REVIEW-GATE"),
                ("IDS-STAGE065", "IDS-V0_1-STAGE065-REVIEW", "IDS-V0_1-STAGE065-REVIEW", "IDS-STAGE066-P1-GATE"),
                ("IDS-STAGE066", "IDS-V0_1-STAGE066-P1", "IDS-V0_1-STAGE066-P1", "IDS-STAGE066-P2-GATE"),
                ("IDS-STAGE066", "IDS-V0_1-STAGE066-P2", "IDS-V0_1-STAGE066-P2", "IDS-STAGE066-P3-GATE"),
                ("IDS-STAGE066", "IDS-V0_1-STAGE066-P3", "IDS-V0_1-STAGE066-P3", "IDS-STAGE066-P4-GATE"),
                ("IDS-STAGE066", "IDS-V0_1-STAGE066-P4", "IDS-V0_1-STAGE066-P4", "IDS-STAGE066-REVIEW-GATE"),
                ("IDS-STAGE066", "IDS-STAGE066-REVIEW", "IDS-V0_1-STAGE066-REVIEW", "IDS-STAGE067-P1-GATE"),
                ("IDS-STAGE067", "IDS-V0_1-STAGE067-P1", "IDS-V0_1-STAGE067-P1", "IDS-STAGE067-P2-GATE"), ("IDS-STAGE067", "IDS-V0_1-STAGE067-P2", "IDS-V0_1-STAGE067-P2", "IDS-STAGE067-P3-GATE"),
            ("IDS-STAGE067", "IDS-V0_1-STAGE067-P3", "IDS-V0_1-STAGE067-P3", "IDS-STAGE067-P4-GATE"),
            ("IDS-STAGE067", "IDS-V0_1-STAGE067-P4", "IDS-V0_1-STAGE067-P4", "IDS-STAGE067-REVIEW-GATE"),
                ("IDS-STAGE067", "IDS-V0_1-STAGE067-REVIEW", "IDS-V0_1-STAGE067-REVIEW", "IDS-STAGE068-P1-GATE"),
                ("IDS-STAGE067", "IDS-V0_1-STAGE067-P4", "IDS-V0_1-STAGE067-P4", "IDS-STAGE067-REVIEW-GATE"),
                ("IDS-STAGE067", "IDS-V0_1-STAGE067-REVIEW", "IDS-V0_1-STAGE067-REVIEW", "IDS-STAGE068-P1-GATE"),
                ("IDS-STAGE068", "IDS-V0_1-STAGE068-P1", "IDS-V0_1-STAGE068-P1", "IDS-STAGE068-P2-GATE"),
                ("IDS-STAGE068", "IDS-V0_1-STAGE068-P2", "IDS-V0_1-STAGE068-P2", "IDS-STAGE068-P3-GATE"),
                ("IDS-STAGE068", "IDS-V0_1-STAGE068-P3", "IDS-V0_1-STAGE068-P3", "IDS-STAGE068-P4-GATE"),
                ("IDS-STAGE068", "IDS-V0_1-STAGE068-P4", "IDS-V0_1-STAGE068-P4", "IDS-STAGE068-REVIEW-GATE"),
                ("IDS-STAGE068", "IDS-V0_1-STAGE068-REVIEW", "IDS-V0_1-STAGE068-REVIEW", "IDS-STAGE069-P1-GATE"),
                ("IDS-STAGE069", "IDS-V0_1-STAGE069-P1", "IDS-V0_1-STAGE069-P1", "IDS-STAGE069-P2-GATE"),
                ("IDS-STAGE069", "IDS-V0_1-STAGE069-P2", "IDS-V0_1-STAGE069-P2", "IDS-STAGE069-P3-GATE"),
                ("IDS-STAGE069", "IDS-V0_1-STAGE069-P3", "IDS-V0_1-STAGE069-P3", "IDS-STAGE069-P4-GATE"),
                ("IDS-STAGE069", "IDS-V0_1-STAGE069-P4", "IDS-V0_1-STAGE069-P4", "IDS-STAGE069-REVIEW-GATE"),
                ("IDS-STAGE070", "IDS-V0_1-STAGE070-P1", "IDS-V0_1-STAGE070-P1", "IDS-STAGE070-P2-GATE"),
                ("IDS-STAGE070", "IDS-V0_1-STAGE070-P2", "IDS-V0_1-STAGE070-P2", "IDS-STAGE070-P3-GATE"),
                ("IDS-STAGE070", "IDS-V0_1-STAGE070-P3", "IDS-V0_1-STAGE070-P3", "IDS-STAGE070-P4-GATE"),
                ("IDS-STAGE070", "IDS-V0_1-STAGE070-P4", "IDS-V0_1-STAGE070-P4", "IDS-STAGE070-REVIEW-GATE"),
                ("IDS-STAGE070", "IDS-V0_1-STAGE070-REVIEW", "IDS-V0_1-STAGE070-REVIEW", "IDS-STAGE071-P1-GATE"),
                ("IDS-STAGE071", "IDS-V0_1-STAGE071-P1", "IDS-V0_1-STAGE071-P1", "IDS-STAGE071-P2-GATE"),
                ("IDS-STAGE071", "IDS-V0_1-STAGE071-P2", "IDS-V0_1-STAGE071-P2", "IDS-STAGE071-P3-GATE"),
                ("IDS-STAGE071", "IDS-V0_1-STAGE071-P3", "IDS-V0_1-STAGE071-P3", "IDS-STAGE071-P4-GATE"),
                ("IDS-STAGE071", "IDS-V0_1-STAGE071-P4", "IDS-V0_1-STAGE071-P4", "IDS-STAGE071-REVIEW-GATE"),
                ("IDS-STAGE071", "IDS-V0_1-STAGE071-REVIEW", "IDS-V0_1-STAGE071-REVIEW", "IDS-STAGE072-P1-GATE"),
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-P1", "IDS-V0_1-STAGE072-P1", "IDS-STAGE072-P2-GATE"),
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-P2", "IDS-V0_1-STAGE072-P2", "IDS-STAGE072-P3-GATE"),
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-P3", "IDS-V0_1-STAGE072-P3", "IDS-STAGE072-P4-GATE"),
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-P4", "IDS-V0_1-STAGE072-P4", "IDS-STAGE072-REVIEW-GATE"),
                ("IDS-STAGE072", "IDS-V0_1-STAGE072-REVIEW", "IDS-V0_1-STAGE072-REVIEW", "IDS-STAGE073-P1-GATE"),
                ("IDS-STAGE073", "IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P1", "IDS-STAGE073-P2-GATE"), ("IDS-STAGE073", "IDS-V0_1-STAGE073-P2", "IDS-V0_1-STAGE073-P2", "IDS-STAGE073-P3-GATE"),
                ("IDS-STAGE069", "IDS-V0_1-STAGE069-REVIEW", "IDS-V0_1-STAGE069-REVIEW", "IDS-STAGE070-P1-GATE"), ('IDS-STAGE073', 'IDS-V0_1-STAGE073-P3', 'IDS-V0_1-STAGE073-P3', 'IDS-STAGE073-P4-GATE'), ('IDS-STAGE073', 'IDS-V0_1-STAGE073-P4', 'IDS-V0_1-STAGE073-P4', 'IDS-STAGE073-REVIEW-GATE'), ("IDS-STAGE073", "IDS-V0_1-STAGE073-REVIEW", "IDS-V0_1-STAGE073-REVIEW", "IDS-STAGE074-P1-GATE"),
                ("IDS-STAGE074", "IDS-V0_1-STAGE074-P1", "IDS-V0_1-STAGE074-P1", "IDS-STAGE074-P2-GATE"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-P2", "IDS-V0_1-STAGE074-P2", "IDS-STAGE074-P3-GATE"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-P3", "IDS-V0_1-STAGE074-P3", "IDS-STAGE074-P4-GATE"), ("IDS-STAGE074", "IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-P4", "IDS-STAGE074-REVIEW-GATE"),
                ("IDS-STAGE074", "IDS-V0_1-STAGE074-REVIEW", "IDS-V0_1-STAGE074-REVIEW", "IDS-STAGE075-P1-GATE"),
                ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P1', 'IDS-V0_1-STAGE075-P1', 'IDS-STAGE075-P2-GATE'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P2', 'IDS-V0_1-STAGE075-P2', 'IDS-STAGE075-P3-GATE'), ('IDS-STAGE075', 'IDS-V0_1-STAGE075-P3', 'IDS-V0_1-STAGE075-P3', 'IDS-STAGE075-P4-GATE'),
            ),
        )
        self.assertIn(plan["task"], ("IDS-V0_1-STAGE063-REVIEW", "IDS-V0_1-STAGE064-P1", "IDS-V0_1-STAGE064-P2", "IDS-V0_1-STAGE064-P3", "IDS-V0_1-STAGE064-P4", "IDS-V0_1-STAGE064-REVIEW", "IDS-V0_1-STAGE065-P1", "IDS-V0_1-STAGE065-P2", "IDS-V0_1-STAGE065-P3", "IDS-V0_1-STAGE065-P4", "IDS-V0_1-STAGE065-REVIEW", "IDS-V0_1-STAGE066-P1", "IDS-V0_1-STAGE066-P2", "IDS-V0_1-STAGE066-P3", "IDS-V0_1-STAGE066-P4", "IDS-V0_1-STAGE066-REVIEW", "IDS-V0_1-STAGE067-P1", "IDS-V0_1-STAGE067-P2", "IDS-V0_1-STAGE067-P3", "IDS-V0_1-STAGE067-P4", "IDS-V0_1-STAGE067-REVIEW", "IDS-V0_1-STAGE068-P1", "IDS-V0_1-STAGE068-P2", "IDS-V0_1-STAGE068-P3", "IDS-V0_1-STAGE068-P4", "IDS-V0_1-STAGE068-REVIEW",
     "IDS-V0_1-STAGE069-P1",
     "IDS-V0_1-STAGE069-P2",
     "IDS-V0_1-STAGE069-P3",
     "IDS-V0_1-STAGE069-P4",
     "IDS-V0_1-STAGE069-REVIEW",

     "IDS-V0_1-STAGE070-P1","IDS-V0_1-STAGE070-P2","IDS-V0_1-STAGE070-P3", "IDS-V0_1-STAGE070-P4", "IDS-V0_1-STAGE070-REVIEW", "IDS-V0_1-STAGE071-P1", "IDS-V0_1-STAGE071-P2", "IDS-V0_1-STAGE071-P3", "IDS-V0_1-STAGE071-P4", "IDS-V0_1-STAGE071-REVIEW", "IDS-V0_1-STAGE072-P1", "IDS-V0_1-STAGE072-P2", "IDS-V0_1-STAGE072-P3", "IDS-V0_1-STAGE072-P4", "IDS-V0_1-STAGE072-REVIEW", "IDS-V0_1-STAGE073-P1", "IDS-V0_1-STAGE073-P2", "IDS-V0_1-STAGE073-P3", "IDS-V0_1-STAGE073-P4", "IDS-V0_1-STAGE073-REVIEW", "IDS-V0_1-STAGE074-P1", "IDS-V0_1-STAGE074-P2", "IDS-V0_1-STAGE074-P3", "IDS-V0_1-STAGE074-P4", "IDS-V0_1-STAGE074-REVIEW",
            'IDS-V0_1-STAGE075-P1', 'IDS-V0_1-STAGE075-P2', 'IDS-V0_1-STAGE075-P3',
        ))
        self.assertTrue(
            (
("IDS-STAGE064-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE064-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE064-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE064-P4-GATE" in plan["stop_condition"]
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
            or "IDS-STAGE069-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE069-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE069-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE069-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE069-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE070-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE070-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE070-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE070-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE070-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE071-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE071-P2-GATE" in plan["stop_condition"]
            or "IDS-STAGE071-P3-GATE" in plan["stop_condition"]
            or "IDS-STAGE071-P4-GATE" in plan["stop_condition"]
            or "IDS-STAGE071-REVIEW-GATE" in plan["stop_condition"]
            or "IDS-STAGE072-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE072-P2-GATE" in plan["stop_condition"]
               or "IDS-STAGE072-P3-GATE" in plan["stop_condition"]
               or "IDS-STAGE072-P4-GATE" in plan["stop_condition"]
               or "IDS-STAGE072-REVIEW-GATE" in plan["stop_condition"]
               or "IDS-STAGE073-P1-GATE" in plan["stop_condition"]) or "IDS-STAGE073-P2-GATE" in plan["stop_condition"] or "IDS-STAGE073-P3-GATE" in plan["stop_condition"] or "IDS-STAGE073-P4-GATE" in plan["stop_condition"] or "IDS-STAGE073-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE074-P1-GATE" in plan["stop_condition"] or "IDS-STAGE074-P2-GATE" in plan["stop_condition"] or "IDS-STAGE074-P3-GATE" in plan["stop_condition"] or "IDS-STAGE074-P4-GATE" in plan["stop_condition"] or "IDS-STAGE074-REVIEW-GATE" in plan["stop_condition"] or "IDS-STAGE075-P1-GATE" in plan["stop_condition"]
            or "IDS-STAGE075-P2-GATE" in plan["stop_condition"] or "IDS-STAGE075-P3-GATE" in plan["stop_condition"], "IDS-STAGE075-P4-GATE" in plan["stop_condition"]
            )
        )
        self.assertTrue(
            {"ACC-STAGE063-REVIEW-01", "ACC-STAGE063-REVIEW-02"}.issubset(
                {item["id"] for item in acceptance["items"]}
            )
        )
        self.assertEqual("IDS-V0_1-STAGE063-REVIEW", run["task_id"])
        self.assertEqual("IDS-STAGE064-P1-GATE", run["next_gate"])
        self.assertTrue(run["result"].startswith("PASS_LOCAL_"))
        self.assertFalse(run["observed_work"]["ovh_deployment_performed"])
        self.assertIn("stage063_review", BATCH.read_text(encoding="utf-8"))
        self.assertIn("IDS-V0_1-STAGE063-REVIEW", ROADMAP.read_text(encoding="utf-8"))
        self.assertTrue(
            any(
                item.get("event_id") == "EVT-IDS-V0_1-STAGE063-REVIEW-20260814-001"
                for item in events
            )
        )


if __name__ == "__main__":
    unittest.main()
