import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = PROJECT_ROOT.parent
BASE = PROJECT_ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
RUNTIME_CHECKER = PROJECT_ROOT / "scripts" / "check_parser_output_runtime.py"
REVIEW_CHECKER = PROJECT_ROOT / "scripts" / "check_parser_output_stage_review.py"
REVIEW_ARTIFACT = BASE / "STAGE047_STAGE_REVIEW.md"
BATCH = BASE / "BATCH041_050_UPLOAD_LOCK.yaml"
ROADMAP = PROJECT_ROOT / "docs" / "governance" / "roadmap.yaml"
EVENTS = PROJECT_ROOT / "docs" / "governance" / "events.jsonl"
HANDOFF = PROJECT_ROOT / "docs" / "HANDOFF.md"

PHASE4_COMMIT = "007ef85e6ee30e155269284dc9c0fe89572c8161"
PHASE4_ROOT_TREE = "779309d42552653af35f4a06701fecc7a6fe62d5"
PHASE4_KMIDS_TREE = "5c31c7341c8d3b546066b5565c273885fbd8fe11"
PHASE4_PARENT = "595a507519b443faa49fca9fa0a6e8bd21cb9dde"
REVIEW_EVENT_ID = "EVT-IDS-V0_1-STAGE047-REVIEW-20260724-001"


def _load(path: Path, name: str):
    if not path.is_file():
        raise AssertionError(f"missing checker: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load checker: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Stage047ParserOutputStageReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = _load(RUNTIME_CHECKER, "stage047_final_review_runtime_tests")
        cls.review = _load(REVIEW_CHECKER, "stage047_final_review_checker_tests")

    def test_review_artifacts_and_identity_exist(self):
        self.assertTrue(REVIEW_ARTIFACT.is_file())
        report = self.review.build_stage047_review_report()
        self.assertEqual(
            "ids.stage047.parser_output.stage_review.v1",
            report["schema_version"],
        )
        self.assertEqual("IDS-V0_1-STAGE047-REVIEW", report["task_id"])
        self.assertEqual("ACC-STAGE-047", report["acceptance_id"])
        self.assertEqual(
            "PASS_REVIEWED_LOCAL_PARSER_OUTPUT_RUNTIME_DISABLED",
            report["result"],
        )

    def test_review_reverifies_sources_phase4_commit_artifacts_and_phases(self):
        report = self.review.build_stage047_review_report()
        self.assertTrue(report["source_integrity_valid"], report)
        self.assertTrue(all(report["source_integrity_checks"].values()), report)
        self.assertEqual(
            {
                "commit": PHASE4_COMMIT,
                "root_tree": PHASE4_ROOT_TREE,
                "km_ids_tree": PHASE4_KMIDS_TREE,
                "parent": PHASE4_PARENT,
                "required_ancestor_of_head": True,
            },
            report["phase4_commit_binding"],
        )
        self.assertTrue(report["phase4_commit_binding_valid"], report)
        self.assertTrue(report["phase4_artifact_bindings_valid"], report)
        self.assertEqual(
            {
                "phase1_contract_valid": True,
                "phase2_slice_valid": True,
                "phase3_scenarios_valid": True,
                "phase4_delivery_valid": True,
            },
            report["phase_results"],
        )

    def test_review_findings_are_machine_checked_and_fail_closed(self):
        report = self.review.build_stage047_review_report()
        self.assertEqual(6, report["finding_count"])
        self.assertEqual(
            {"Critical": 2, "Important": 4},
            report["finding_counts"],
        )
        self.assertTrue(all(report["finding_checks"].values()), report)
        tampered = copy.deepcopy(report["finding_checks"])
        tampered["invalid_unicode_structured_rejection"] = False
        blocked = self.review.build_stage047_review_report(
            finding_checks=tampered
        )
        self.assertFalse(blocked["review_valid"], blocked)
        self.assertEqual("FAIL_CLOSED", blocked["result"])
        self.assertEqual("IDS-STAGE047-REVIEW-GATE", blocked["next_gate"])
        self.assertFalse(blocked["stage048_entry_allowed"])
        self.assertFalse(blocked["github_upload_allowed"])

    def test_unicode_reference_graph_error_and_time_repairs_hold(self):
        report = self.review.build_stage047_review_report()
        expected = {
            "complete_request_result_source_lineage",
            "invalid_unicode_structured_rejection",
            "canonical_lower_ascii_control_references",
            "reciprocal_internal_reference_graph",
            "bounded_status_and_safe_errors",
            "monotonic_request_production_time",
        }
        self.assertEqual(expected, set(report["finding_checks"]))
        self.assertTrue(all(report["finding_checks"].values()), report)

    def test_governance_closes_stage_only_to_stage048_separate_run(self):
        batch = BATCH.read_text(encoding="utf-8")
        roadmap = ROADMAP.read_text(encoding="utf-8")
        events = EVENTS.read_text(encoding="utf-8")
        handoff = HANDOFF.read_text(encoding="utf-8")
        for marker in (
            'status: "stage047_completed_reviewed_local"',
            'review_status: "passed"',
            'current_task_id: "IDS-V0_1-STAGE047-REVIEW"',
            'next_allowed_task_id: "IDS-V0_1-STAGE048-P1"',
            'push_allowed: false',
            'stage048_entry_allowed: false',
        ):
            self.assertIn(marker, batch)
        for marker in (
            'current_phase_id: "IDS-STAGE047-REVIEW"',
            'current_task_id: "IDS-V0_1-STAGE047-REVIEW"',
            'next_gate_id: "IDS-STAGE048-P1-GATE"',
            'status: "completed_reviewed_local"',
        ):
            self.assertIn(marker, roadmap)
        self.assertIn(REVIEW_EVENT_ID, events)
        top = "\n".join(handoff.splitlines()[:60])
        self.assertIn(
            "Completed task in this run: `IDS-V0_1-STAGE047-REVIEW`",
            top,
        )
        self.assertIn(
            "Next allowed task: `IDS-V0_1-STAGE048-P1`",
            top,
        )

    def test_review_preserves_runtime_and_external_effect_prohibitions(self):
        report = self.review.build_stage047_review_report()
        for field in (
            "ids_business_source_read_performed",
            "source_file_open_performed",
            "parser_dispatch_performed",
            "parser_execution_performed",
            "fallback_execution_performed",
            "quality_gate_evaluation_performed",
            "persistent_state_write_performed",
            "audit_write_performed",
            "database_connection_performed",
            "raw_metadata_content_accessed",
            "production_runtime_activation_performed",
            "stage048_started",
            "stage048_entry_allowed",
            "batch_review_performed",
            "github_upload_allowed",
            "push_allowed",
            "app_reinstall_allowed",
        ):
            with self.subTest(field=field):
                self.assertFalse(report[field])
        review_text = REVIEW_ARTIFACT.read_text(encoding="utf-8")
        for marker in (
            "NO_STAGE048_THIS_RUN",
            "NO_GITHUB_UPLOAD",
            "NO_APP_REINSTALL",
            "NO_RAW_METADATA_ACCESS",
            "NO_PARSER_OR_FALLBACK_RUNTIME",
        ):
            self.assertIn(marker, review_text)

    def test_review_sources_are_git_tracked_and_match_the_index(self):
        report = self.review.build_stage047_review_report()
        self.assertTrue(
            report["source_binding_checks"]["all_review_sources_git_tracked"],
            report,
        )
        self.assertTrue(
            report["source_binding_checks"][
                "all_review_sources_match_git_index"
            ],
            report,
        )

    def test_cli_emits_exact_review_report(self):
        expected = self.review.build_stage047_review_report()
        completed = subprocess.run(
            ["python3", "-B", str(REVIEW_CHECKER)],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(expected, json.loads(completed.stdout))
        self.assertEqual("", completed.stderr)


if __name__ == "__main__":
    unittest.main()
