#!/usr/bin/env python3
"""Fail-closed STAGE-047 Phase 4 parser-output delivery checker.

The checker replays the committed Phase 3 synthetic, preparsed scenarios and
derives sanitized output samples, non-runtime fallback-log samples, quality
metrics, failure classifications, support boundaries and rollback evidence.
It never opens an IDS business source file and never runs a parser, fallback,
quality gate, evidence promotion or persistence path.
"""

from __future__ import annotations

from collections import Counter
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping, Optional
import unicodedata
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
BASE = PROJECT_ROOT / "docs/pursuing_goal/ids_v0_1"
CONTRACT_PATH = BASE / "parser_output/stage047_parser_output_delivery_contract.json"
PHASE3_CHECKER_PATH = PROJECT_ROOT / "scripts/check_parser_output_scenarios.py"

SCHEMA_VERSION = "ids.stage047.parser_output.phase4.delivery.v1"
REPORT_SCHEMA_VERSION = "ids.stage047.parser_output.phase4.report.v1"
TASK_ID = "IDS-V0_1-STAGE047-P4"
ACCEPTANCE_ID = "ACC-STAGE-047"
P4_GATE = "IDS-STAGE047-P4-GATE"
REVIEW_GATE = "IDS-STAGE047-REVIEW-GATE"
VALID_RESULT = "PASS_ISOLATED_PARSER_OUTPUT_CLOSEOUT_RUNTIME_DISABLED"
PHASE3_VALID_RESULT = "PASS_ISOLATED_PARSER_OUTPUT_SCENARIOS_RUNTIME_DISABLED"
CANONICAL_CONTRACT_SHA256 = (
    "33a815bafc49c681f0e5116106a94c5b915454eedc55c02c6641d740c9a137ab"
)

EXPECTED_ROOT_KEYS = {
    "schema_version",
    "stage",
    "phase",
    "task_id",
    "acceptance_id",
    "local_code",
    "execution_mode",
    "valid_result",
    "contract_state",
    "stage_review_status",
    "next_gate",
    "source_binding",
    "phase3_commit_binding",
    "phase3_artifact_bindings",
    "output_samples_contract",
    "fallback_log_contract",
    "quality_metrics_contract",
    "failure_classification_contract",
    "support_boundary",
    "version_evidence_contract",
    "configuration_rollback",
    "review_gate",
    "known_limits",
    "owner_feedback_contract",
    "truth_flags",
}

EXPECTED_SOURCE = {
    "source_archive_path": (
        "/Users/linzezhang/Downloads/IDS_Taskpack_v0_1_only_中文修订版.zip"
    ),
    "source_archive_sha256": (
        "55b782e338610aab6361b7945bb5e290ba60038a06cc765c7c2da801734db6d3"
    ),
    "source_member": (
        "IDS_v0_1_Final_Chinese_Revised/stages/"
        "STAGE-047_解析器输出合同.md"
    ),
    "source_member_match_count": 1,
    "source_member_sha256": (
        "e1d5bdb219b6f16ca7fec4e4455e7acba1ecbae9803a7c13721b75895671d2f4"
    ),
    "roadmap_path": (
        "/Users/linzezhang/Downloads/"
        "IDS_Codex开发Roadmap_v0_1_only_中文修订版.txt"
    ),
    "roadmap_sha256": (
        "a193fd2c44c51d634bf7887a1a6baf7e5199d9a8535e4211e35e97588e2e21a6"
    ),
    "instructions_path": (
        "/Users/linzezhang/Downloads/"
        "IDS_Codex使用说明_v0_1_only_中文修订版.txt"
    ),
    "instructions_sha256": (
        "ce456e06136d5ecc56cd7c9dc926abb5894817dda87bf7667588bf85211794f8"
    ),
    "source_verification_status": "SOURCE_VERIFIED",
}

EXPECTED_PHASE3_COMMIT = {
    "commit": "595a507519b443faa49fca9fa0a6e8bd21cb9dde",
    "root_tree": "65a4db060a67ffbb4e7007b25d0dd453fbdbfc88",
    "kmids_tree": "d0e7058864e6669abcf213cf8c9defe4d57c6fa5",
    "parent": "65b81389e24d9ae371f464dcd6321784b9078d8b",
    "required_ancestor_of_head": True,
}

EXPECTED_PHASE3_ARTIFACTS = {
    "stage047_phase3_evidence": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "STAGE047_PHASE3_PARSER_OUTPUT_SCENARIOS.md"
        ),
        "sha256": (
            "e0512ba27a5745588c037cfc400b17252000f097127be7c21c47a81e331b2d48"
        ),
    },
    "stage047_phase3_contract": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/parser_output/"
            "stage047_parser_output_scenarios_contract.json"
        ),
        "sha256": (
            "f51edfe2fc5c35b609bf3679252f855d052e9a20e468b43ab03c59ce3302e23a"
        ),
    },
    "stage047_phase3_checker": {
        "ref": "KM_IDSystem/scripts/check_parser_output_scenarios.py",
        "sha256": (
            "5c3a63b21003940e7cf5041dcf34f22dd1736389116f05d0034cd943dc6ba2ba"
        ),
    },
    "stage047_phase3_tests": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
            "test_stage047_parser_output_scenarios.py"
        ),
        "sha256": (
            "4a3c17674562feeaff0d56c6bbd133d9e2f0b916330655ea3c7bbd6370d5b06c"
        ),
    },
    "stage047_phase3_run": {
        "ref": "KM_IDSystem/machine/runs/2026-07-23-stage047-p3-local.json",
        "sha256": (
            "ac8e543a8613051dc54abac78dba4abcdda83458a68dcee9286fb432ca6a14a4"
        ),
    },
}

SUPPORTED_TYPES = ["PDF", "DOCX", "XLSX", "CSV", "TXT", "PNG", "JPEG", "TIFF"]
OUTPUT_FIELDS = ["text", "tables", "pages", "sections", "confidence", "errors"]
SAMPLE_SCENARIOS = [
    "pdf_preparsed_pages_candidate",
    "docx_preparsed_sections_candidate",
    "xlsx_preparsed_table_candidate_formula_preserved",
    "csv_preparsed_table_candidate",
    "txt_preparsed_text_candidate",
    "png_preparsed_image_partial_review",
    "jpeg_preparsed_image_partial_review",
    "tiff_preparsed_image_partial_review",
]
ALL_SCENARIOS = SAMPLE_SCENARIOS + [
    "unknown_route_requires_owner_review_no_output",
    "corrupt_route_blocks_explicit_no_output",
    "low_quality_txt_output_requires_review",
    "explicit_parser_failure_output_blocked",
    "instruction_like_text_cannot_override_policy",
    "invalid_lineage_rejected_sanitized",
    "malformed_nested_references_rejected",
    "empty_without_error_rejected",
]
FAILURE_SCENARIOS = {
    "png_preparsed_image_partial_review",
    "jpeg_preparsed_image_partial_review",
    "tiff_preparsed_image_partial_review",
    "unknown_route_requires_owner_review_no_output",
    "corrupt_route_blocks_explicit_no_output",
    "low_quality_txt_output_requires_review",
    "explicit_parser_failure_output_blocked",
    "invalid_lineage_rejected_sanitized",
    "malformed_nested_references_rejected",
    "empty_without_error_rejected",
}

TRUE_TRUTH_FLAGS = {
    "taskpack_source_read_performed",
    "taskpack_and_git_artifact_hashes_recomputed",
    "phase3_snapshot_reverified",
    "phase3_checker_replayed",
    "sanitized_output_samples_composed",
    "fallback_log_samples_derived",
    "quality_metrics_derived",
    "failure_classification_composed",
    "support_boundary_documented",
    "version_evidence_documented",
    "configuration_rollback_documented",
    "phase4_started",
}
FALSE_TRUTH_FLAGS = {
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "source_file_open_performed",
    "ids_business_filesystem_scan_performed",
    "ids_business_file_hash_performed",
    "file_type_redetection_performed",
    "actual_business_route_evaluation_performed",
    "runtime_parser_selected",
    "parser_dispatch_performed",
    "parser_execution_performed",
    "ids_business_parser_output_produced",
    "fallback_execution_performed",
    "fallback_attempt_performed",
    "runtime_fallback_log_produced",
    "differential_parser_evaluation_performed",
    "prompt_injection_scan_performed",
    "formula_execution_performed",
    "quality_gate_evaluation_performed",
    "evidence_promotion_performed",
    "manifest_write_performed",
    "evidence_ledger_write_performed",
    "audit_write_performed",
    "index_write_performed",
    "report_write_performed",
    "job_creation_performed",
    "state_transition_performed",
    "persistent_state_write_performed",
    "database_connection_performed",
    "schema_change_performed",
    "runtime_output_written",
    "production_runtime_activation_performed",
    "whole_stage_review_performed",
    "stage048_entry_allowed",
    "batch_review_performed",
    "github_upload_allowed",
    "push_allowed",
    "app_reinstall_allowed",
}


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _source_binding_live() -> bool:
    try:
        archive_path = Path(EXPECTED_SOURCE["source_archive_path"])
        roadmap_path = Path(EXPECTED_SOURCE["roadmap_path"])
        instructions_path = Path(EXPECTED_SOURCE["instructions_path"])
        if (
            not archive_path.is_file()
            or _sha256(archive_path) != EXPECTED_SOURCE["source_archive_sha256"]
            or _sha256(roadmap_path) != EXPECTED_SOURCE["roadmap_sha256"]
            or _sha256(instructions_path) != EXPECTED_SOURCE["instructions_sha256"]
        ):
            return False
        expected_member = unicodedata.normalize("NFC", EXPECTED_SOURCE["source_member"])
        with zipfile.ZipFile(archive_path) as archive:
            matches = [
                name
                for name in archive.namelist()
                if unicodedata.normalize("NFC", name) == expected_member
            ]
            if len(matches) != EXPECTED_SOURCE["source_member_match_count"]:
                return False
            member_sha = _sha256_bytes(archive.read(matches[0]))
        return member_sha == EXPECTED_SOURCE["source_member_sha256"]
    except (OSError, KeyError, TypeError, ValueError, zipfile.BadZipFile):
        return False


def _git_bytes(*args: str) -> Optional[bytes]:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=REPO_ROOT,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return None


def _git_text(*args: str) -> Optional[str]:
    payload = _git_bytes(*args)
    if payload is None:
        return None
    try:
        return payload.decode("utf-8").strip()
    except UnicodeDecodeError:
        return None


def _phase3_commit_bound(value: Any) -> bool:
    if value != EXPECTED_PHASE3_COMMIT:
        return False
    commit = EXPECTED_PHASE3_COMMIT["commit"]
    observed = _git_text("show", "-s", "--format=%H%n%T%n%P", commit)
    kmids_tree = _git_text("rev-parse", f"{commit}:KM_IDSystem")
    try:
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=REPO_ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    except OSError:
        ancestor = False
    return (
        observed
        == "\n".join(
            (
                commit,
                EXPECTED_PHASE3_COMMIT["root_tree"],
                EXPECTED_PHASE3_COMMIT["parent"],
            )
        )
        and kmids_tree == EXPECTED_PHASE3_COMMIT["kmids_tree"]
        and ancestor
    )


def _safe_repo_ref(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    path = Path(value)
    return (
        not path.is_absolute()
        and ".." not in path.parts
        and value.startswith("KM_IDSystem/")
        and "\x00" not in value
    )


def _phase3_artifacts_live(value: Any) -> bool:
    if value != EXPECTED_PHASE3_ARTIFACTS or not isinstance(value, Mapping):
        return False
    commit = EXPECTED_PHASE3_COMMIT["commit"]
    for binding in value.values():
        ref = binding.get("ref")
        expected = binding.get("sha256")
        if not _safe_repo_ref(ref) or not isinstance(expected, str):
            return False
        committed = _git_bytes("show", f"{commit}:{ref}")
        indexed = _git_bytes("show", f":{ref}")
        working_path = REPO_ROOT / ref
        try:
            working = working_path.read_bytes()
        except OSError:
            return False
        if any(
            payload is None or _sha256_bytes(payload) != expected
            for payload in (committed, indexed, working)
        ):
            return False
    return True


def _section_boundaries_valid(contract: Mapping[str, Any]) -> bool:
    samples = contract.get("output_samples_contract", {})
    fallback = contract.get("fallback_log_contract", {})
    metrics = contract.get("quality_metrics_contract", {})
    failures = contract.get("failure_classification_contract", {})
    support = contract.get("support_boundary", {})
    versions = contract.get("version_evidence_contract", {})
    rollback = contract.get("configuration_rollback", {})
    review = contract.get("review_gate", {})
    truth = contract.get("truth_flags", {})
    failure_scenarios = (
        [
            scenario
            for spec in failures.values()
            for scenario in spec.get("scenario_ids", [])
        ]
        if isinstance(failures, Mapping)
        else []
    )
    return (
        samples.get("sample_status")
        == "RECOMPUTED_SANITIZED_CONTROL_OUTPUT_NOT_RUNTIME"
        and samples.get("sample_scenario_ids") == SAMPLE_SCENARIOS
        and samples.get("required_sample_count") == len(SAMPLE_SCENARIOS)
        and samples.get("required_output_fields") == OUTPUT_FIELDS
        and samples.get("raw_content_retention_allowed") is False
        and samples.get("formula_value_retention_allowed") is False
        and samples.get("control_output_is_ids_business_output") is False
        and all(
            samples.get(name) is False
            for name in (
                "parser_dispatch_allowed",
                "parser_execution_allowed",
                "quality_gate_evaluation_allowed",
                "evidence_promotion_allowed",
                "persistent_write_allowed",
            )
        )
        and fallback.get("required_log_sample_count") == len(ALL_SCENARIOS)
        and [item.get("scenario_id") for item in fallback.get("log_samples", [])]
        == ALL_SCENARIOS
        and all(
            item.get("attempted") is False
            and item.get("attempt_count") == 0
            and item.get("silent_drop") is False
            and item.get("parser_switch_performed") is False
            for item in fallback.get("log_samples", [])
        )
        and fallback.get("runtime_owner") == "STAGE-048"
        and fallback.get("fallback_execution_allowed") is False
        and fallback.get("fallback_attempt_allowed") is False
        and metrics.get("required_scenario_count") == 16
        and metrics.get("required_accepted_output_count") == 11
        and metrics.get("required_rejected_output_count") == 3
        and metrics.get("required_route_no_output_count") == 2
        and set(failure_scenarios) == FAILURE_SCENARIOS
        and len(failure_scenarios) == len(set(failure_scenarios)) == 10
        and len(failures) == 7
        and all(
            item.get("fail_closed") is True
            and item.get("fallback_execution_performed") is False
            for item in failures.values()
        )
        and support.get("control_supported_formats") == SUPPORTED_TYPES
        and support.get("runtime_supported_formats") == []
        and support.get("parser_runtime_available") is False
        and support.get("fallback_runtime_available") is False
        and versions.get("control_versions_are_runtime_versions") is False
        and versions.get("runtime_parser_version_count") == 0
        and versions.get("configuration_change_performed") is False
        and rollback.get("rollback_target_commit")
        == EXPECTED_PHASE3_COMMIT["commit"]
        and rollback.get("rollback_target_kmids_tree")
        == EXPECTED_PHASE3_COMMIT["kmids_tree"]
        and rollback.get("configuration_change_performed") is False
        and rollback.get("parser_configuration_file_created") is False
        and review.get("current_gate") == P4_GATE
        and review.get("next_gate") == REVIEW_GATE
        and review.get("next_task_id") == "IDS-V0_1-STAGE047-REVIEW"
        and review.get("must_run_separately") is True
        and review.get("phase4_may_mark_stage_reviewed") is False
        and review.get("stage048_entry_allowed") is False
        and review.get("batch_review_allowed") is False
        and review.get("github_upload_allowed") is False
        and review.get("app_reinstall_allowed") is False
        and set(truth) == TRUE_TRUTH_FLAGS | FALSE_TRUTH_FLAGS
        and all(truth.get(name) is True for name in TRUE_TRUTH_FLAGS)
        and all(truth.get(name) is False for name in FALSE_TRUTH_FLAGS)
    )


def load_delivery_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def validate_delivery_contract(contract: Any) -> dict[str, bool]:
    if not isinstance(contract, Mapping):
        return {"mapping": False}
    return {
        "root_exact_shape": set(contract) == EXPECTED_ROOT_KEYS,
        "canonical_contract_identity": (
            _canonical_sha256(contract) == CANONICAL_CONTRACT_SHA256
        ),
        "identity_exact": (
            contract.get("schema_version") == SCHEMA_VERSION
            and contract.get("stage") == "STAGE-047"
            and contract.get("phase") == "Phase 4"
            and contract.get("task_id") == TASK_ID
            and contract.get("acceptance_id") == ACCEPTANCE_ID
            and contract.get("local_code") == "D08-S003"
            and contract.get("valid_result") == VALID_RESULT
            and contract.get("stage_review_status") == "pending_next_run"
            and contract.get("next_gate") == REVIEW_GATE
        ),
        "source_binding_exact": contract.get("source_binding") == EXPECTED_SOURCE,
        "source_binding_live": _source_binding_live(),
        "phase3_commit_bound": _phase3_commit_bound(
            contract.get("phase3_commit_binding")
        ),
        "phase3_artifacts_exact": (
            contract.get("phase3_artifact_bindings") == EXPECTED_PHASE3_ARTIFACTS
        ),
        "phase3_artifacts_live": _phase3_artifacts_live(
            contract.get("phase3_artifact_bindings")
        ),
        "section_boundaries_fail_closed": _section_boundaries_valid(contract),
    }


def _blank_report(
    contract_checks: Optional[Mapping[str, bool]] = None,
    *,
    contract_valid: bool = False,
    delivery_checks_performed: bool = False,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": "STAGE-047",
        "phase": "Phase 4",
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "execution_mode": "FAIL_CLOSED_NO_DELIVERY_EXECUTION",
        "contract_valid": contract_valid,
        "delivery_contract_valid": False,
        "contract_checks": dict(contract_checks or {}),
        "delivery_checks_performed": delivery_checks_performed,
        "delivery_checks": {},
        "phase3_scenarios_valid": False,
        "parser_output_samples": {},
        "fallback_log_samples": [],
        "quality_metrics": {},
        "failure_classification": {},
        "support_boundary": {},
        "version_evidence": {},
        "configuration_rollback": {},
        "known_limits": [],
        "stage_review_status": "not_started",
        "next_gate": P4_GATE,
        "execution_ready": False,
        "owner_feedback_zh": "Stage047 第四阶段合同无效，已失败关闭且未生成交付证据。",
        "result": "FAIL_CLOSED_INVALID_DELIVERY_CONTRACT",
        "valid": False,
    }
    report.update({name: False for name in TRUE_TRUTH_FLAGS | FALSE_TRUTH_FLAGS})
    return report


def _output_projection(payload: Mapping[str, Any]) -> dict[str, Any]:
    errors = payload.get("errors", [])
    return {
        "text": {
            "present": isinstance(payload.get("text"), str)
            and bool(payload.get("text")),
            "content_retained": False,
        },
        "tables": {
            "count": len(payload.get("tables", [])),
            "cell_content_retained": False,
        },
        "pages": {
            "count": len(payload.get("pages", [])),
            "text_content_retained": False,
        },
        "sections": {
            "count": len(payload.get("sections", [])),
            "text_content_retained": False,
        },
        "confidence": payload.get("confidence"),
        "errors": {
            "count": len(errors),
            "safe_codes": [item.get("code") for item in errors],
            "raw_error_retained": False,
        },
    }


def _parser_output_samples(
    contract: Mapping[str, Any],
    phase3_module: Any,
    scenario_results: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    sample_contract = contract["output_samples_contract"]
    samples: dict[str, dict[str, Any]] = {}
    for scenario_id in sample_contract["sample_scenario_ids"]:
        scenario = scenario_results[scenario_id]
        detected_type = scenario["detected_type"]
        route = phase3_module.FORMAT_CONTROL_ROUTES[detected_type]
        payload = phase3_module._scenario_payload(scenario_id)
        samples[scenario_id] = {
            "scenario_id": scenario_id,
            "sample_status": sample_contract["sample_status"],
            "detected_type": detected_type,
            "candidate_route_id": route["candidate_route_id"],
            "parser_family": route["parser_family"],
            "parser_version": route["parser_version"],
            "output_id": scenario["output_id"],
            "output_status": scenario["output_status"],
            "quality_gate_state": scenario["quality_gate_state"],
            "output_projection": _output_projection(payload),
            "content_label": scenario["content_label"],
            "content_interpretation": scenario["content_interpretation"],
            "formula_text_preserved": scenario["formula_text_preserved"],
            "raw_content_retained": False,
            "parser_dispatch_performed": False,
            "parser_execution_performed": False,
            "quality_gate_evaluation_performed": False,
            "persistent_write_performed": False,
        }
    return samples


def _fallback_log_samples(
    contract: Mapping[str, Any], scenario_results: Mapping[str, Any]
) -> list[dict[str, Any]]:
    fallback = contract["fallback_log_contract"]
    samples = []
    for spec in fallback["log_samples"]:
        scenario = scenario_results[spec["scenario_id"]]
        samples.append(
            {
                "scenario_id": spec["scenario_id"],
                "sample_status": fallback["sample_status"],
                "detected_type": scenario["detected_type"],
                "result_category": scenario["result_category"],
                "output_status": scenario["output_status"],
                "quality_gate_state": scenario["quality_gate_state"],
                "normalization_result_code": scenario["normalization_result_code"],
                "fallback_disposition": scenario["fallback_disposition"],
                "explicit_disposition": scenario["explicit_disposition"],
                "fallback_state": spec["fallback_state"],
                "attempted": False,
                "attempt_count": 0,
                "silent_drop": False,
                "parser_switch_performed": False,
                "runtime_owner": fallback["runtime_owner"],
            }
        )
    return samples


def _quality_metrics(scenario_results: Mapping[str, Any]) -> dict[str, Any]:
    values = list(scenario_results.values())
    scenario_count = len(values)
    passed_count = sum(item["status"] == "PASS" for item in values)
    supported_observed = {
        item["detected_type"]
        for item in values
        if item["detected_type"] in SUPPORTED_TYPES
    }
    status_counts = Counter(
        item["output_status"] for item in values if item["output_status"] is not None
    )
    disposition_counts = Counter(item["fallback_disposition"] for item in values)
    output_ids = [item["output_id"] for item in values if item["output_id"]]
    return {
        "scenario_count": scenario_count,
        "passed_scenario_count": passed_count,
        "scenario_pass_rate": passed_count / scenario_count if scenario_count else 0.0,
        "supported_format_expected_count": len(SUPPORTED_TYPES),
        "supported_format_observed_count": len(supported_observed),
        "supported_format_coverage_ratio": len(supported_observed)
        / len(SUPPORTED_TYPES),
        "accepted_output_count": sum(
            item["result_category"] == "ACCEPTED_OUTPUT"
            and item["accepted"] is True
            for item in values
        ),
        "rejected_output_count": sum(
            item["result_category"] == "REJECTED_OUTPUT"
            and item["accepted"] is False
            for item in values
        ),
        "route_no_output_count": sum(
            item["result_category"] == "ROUTE_NO_OUTPUT" for item in values
        ),
        "status_counts": {
            name: status_counts.get(name, 0)
            for name in (
                "OUTPUT_CANDIDATE_NOT_VALIDATED",
                "OUTPUT_PARTIAL_REVIEW_REQUIRED",
                "OUTPUT_FAILED_EXPLICIT",
            )
        },
        "fallback_disposition_counts": {
            name: disposition_counts.get(name, 0)
            for name in (
                "CANDIDATE_OUTPUT_NO_FALLBACK",
                "QUALITY_REVIEW_REQUIRED_NO_FALLBACK",
                "EXPLICIT_FAILURE_NO_FALLBACK",
                "OWNER_REVIEW_REQUIRED_STAGE048_NOT_RUN",
                "EXPLICIT_ROUTE_ERROR_STAGE048_NOT_RUN",
                "REJECTED_FAIL_CLOSED_NO_FALLBACK",
            )
        },
        "unique_output_id_count": len(set(output_ids)),
        "explicit_disposition_count": sum(
            item["explicit_disposition"] is True for item in values
        ),
        "silent_drop_count": sum(item["silent_drop"] is True for item in values),
        "parser_execution_count": sum(
            item["parser_execution_performed"] is True for item in values
        ),
        "fallback_execution_count": sum(
            item["fallback_execution_performed"] is True for item in values
        ),
        "persistent_write_count": sum(
            item["persistent_write_performed"] is True for item in values
        ),
    }


def _expected_metrics(contract: Mapping[str, Any]) -> dict[str, Any]:
    expected = contract["quality_metrics_contract"]
    return {
        "scenario_count": expected["required_scenario_count"],
        "passed_scenario_count": expected["required_passed_scenario_count"],
        "scenario_pass_rate": expected["required_scenario_pass_rate"],
        "supported_format_expected_count": expected[
            "required_supported_format_count"
        ],
        "supported_format_observed_count": expected[
            "required_supported_format_count"
        ],
        "supported_format_coverage_ratio": expected[
            "required_supported_format_coverage_ratio"
        ],
        "accepted_output_count": expected["required_accepted_output_count"],
        "rejected_output_count": expected["required_rejected_output_count"],
        "route_no_output_count": expected["required_route_no_output_count"],
        "status_counts": expected["required_status_counts"],
        "fallback_disposition_counts": expected[
            "required_fallback_disposition_counts"
        ],
        "unique_output_id_count": expected["required_unique_output_id_count"],
        "explicit_disposition_count": expected[
            "required_explicit_disposition_count"
        ],
        "silent_drop_count": expected["required_silent_drop_count"],
        "parser_execution_count": expected["required_parser_execution_count"],
        "fallback_execution_count": expected["required_fallback_execution_count"],
        "persistent_write_count": expected["required_persistent_write_count"],
    }


def _failure_classification(
    contract: Mapping[str, Any], scenario_results: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    classifications: dict[str, dict[str, Any]] = {}
    for name, spec in contract["failure_classification_contract"].items():
        exact = all(
            scenario_results[scenario_id]["result_category"]
            == spec["result_category"]
            and scenario_results[scenario_id]["output_status"]
            == spec["output_status"]
            and scenario_results[scenario_id]["fallback_disposition"]
            == spec["fallback_disposition"]
            and scenario_results[scenario_id]["explicit_disposition"] is True
            and scenario_results[scenario_id]["silent_drop"] is False
            and scenario_results[scenario_id]["parser_execution_performed"] is False
            and scenario_results[scenario_id]["fallback_execution_performed"] is False
            for scenario_id in spec["scenario_ids"]
        )
        item = copy.deepcopy(spec)
        item["fail_closed"] = exact and spec["fail_closed"] is True
        item["fallback_execution_performed"] = False
        classifications[name] = item
    return classifications


def build_stage047_phase4_delivery_report(
    contract: Any = None, *, contract_path: Path = CONTRACT_PATH
) -> dict[str, Any]:
    if contract is None:
        contract = load_delivery_contract(contract_path)
    checks = validate_delivery_contract(contract)
    contract_valid = bool(checks) and all(checks.values())
    if not contract_valid or not isinstance(contract, Mapping):
        return _blank_report(checks)

    try:
        phase3_module = _load_module(PHASE3_CHECKER_PATH, "stage047_phase3_for_p4")
        phase3_report = phase3_module.build_stage047_phase3_report()
        scenario_results = phase3_report["scenario_results"]
        parser_samples = _parser_output_samples(
            contract, phase3_module, scenario_results
        )
        fallback_logs = _fallback_log_samples(contract, scenario_results)
        metrics = _quality_metrics(scenario_results)
        failures = _failure_classification(contract, scenario_results)
    except (KeyError, TypeError, ValueError, RuntimeError, OSError):
        return _blank_report(
            checks,
            contract_valid=True,
            delivery_checks_performed=True,
        )

    phase3_false_effects = (
        "ids_business_source_read_performed",
        "raw_metadata_content_accessed",
        "source_file_open_performed",
        "file_type_redetection_performed",
        "actual_business_route_evaluation_performed",
        "runtime_parser_selected",
        "parser_dispatch_performed",
        "parser_execution_performed",
        "ids_business_parser_output_produced",
        "fallback_execution_performed",
        "prompt_injection_scan_performed",
        "formula_execution_performed",
        "quality_gate_evaluation_performed",
        "evidence_promotion_performed",
        "persistent_state_write_performed",
        "database_connection_performed",
        "runtime_output_written",
        "production_runtime_activation_performed",
        "phase4_started",
        "whole_stage_review_performed",
        "batch_review_performed",
        "github_upload_allowed",
        "push_allowed",
        "app_reinstall_allowed",
    )
    phase3_valid = (
        phase3_report.get("valid") is True
        and phase3_report.get("result") == PHASE3_VALID_RESULT
        and phase3_report.get("scenario_count") == 16
        and phase3_report.get("passed_scenario_count") == 16
        and phase3_report.get("accepted_output_count") == 11
        and phase3_report.get("rejected_output_count") == 3
        and phase3_report.get("route_no_output_count") == 2
        and phase3_report.get("status_counts")
        == {
            "OUTPUT_CANDIDATE_NOT_VALIDATED": 6,
            "OUTPUT_PARTIAL_REVIEW_REQUIRED": 4,
            "OUTPUT_FAILED_EXPLICIT": 1,
        }
        and phase3_report.get("unique_output_id_count") == 11
        and phase3_report.get("silent_drop_count") == 0
        and isinstance(scenario_results, Mapping)
        and list(scenario_results) == ALL_SCENARIOS
        and all(phase3_report.get(name) is False for name in phase3_false_effects)
    )
    required_sample_fields = set(
        contract["output_samples_contract"]["required_sample_fields"]
    )
    samples_valid = (
        list(parser_samples) == SAMPLE_SCENARIOS
        and len(parser_samples) == 8
        and [item["detected_type"] for item in parser_samples.values()]
        == SUPPORTED_TYPES
        and all(set(sample) == required_sample_fields for sample in parser_samples.values())
        and all(
            set(sample["output_projection"]) == set(OUTPUT_FIELDS)
            and sample["sample_status"]
            == "RECOMPUTED_SANITIZED_CONTROL_OUTPUT_NOT_RUNTIME"
            and sample["content_label"] == "UNTRUSTED_EVIDENCE_TEXT"
            and sample["content_interpretation"] == "EVIDENCE_ONLY"
            and sample["raw_content_retained"] is False
            and sample["parser_dispatch_performed"] is False
            and sample["parser_execution_performed"] is False
            and sample["quality_gate_evaluation_performed"] is False
            and sample["persistent_write_performed"] is False
            for sample in parser_samples.values()
        )
        and "=1+1" not in json.dumps(parser_samples, ensure_ascii=False)
        and "UNSAFE_CONTROL_TEXT_MUST_NOT_BE_ECHOED"
        not in json.dumps(parser_samples, ensure_ascii=False)
    )
    required_log_fields = set(contract["fallback_log_contract"]["required_log_fields"])
    fallback_specs = contract["fallback_log_contract"]["log_samples"]
    fallback_valid = (
        len(fallback_logs) == 16
        and [item["scenario_id"] for item in fallback_logs] == ALL_SCENARIOS
        and all(set(item) == required_log_fields for item in fallback_logs)
        and all(
            item["fallback_state"] == spec["fallback_state"]
            and item["explicit_disposition"] is True
            and item["attempted"] is False
            and item["attempt_count"] == 0
            and item["silent_drop"] is False
            and item["parser_switch_performed"] is False
            and item["runtime_owner"] == "STAGE-048"
            for item, spec in zip(fallback_logs, fallback_specs)
        )
    )
    metrics_valid = metrics == _expected_metrics(contract)
    failures_valid = failures == contract["failure_classification_contract"]
    truth_flags = contract["truth_flags"]
    truth_valid = (
        set(truth_flags) == TRUE_TRUTH_FLAGS | FALSE_TRUTH_FLAGS
        and all(truth_flags[name] is True for name in TRUE_TRUTH_FLAGS)
        and all(truth_flags[name] is False for name in FALSE_TRUTH_FLAGS)
    )
    delivery_checks = {
        "phase3_scenarios_replayed_valid": phase3_valid,
        "sanitized_parser_output_samples_valid": samples_valid,
        "fallback_log_samples_valid": fallback_valid,
        "quality_metrics_valid": metrics_valid,
        "failure_classification_valid": failures_valid,
        "truth_flags_valid": truth_valid,
        "no_runtime_or_external_effects": all(
            truth_flags[name] is False for name in FALSE_TRUTH_FLAGS
        ),
    }
    delivery_valid = all(delivery_checks.values())
    owner_feedback = " ".join(contract["owner_feedback_contract"].values())
    report: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": "STAGE-047",
        "phase": "Phase 4",
        "task_id": TASK_ID,
        "acceptance_id": ACCEPTANCE_ID,
        "execution_mode": contract["execution_mode"],
        "contract_valid": contract_valid,
        "delivery_contract_valid": delivery_valid,
        "contract_checks": checks,
        "delivery_checks_performed": True,
        "delivery_checks": delivery_checks,
        "phase3_scenarios_valid": phase3_valid,
        "parser_output_samples": parser_samples,
        "fallback_log_samples": fallback_logs,
        "quality_metrics": metrics,
        "failure_classification": failures,
        "support_boundary": copy.deepcopy(contract["support_boundary"]),
        "version_evidence": copy.deepcopy(contract["version_evidence_contract"]),
        "configuration_rollback": copy.deepcopy(contract["configuration_rollback"]),
        "known_limits": copy.deepcopy(contract["known_limits"]),
        "stage_review_status": contract["stage_review_status"],
        "next_gate": contract["next_gate"] if delivery_valid else P4_GATE,
        "execution_ready": False,
        "owner_feedback_zh": owner_feedback,
        "result": VALID_RESULT if delivery_valid else "FAIL_CLOSED_DELIVERY_EVIDENCE",
        "valid": delivery_valid,
    }
    report.update(copy.deepcopy(truth_flags))
    return report


def main() -> int:
    report = build_stage047_phase4_delivery_report()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
