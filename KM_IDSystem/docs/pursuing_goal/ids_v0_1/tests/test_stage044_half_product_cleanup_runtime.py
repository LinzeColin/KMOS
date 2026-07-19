import copy
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT = ROOT.parent
BASE = ROOT / "docs" / "pursuing_goal" / "ids_v0_1"
PHASE2_DOC = BASE / "STAGE044_PHASE2_HALF_PRODUCT_CLEANUP_SLICE.md"
CONTRACT = (
    BASE
    / "half_product_cleanup"
    / "stage044_half_product_cleanup_runtime_contract.json"
)
CHECKER = ROOT / "scripts" / "check_half_product_cleanup_runtime.py"
PARAMETER_REGISTRY = ROOT / "docs" / "governance" / "parameter_registry.csv"
MODEL_REGISTRY = ROOT / "docs" / "governance" / "model_registry.yaml"
FORMULA_REGISTRY = ROOT / "docs" / "governance" / "formula_registry.yaml"
MODEL_SPEC = ROOT / "docs" / "governance" / "MODEL_SPEC.md"

PARAMETERS = {
    "cleanup_scan_interval": 300,
    "cleanup_candidate_retention": 600,
    "cleanup_lock_lease": 30,
    "writer_quiescence_window": 60,
    "cleanup_attempt_timeout": 30,
}
PARAMETER_IDS = [
    "PARAM-082",
    "PARAM-083",
    "PARAM-084",
    "PARAM-085",
    "PARAM-086",
]
SOURCE_BINDING = {
    "source_archive_path": (
        "/Users/linzezhang/Downloads/"
        "IDS_Taskpack_v0_1_only_中文修订版.zip"
    ),
    "source_archive_sha256": (
        "55b782e338610aab6361b7945bb5e290ba60038a06cc765c7c2da801734db6d3"
    ),
    "source_member": (
        "IDS_v0_1_Final_Chinese_Revised/stages/"
        "STAGE-044_半成品输出清理.md"
    ),
    "source_member_match_count": 1,
    "source_member_sha256": (
        "e7e98eb5497aa33124b944dfc1d00e15588a672c0f9accc4cda4a66fe1f72a53"
    ),
    "roadmap_sha256": (
        "a193fd2c44c51d634bf7887a1a6baf7e5199d9a8535e4211e35e97588e2e21a6"
    ),
    "instructions_sha256": (
        "ce456e06136d5ecc56cd7c9dc926abb5894817dda87bf7667588bf85211794f8"
    ),
    "source_verification_status": "SOURCE_VERIFIED",
}
PREDECESSOR_BINDING = {
    "commit": "0eabde291fc54328e6fbc76df4f9dc5af894b770",
    "tree": "53a8e0388ba3a2f6551c43b6dc07ee22ff90505c",
    "parent": "e7835134550e2776f0949870fcaf7d7b9a54bd01",
    "task_id": "IDS-V0_1-STAGE044-P1",
    "result": "PASS_PHASE1_CONTRACT_DELETE_DISABLED",
}
UPSTREAM_BINDINGS = {
    "phase1_contract": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/half_product_cleanup/"
        "stage044_half_product_cleanup_contract.json",
        "b4dddb7fc2cb840e0ee427b2c137394cc47e1c6b15c7bee7dfe286a3b89adfe7",
    ),
    "phase1_checker": (
        "KM_IDSystem/scripts/check_half_product_cleanup.py",
        "a57c6f848a015844591bd92a94f92578f424b52a201c558132fc9544848b777c",
    ),
    "phase1_boundary": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
        "STAGE044_PHASE1_HALF_PRODUCT_CLEANUP_SCOPE_BOUNDARY.md",
        "a5befb807e2481754e65f602d2abf7a2f4b4cac77b2b67dcc4a2343d6aeca014",
    ),
    "stage034_retention_contract": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/data_retention_table/"
        "stage034_data_retention_table_index.json",
        "0b579f93c623cd20e99752c9801f5c9bb14757e531697d687f87fe5c7c6c8504",
    ),
    "stage037_state_index": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/job_state_model/"
        "stage037_job_state_model_index.json",
        "b70bf72ebe4212f45d380c13fbfe429791e1f4a5c73dccbba81211b7adc1c2d3",
    ),
    "stage040_backpressure_runtime": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/backpressure_policy/"
        "stage040_backpressure_runtime_contract.json",
        "2970ebd143030821d9a8b00e4fdb11342f8f82ef3bcf4d91717ba707b5054e2e",
    ),
    "stage041_lock_runtime": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/lock_registry/"
        "stage041_lock_registry_runtime_contract.json",
        "80f87c789c6fc834b13eaec3d14d9444417ee7313ff8f88f6893bbda15e1f464",
    ),
    "stage042_lifecycle_runtime": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/automatic_lifecycle/"
        "stage042_automatic_lifecycle_runtime_contract.json",
        "f24283a0ab934082b0ceb48c6ca1597ca17d1c6cca6a939e2653fb00ede83e49",
    ),
    "stage043_recovery_runtime": (
        "KM_IDSystem/docs/pursuing_goal/ids_v0_1/worker_crash_recovery/"
        "stage043_worker_crash_recovery_runtime_contract.json",
        "153a451f3e5aef4fef1faa8b4e3035f472ac50298d790731f19ba8701361ab38",
    ),
}


class Stage044HalfProductCleanupPhase2Tests(unittest.TestCase):
    def _contract(self):
        self.assertTrue(CONTRACT.is_file(), f"missing Phase 2 contract: {CONTRACT}")
        return json.loads(CONTRACT.read_text(encoding="utf-8"))

    def _checker(self):
        self.assertTrue(CHECKER.is_file(), f"missing Phase 2 checker: {CHECKER}")
        spec = importlib.util.spec_from_file_location(
            "stage044_half_product_cleanup_runtime_checker", CHECKER
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_phase2_artifacts_and_identity_are_exact(self):
        for path in (PHASE2_DOC, CONTRACT, CHECKER):
            with self.subTest(path=path):
                self.assertTrue(path.is_file(), f"missing Phase 2 artifact: {path}")
        contract = self._contract()
        self.assertEqual("ids.stage044.half_product_cleanup.phase2.v1", contract["schema_version"])
        self.assertEqual("IDS-V0_1-STAGE044-P2", contract["task_id"])
        self.assertEqual("ACC-STAGE-044", contract["acceptance_id"])
        self.assertEqual(
            "ISOLATED_NON_PRODUCTION_REFERENCE_ONLY_CLEANUP_CANDIDATE_DECISION_SLICE",
            contract["execution_mode"],
        )
        self.assertEqual(
            "ids.half_product_cleanup_policy.v0_1.stage044.p2",
            contract["policy_contract_id"],
        )
        self.assertEqual("IDS-STAGE044-P3-GATE", contract["next_gate"])

    def test_source_predecessor_and_upstream_bindings_are_exact(self):
        module = self._checker()
        contract = self._contract()
        self.assertEqual(SOURCE_BINDING, contract["source_binding"])
        self.assertEqual(PREDECESSOR_BINDING, contract["phase1_predecessor_binding"])
        observed = subprocess.check_output(
            ["git", "show", "-s", "--format=%H%n%T%n%P", PREDECESSOR_BINDING["commit"]],
            cwd=REPO_ROOT,
            text=True,
        ).splitlines()
        self.assertEqual(
            [PREDECESSOR_BINDING["commit"], PREDECESSOR_BINDING["tree"], PREDECESSOR_BINDING["parent"]],
            observed,
        )
        for key, (relative, digest) in UPSTREAM_BINDINGS.items():
            with self.subTest(binding=key):
                self.assertEqual(
                    {"ref": relative, "sha256": digest},
                    contract["upstream_bindings"][key],
                )
                self.assertEqual(
                    digest,
                    hashlib.sha256((REPO_ROOT / relative).read_bytes()).hexdigest(),
                )
        self.assertTrue(all(module.evaluate_contract(contract).values()))

    def test_all_five_parameters_are_sourced_registered_and_not_calibrated(self):
        contract = self._contract()
        policy = contract["policy"]
        self.assertEqual(PARAMETERS, policy["parameters"])
        self.assertEqual("PROPOSED", policy["fact_level"])
        self.assertFalse(policy["production_calibrated"])
        self.assertEqual("TASK-OPME-B-001", policy["production_calibration_task_id"])
        self.assertEqual(set(PARAMETERS), set(policy["parameter_provenance"]))
        for name, item in policy["parameter_provenance"].items():
            with self.subTest(parameter=name):
                self.assertEqual(PARAMETERS[name], item["value"])
                self.assertEqual("seconds", item["unit"])
                self.assertEqual("PROPOSED", item["fact_level"])
                self.assertEqual(policy["policy_version"], item["policy_version"])
                self.assertTrue(item["source_refs"])
                self.assertTrue(item["derivation"])
                self.assertTrue(item["validation_evidence"])
                self.assertEqual("NO_AUTOMATIC_HALF_PRODUCT_CLEANUP", item["rollback"])
        with PARAMETER_REGISTRY.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        selected = {
            row["parameter_id"]: row
            for row in rows
            if row["parameter_id"] in PARAMETER_IDS
        }
        self.assertEqual(set(PARAMETER_IDS), set(selected))
        for parameter_id, (symbol, value) in zip(PARAMETER_IDS, PARAMETERS.items()):
            with self.subTest(parameter_id=parameter_id):
                row = selected[parameter_id]
                self.assertEqual("MOD-013", row["model_id"])
                self.assertEqual("FORM-013", row["formula_id"])
                self.assertEqual(symbol, row["symbol"])
                self.assertEqual(str(value), row["active_value"])
                self.assertEqual("planned", row["status"])
                self.assertEqual("PROPOSED", row["fact_level"])
        model_text = MODEL_REGISTRY.read_text(encoding="utf-8")
        formula_text = FORMULA_REGISTRY.read_text(encoding="utf-8")
        spec_text = MODEL_SPEC.read_text(encoding="utf-8")
        self.assertIn('assumption_id: "ASM-009"', model_text)
        self.assertIn('model_id: "MOD-013"', model_text)
        self.assertIn('formula_id: "FORM-013"', formula_text)
        for marker in (
            "- model_count: 13",
            "- formula_count: 13",
            "- parameter_count: 86",
            "- active_model_count: 7",
            "- active_formula_count: 7",
            "- active_parameter_count: 49",
        ):
            self.assertIn(marker, spec_text)

    def test_control_request_is_canonical_reference_only_and_never_traversed(self):
        module = self._checker()
        request = module.build_cleanup_request()
        self.assertTrue(module.validate_cleanup_request(request))
        self.assertEqual(
            request["cleanup_request_id"],
            module.derive_cleanup_request_id(request),
        )
        self.assertTrue(request["job_id"].startswith("control:stage044:"))
        self.assertFalse(any(str(value).startswith("/") for value in request.values()))
        dumped = json.dumps(request, ensure_ascii=False)
        self.assertNotIn("raw_payload", dumped)
        for ref in request["evidence"]["input_refs"]:
            tracked = subprocess.run(
                ["git", "ls-files", "--error-unmatch", ref],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, tracked.returncode, ref)

    def test_valid_candidate_requires_review_and_never_authorizes_delete(self):
        module = self._checker()
        request = module.build_cleanup_request()
        result = module.evaluate_cleanup_candidate(request)
        self.assertEqual("CLEANUP_CANDIDATE_REVIEW_REQUIRED", result["decision_action"])
        self.assertEqual("STAGE-044", result["runtime_owner"])
        self.assertTrue(result["candidate_only"])
        self.assertFalse(result["delete_allowed"])
        self.assertFalse(result["filesystem_traversal_performed"])
        self.assertFalse(result["production_lock_acquired"])
        self.assertEqual([], result["output_refs"])
        self.assertTrue(result["candidate_ref"].startswith("candidate:sha256:"))
        self.assertTrue(result["audit_ref"].startswith("audit:stage044:sha256:"))

    def test_only_two_classes_and_failed_terminal_states_can_be_candidates(self):
        module = self._checker()
        for artifact_class in ("TEMP_STAGING_OUTPUT", "INCOMPLETE_DERIVATIVE_OUTPUT"):
            for state in ("FAILED", "DEAD_LETTERED", "CANCELLED"):
                with self.subTest(artifact_class=artifact_class, state=state):
                    request = module.build_cleanup_request(
                        artifact_class=artifact_class,
                        observed_job_state=state,
                    )
                    self.assertEqual(
                        "CLEANUP_CANDIDATE_REVIEW_REQUIRED",
                        module.evaluate_cleanup_candidate(request)["decision_action"],
                    )
        for state in (
            "CREATED", "QUEUED", "CLAIMED", "RUNNING", "PAUSE_REQUESTED",
            "PAUSED", "RETRY_WAIT", "SUCCEEDED",
        ):
            with self.subTest(state=state):
                request = module.build_cleanup_request(observed_job_state=state)
                self.assertEqual(
                    "CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN",
                    module.evaluate_cleanup_candidate(request)["decision_action"],
                )

    def test_protected_classes_holds_and_durable_refs_fail_closed(self):
        module = self._checker()
        protected = self._contract()["decision_contract"]["protected_artifact_classes"]
        for artifact_class in protected:
            with self.subTest(artifact_class=artifact_class):
                request = module.build_cleanup_request(artifact_class=artifact_class)
                result = module.evaluate_cleanup_candidate(request)
                self.assertEqual("CLEANUP_BLOCKED_PROTECTED", result["decision_action"])
                self.assertFalse(result["delete_allowed"])
        for overrides in (
            {"legal_hold_status": "HELD"},
            {"owner_hold_status": "HELD"},
            {"durable_reference_status": "REFERENCED"},
            {"rebuildable": False},
        ):
            with self.subTest(overrides=overrides):
                request = module.build_cleanup_request(**overrides)
                self.assertEqual(
                    "CLEANUP_BLOCKED_PROTECTED",
                    module.evaluate_cleanup_candidate(request)["decision_action"],
                )

    def test_resource_pressure_is_mandatory_and_never_auto_resumes(self):
        module = self._checker()
        for signal in (
            "EXTERNAL_DRIVE_OFFLINE",
            "DISK_SPACE_INSUFFICIENT",
            "EXTERNAL_API_BUDGET_INSUFFICIENT",
        ):
            with self.subTest(signal=signal):
                request = module.build_cleanup_request(
                    resource_gates_passed=False,
                    resource_pressure_signal=signal,
                )
                result = module.evaluate_cleanup_candidate(request)
                self.assertEqual("CLEANUP_BLOCKED_RESOURCE", result["decision_action"])
                self.assertFalse(result["automatic_resume_allowed"])
                self.assertFalse(result["delete_allowed"])

    def test_identity_root_and_path_evidence_fail_closed(self):
        module = self._checker()
        requests = [
            module.build_cleanup_request(root_relative_path="../escape.partial"),
            module.build_cleanup_request(root_relative_path="/absolute.partial"),
            module.build_cleanup_request(
                root_relative_path="control/stage044/./attempt-output.partial"
            ),
            module.build_cleanup_request(
                root_relative_path="control//stage044/attempt-output.partial"
            ),
            module.build_cleanup_request(root_relative_path="control/link.partial", no_symlink_components_proved=False),
            module.build_cleanup_request(attempt_ownership_proved=False),
            module.build_cleanup_request(approved_root_identity_proved=False),
            module.build_cleanup_request(lstat_identity_stable=False),
            module.build_cleanup_request(st_ino=True),
            module.build_cleanup_request(input_refs=["KM_IDSystem/README.md"]),
            module.build_cleanup_request(
                creator_job_id="control:stage044:job:another"
            ),
            module.build_cleanup_request(
                approved_root_canonical_identity="root:sha256:" + "f" * 64
            ),
            module.build_cleanup_request(
                cleanup_manifest_ref="manifest:sha256:" + "0" * 64
            ),
            module.build_cleanup_request(
                writer_quiescence_evidence_ref="evidence:stage044:writer-forged"
            ),
            module.build_cleanup_request(
                resource_gate_evidence_ref="evidence:stage044:resource-forged"
            ),
        ]
        for request in requests:
            with self.subTest(request=request):
                result = module.evaluate_cleanup_candidate(request)
                self.assertEqual("CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN", result["decision_action"])
                self.assertFalse(result["delete_allowed"])

    def test_retention_lock_and_quiescence_windows_are_all_required(self):
        module = self._checker()
        blocked_requests = [
            module.build_cleanup_request(retention_elapsed_seconds=599),
            module.build_cleanup_request(writer_quiescence_elapsed_seconds=59),
            module.build_cleanup_request(writer_quiescence_proved=False),
            module.build_cleanup_request(exclusive_namespace_lock_proved=False),
            module.build_cleanup_request(namespace_lock_managed=False),
            module.build_cleanup_request(producer_and_cleanup_leases_absent_or_fenced=False),
        ]
        for request in blocked_requests:
            with self.subTest(request=request):
                result = module.evaluate_cleanup_candidate(request)
                self.assertEqual("CLEANUP_BLOCKED_ACTIVE_OR_UNKNOWN", result["decision_action"])
                self.assertFalse(result["delete_allowed"])

    def test_exact_replay_is_idempotent_and_same_id_changed_payload_conflicts(self):
        module = self._checker()
        ledger = module.InMemoryCleanupDecisionLedger()
        request = module.build_cleanup_request()
        first = module.evaluate_cleanup_candidate(request, ledger=ledger)
        replay = module.evaluate_cleanup_candidate(copy.deepcopy(request), ledger=ledger)
        self.assertEqual(first, replay)
        changed = copy.deepcopy(request)
        changed["owner_hold_status"] = "HELD"
        conflict = module.evaluate_cleanup_candidate(changed, ledger=ledger)
        self.assertEqual("REQUIRE_MANUAL_REVIEW", conflict["decision_action"])
        self.assertEqual("CLEANUP_REQUEST_CONFLICT", conflict["reason_code"])
        self.assertFalse(conflict["delete_allowed"])

    def test_results_are_safe_reference_only_and_malformed_input_is_not_echoed(self):
        module = self._checker()
        request = module.build_cleanup_request()
        result = module.evaluate_cleanup_candidate(request)
        self.assertEqual(request["evidence"]["input_refs"], result["input_refs"])
        self.assertTrue(result["human_status"]["label_zh"])
        malformed = module.evaluate_cleanup_candidate({"raw_payload": "secret-value"})
        self.assertEqual("REQUIRE_MANUAL_REVIEW", malformed["decision_action"])
        dumped = json.dumps(malformed, ensure_ascii=False)
        self.assertNotIn("secret-value", dumped)
        self.assertNotIn("raw_payload", dumped)

    def test_contract_and_request_tampering_fail_closed(self):
        module = self._checker()
        contract = self._contract()
        mutations = []
        wrong_parameter = copy.deepcopy(contract)
        wrong_parameter["policy"]["parameters"]["cleanup_candidate_retention"] = 1
        mutations.append(wrong_parameter)
        runtime_enabled = copy.deepcopy(contract)
        runtime_enabled["runtime_boundary"]["delete_allowed"] = True
        mutations.append(runtime_enabled)
        wrong_hash = copy.deepcopy(contract)
        wrong_hash["upstream_bindings"]["phase1_contract"]["sha256"] = "0" * 64
        mutations.append(wrong_hash)
        extra_root = copy.deepcopy(contract)
        extra_root["unexpected"] = True
        mutations.append(extra_root)
        path_policy_changed = copy.deepcopy(contract)
        path_policy_changed["path_and_identity_contract"]["file_type_allowlist"] = [
            "DIRECTORY"
        ]
        mutations.append(path_policy_changed)
        human_status_overclaim = copy.deepcopy(contract)
        human_status_overclaim["human_status_projection"][
            "CLEANUP_CANDIDATE_REVIEW_REQUIRED"
        ]["label_zh"] = "文件已自动删除"
        mutations.append(human_status_overclaim)
        for candidate in mutations:
            with self.subTest(candidate=candidate):
                self.assertFalse(all(module.evaluate_contract(candidate).values()))
                self.assertFalse(module._contract_fast_valid(candidate))
                result = module.evaluate_cleanup_candidate(
                    module.build_cleanup_request(), contract=candidate
                )
                self.assertEqual("REQUIRE_MANUAL_REVIEW", result["decision_action"])
        forged = module.build_cleanup_request()
        forged["cleanup_request_id"] = "control:stage044:cleanup:" + "0" * 64
        result = module.evaluate_cleanup_candidate(forged)
        self.assertEqual("REQUIRE_MANUAL_REVIEW", result["decision_action"])
        self.assertEqual("CLEANUP_REQUEST_ID_MISMATCH", result["reason_code"])

    def test_checker_report_proves_decisions_but_no_cleanup_execution(self):
        module = self._checker()
        report = module.build_stage044_phase2_report()
        self.assertTrue(all(report["contract_checks"].values()), report)
        self.assertTrue(all(report["decision_checks"].values()), report)
        self.assertTrue(report["parameter_values_assigned"])
        self.assertEqual("PROPOSED", report["parameter_fact_level"])
        self.assertTrue(report["isolated_candidate_decision_runtime_performed"])
        self.assertTrue(report["cleanup_candidate_evaluation_performed"])
        self.assertFalse(report["cleanup_scan_performed"])
        self.assertFalse(report["filesystem_traversal_performed"])
        self.assertFalse(report["production_lock_runtime_performed"])
        self.assertFalse(report["delete_operation_started"])
        self.assertFalse(report["cleanup_runtime_performed"])
        self.assertFalse(report["raw_metadata_content_accessed"])
        self.assertFalse(report["github_upload_allowed"])
        self.assertEqual("IDS-STAGE044-P3-GATE", report["next_gate"])
        self.assertEqual(
            "PASS_ISOLATED_CLEANUP_CANDIDATE_DECISION_DELETE_DISABLED",
            report["result"],
        )

    def test_governance_event_and_phase2_transition_are_exact(self):
        batch = (BASE / "BATCH041_050_UPLOAD_LOCK.yaml").read_text(encoding="utf-8")
        roadmap = (ROOT / "docs" / "governance" / "roadmap.yaml").read_text(encoding="utf-8")
        events = (ROOT / "docs" / "governance" / "events.jsonl").read_text(encoding="utf-8")
        handoff = (ROOT / "docs" / "HANDOFF.md").read_text(encoding="utf-8")
        for marker in (
            'status: "stage044_phase2_completed"',
            'current_task_id: "IDS-V0_1-STAGE044-P2"',
            'next_allowed_task_id: "IDS-V0_1-STAGE044-P3"',
            'next_gate: "IDS-STAGE044-P3-GATE"',
            'github_upload_allowed: false',
        ):
            self.assertIn(marker, batch)
        current_routes = (
            (
                'current_phase_id: "IDS-STAGE044-P2"',
                'current_task_id: "IDS-V0_1-STAGE044-P2"',
                'next_gate_id: "IDS-STAGE044-P3-GATE"',
            ),
            (
                'current_phase_id: "IDS-STAGE044-P3"',
                'current_task_id: "IDS-V0_1-STAGE044-P3"',
                'next_gate_id: "IDS-STAGE044-P4-GATE"',
            ),
            (
                'current_phase_id: "IDS-STAGE044-P4"',
                'current_task_id: "IDS-V0_1-STAGE044-P4"',
                'next_gate_id: "IDS-STAGE044-REVIEW-GATE"',
            ),
        )
        self.assertIn('current_stage_id: "IDS-STAGE044"', roadmap)
        self.assertTrue(
            any(all(marker in roadmap for marker in route) for route in current_routes),
            roadmap[:500],
        )
        self.assertIn("EVT-IDS-V0_1-STAGE044-P2-20260719-001", events)
        self.assertTrue(
            "Completed task in this run: `IDS-V0_1-STAGE044-P2`" in handoff
            or "`IDS-V0_1-STAGE044-P2` is preserved as completed" in handoff
            or "Completed task in this run: `IDS-V0_1-STAGE044-P4`" in handoff
        )
        self.assertTrue(
            "Next allowed task: `IDS-V0_1-STAGE044-P3`" in handoff
            or "Next allowed task: `IDS-V0_1-STAGE044-P4`" in handoff
            or "Next allowed task: `IDS-V0_1-STAGE044-REVIEW`" in handoff
        )
        self.assertIn("delete_operation_started=false", events)

    def test_cli_emits_the_exact_machine_report(self):
        module = self._checker()
        expected = module.build_stage044_phase2_report()
        completed = subprocess.run(
            ["python3", "-B", str(CHECKER)],
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
