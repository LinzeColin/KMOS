#!/usr/bin/env python3
"""Fail-closed STAGE-046 Phase 4 delivery checker.

The checker replays the committed Phase 3 metadata-only routing scenarios and
derives schema-only parser-output samples, non-runtime fallback control logs,
quality metrics, and bounded failure classifications. It never opens an IDS
business source file and never dispatches a parser or fallback runtime.
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
CONTRACT_PATH = (
    BASE / "parser_routing/stage046_parser_routing_delivery_contract.json"
)
PHASE3_CHECKER_PATH = PROJECT_ROOT / "scripts/check_parser_routing_scenarios.py"

SCHEMA_VERSION = "ids.stage046.parser_routing.phase4.delivery.v1"
REPORT_SCHEMA_VERSION = "ids.stage046.parser_routing.phase4.report.v1"
TASK_ID = "IDS-V0_1-STAGE046-P4"
ACCEPTANCE_ID = "ACC-STAGE-046"
P4_GATE = "IDS-STAGE046-P4-GATE"
REVIEW_GATE = "IDS-STAGE046-REVIEW-GATE"
VALID_RESULT = "PASS_ISOLATED_PARSER_ROUTING_CLOSEOUT_PARSER_DISABLED"
PHASE3_VALID_RESULT = "PASS_ISOLATED_PARSER_ROUTING_SCENARIOS_PARSER_DISABLED"
ROUTER_VERSION = "ids.parser_router.v0_1.stage046.p2"
REGISTRY_VERSION = "ids.parser_route_registry.v0_1.stage046.p2"
CANONICAL_CONTRACT_SHA256 = (
    "96d99ba148a7447084794625daf9b12ba64f3c7352fe2e34ad581deedbfe6db6"
)

EXPECTED_ROOT_KEYS = {
    "schema_version",
    "stage",
    "phase",
    "task_id",
    "acceptance_id",
    "execution_mode",
    "valid_result",
    "contract_state",
    "stage_review_status",
    "next_gate",
    "source_binding",
    "phase3_commit_binding",
    "upstream_bindings",
    "parser_output_samples_contract",
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
        "STAGE-046_解析器路由合同.md"
    ),
    "source_member_match_count": 1,
    "source_member_sha256": (
        "955cdf40f365c05853a87269eb02aa46e5922807e0bb0c48d9b99cfca9bc1d39"
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
    "commit": "49b876ec68ec8f92f0b9df72d57cca7b2d1d3344",
    "root_tree": "974c9917128938f133c64f5752c26502704e90ae",
    "kmids_tree": "d1eba5655e94697a2381c141a7c55b0e3892d1a6",
    "parent": "18c45ee39522891abe4ef65ed609eb5482f2f148",
    "required_ancestor_of_head": True,
}

EXPECTED_UPSTREAM = {
    "stage046_phase3_evidence": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "STAGE046_PHASE3_PARSER_ROUTING_SCENARIOS.md"
        ),
        "sha256": (
            "fa603715547ec41df2ad0f36aab8fa8484f4ed0fba44d5ed1cfffdfec0a7b181"
        ),
    },
    "stage046_phase3_contract": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/parser_routing/"
            "stage046_parser_routing_scenarios_contract.json"
        ),
        "sha256": (
            "f9bbfe5913bb99762bf927028a509b14b83f6a2f491bfd08d32b7f285382a067"
        ),
    },
    "stage046_phase3_checker": {
        "ref": "KM_IDSystem/scripts/check_parser_routing_scenarios.py",
        "sha256": (
            "4bc1622bdd7668bf599609deb281ebde4d2f404abd840010fa43c53a82c82dca"
        ),
    },
    "stage046_phase3_tests": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
            "test_stage046_parser_routing_scenarios.py"
        ),
        "sha256": (
            "30c0387c08cdbe0274824d67c4ffbb0499ea2f01e4d9cbfd7b8bbc8b9f0c610b"
        ),
    },
    "stage046_phase3_run": {
        "ref": "KM_IDSystem/machine/runs/2026-07-22-stage046-p3-local.json",
        "sha256": (
            "0c2d919db3db91f03e4e266bb5ea0f2bfb2ce1101b47deff40e69d43f95fafff"
        ),
    },
}

ROUTE_CONTRACTS = [
    {"route_id": "ROUTE_PDF", "parser_family": "PDF_PARSER", "accepted_types": ["PDF"]},
    {"route_id": "ROUTE_OOXML_WORD", "parser_family": "OOXML_WORD_PARSER", "accepted_types": ["DOCX"]},
    {"route_id": "ROUTE_OOXML_WORKBOOK", "parser_family": "OOXML_WORKBOOK_PARSER", "accepted_types": ["XLSX"]},
    {"route_id": "ROUTE_DELIMITED_TEXT", "parser_family": "DELIMITED_TEXT_PARSER", "accepted_types": ["CSV"]},
    {"route_id": "ROUTE_PLAIN_TEXT", "parser_family": "PLAIN_TEXT_PARSER", "accepted_types": ["TXT"]},
    {"route_id": "ROUTE_IMAGE", "parser_family": "IMAGE_PARSER", "accepted_types": ["PNG", "JPEG", "TIFF"]},
]
ROUTE_IDS = [item["route_id"] for item in ROUTE_CONTRACTS]
SUPPORTED_FORMATS = ["PDF", "DOCX", "XLSX", "CSV", "TXT", "PNG", "JPEG", "TIFF"]
PARSER_OUTPUT_FIELDS = ["text", "tables", "pages", "sections", "confidence", "errors"]
DEFAULT_OUTPUT = {
    "text": None,
    "tables": [],
    "pages": [],
    "sections": [],
    "confidence": "UNKNOWN",
    "errors": [],
}
SCENARIOS = [
    "pdf_high_candidate_parser_unavailable",
    "docx_high_candidate_parser_unavailable",
    "xlsx_high_candidate_parser_unavailable",
    "csv_medium_quality_review",
    "txt_medium_quality_review",
    "png_high_candidate_parser_unavailable",
    "jpeg_high_candidate_parser_unavailable",
    "tiff_high_candidate_parser_unavailable",
    "unknown_requires_owner_review",
    "corrupt_input_blocks_explicitly",
    "conflict_requires_owner_review",
    "extension_only_low_requires_owner_review",
    "unsupported_format_is_explicit",
    "instruction_like_text_cannot_override_policy",
]

TRUE_TRUTH_FLAGS = {
    "taskpack_source_read_performed",
    "phase3_checker_replayed",
    "parser_output_schema_samples_composed",
    "fallback_log_samples_derived",
    "quality_metrics_derived",
    "failure_classification_composed",
    "support_boundary_documented",
    "configuration_rollback_documented",
}
FALSE_TRUTH_FLAGS = {
    "source_file_open_performed",
    "filesystem_scan_performed",
    "file_hash_performed",
    "file_type_redetection_performed",
    "ids_business_source_read_performed",
    "raw_metadata_content_accessed",
    "fake_ids_business_data_used",
    "real_ids_business_job_created",
    "parser_dispatch_performed",
    "parser_execution_performed",
    "parser_output_produced",
    "fallback_execution_performed",
    "fallback_attempt_performed",
    "runtime_fallback_log_produced",
    "parser_configuration_mutated",
    "high_confidence_evidence_write_performed",
    "manifest_write_performed",
    "evidence_ledger_write_performed",
    "audit_write_performed",
    "job_creation_performed",
    "state_transition_performed",
    "persistent_state_write_performed",
    "database_connection_performed",
    "schema_change_performed",
    "runtime_output_written",
    "production_runtime_activation_performed",
    "whole_stage_review_performed",
    "batch_review_performed",
    "github_upload_allowed",
    "push_allowed",
    "app_reinstall_allowed",
    "stage047_entry_allowed",
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


def _git_output(*args: str) -> Optional[str]:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _phase3_commit_bound(value: Any) -> bool:
    if value != EXPECTED_PHASE3_COMMIT:
        return False
    commit = EXPECTED_PHASE3_COMMIT["commit"]
    observed = _git_output("show", "-s", "--format=%H%n%T%n%P", commit)
    kmids_tree = _git_output("rev-parse", f"{commit}:KM_IDSystem")
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


def _index_bytes(relative: str) -> Optional[bytes]:
    try:
        return subprocess.check_output(
            ["git", "show", f":{relative}"],
            cwd=REPO_ROOT,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return None


def _upstream_bindings_live(value: Any) -> bool:
    if value != EXPECTED_UPSTREAM or not isinstance(value, Mapping):
        return False
    for binding in value.values():
        ref = binding.get("ref")
        if not _safe_repo_ref(ref):
            return False
        payload = _index_bytes(ref)
        if payload is None or _sha256_bytes(payload) != binding.get("sha256"):
            return False
    return True


def _section_boundaries_valid(contract: Mapping[str, Any]) -> bool:
    samples = contract.get("parser_output_samples_contract", {})
    fallback = contract.get("fallback_log_contract", {})
    failures = contract.get("failure_classification_contract", {})
    review = contract.get("review_gate", {})
    truth = contract.get("truth_flags", {})
    failure_scenarios = [
        scenario
        for spec in failures.values()
        for scenario in spec.get("scenario_ids", [])
    ] if isinstance(failures, Mapping) else []
    return (
        samples.get("route_contracts") == ROUTE_CONTRACTS
        and samples.get("required_output_fields") == PARSER_OUTPUT_FIELDS
        and samples.get("default_output") == DEFAULT_OUTPUT
        and samples.get("parser_version_placeholder") == "UNASSIGNED_NOT_IMPLEMENTED"
        and samples.get("parser_dispatch_allowed") is False
        and samples.get("parser_execution_allowed") is False
        and samples.get("parser_output_write_allowed") is False
        and fallback.get("required_log_sample_count") == 14
        and [item.get("scenario_id") for item in fallback.get("log_samples", [])]
        == SCENARIOS
        and all(
            item.get("attempted") is False
            and item.get("attempt_count") == 0
            and item.get("silent_drop") is False
            and item.get("parser_switch_performed") is False
            for item in fallback.get("log_samples", [])
        )
        and set(failure_scenarios) == set(SCENARIOS)
        and len(failure_scenarios) == len(SCENARIOS)
        and len(set(failure_scenarios)) == 14
        and review.get("must_run_separately") is True
        and review.get("phase4_may_mark_stage_reviewed") is False
        and review.get("stage047_entry_allowed") is False
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
            and contract.get("stage") == "STAGE-046"
            and contract.get("phase") == "Phase 4"
            and contract.get("task_id") == TASK_ID
            and contract.get("acceptance_id") == ACCEPTANCE_ID
            and contract.get("valid_result") == VALID_RESULT
            and contract.get("stage_review_status") == "pending_next_run"
            and contract.get("next_gate") == REVIEW_GATE
        ),
        "source_binding_exact": contract.get("source_binding") == EXPECTED_SOURCE,
        "source_binding_live": _source_binding_live(),
        "phase3_commit_bound": _phase3_commit_bound(
            contract.get("phase3_commit_binding")
        ),
        "upstream_bindings_exact": (
            contract.get("upstream_bindings") == EXPECTED_UPSTREAM
        ),
        "upstream_bindings_live": _upstream_bindings_live(
            contract.get("upstream_bindings")
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
        "stage": "STAGE-046",
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
        "owner_feedback_zh": (
            "Stage046 步骤四合同无效，已失败关闭且未生成交付证据。"
        ),
        "result": "FAIL_CLOSED_INVALID_DELIVERY_CONTRACT",
        "valid": False,
    }
    report.update({name: False for name in TRUE_TRUTH_FLAGS | FALSE_TRUTH_FLAGS})
    return report


def _parser_output_samples(contract: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    sample_contract = contract["parser_output_samples_contract"]
    return {
        route["route_id"]: {
            "sample_status": sample_contract["sample_status"],
            "route_id": route["route_id"],
            "parser_family": route["parser_family"],
            "accepted_types": copy.deepcopy(route["accepted_types"]),
            "parser_version": sample_contract["parser_version_placeholder"],
            "output": copy.deepcopy(sample_contract["default_output"]),
            "content_fields_are_untrusted_evidence": sample_contract[
                "content_fields_are_untrusted_evidence"
            ],
            "parser_dispatch_performed": False,
            "parser_execution_performed": False,
        }
        for route in sample_contract["route_contracts"]
    }


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
                "detection_state": scenario["detection_state"],
                "detection_confidence": scenario["detection_confidence"],
                "route_action": scenario["route_action"],
                "governed_route_id": scenario["governed_route_id"],
                "candidate_route_id": scenario["candidate_route_id"],
                "parser_family": scenario["parser_family"],
                "parser_version": scenario["parser_version"],
                "quality_disposition": scenario["quality_disposition"],
                "error_codes": copy.deepcopy(scenario["errors"]),
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
    confidence_counts = Counter(item["detection_confidence"] for item in values)
    disposition_counts = Counter(item["quality_disposition"] for item in values)
    observed_formats = {
        item["detected_type"]
        for item in values
        if item["detected_type"] in SUPPORTED_FORMATS
    }
    governed_route_ids = {
        item["governed_route_id"]
        for item in values
        if item["detected_type"] in SUPPORTED_FORMATS
        and item["governed_route_id"] is not None
    }
    selected_route_ids = {
        item["candidate_route_id"]
        for item in values
        if item["candidate_route_id"] is not None
    }
    scenario_count = len(values)
    passed_count = sum(item["status"] == "PASS" for item in values)
    return {
        "scenario_count": scenario_count,
        "passed_scenario_count": passed_count,
        "scenario_pass_rate": passed_count / scenario_count if scenario_count else 0.0,
        "governed_format_expected_count": len(SUPPORTED_FORMATS),
        "governed_format_observed_count": len(observed_formats),
        "governed_format_coverage_ratio": len(observed_formats)
        / len(SUPPORTED_FORMATS),
        "governed_route_family_count": len(governed_route_ids),
        "selected_candidate_route_id_count": len(selected_route_ids),
        "confidence_counts": {
            name: confidence_counts.get(name, 0)
            for name in ("HIGH", "MEDIUM", "LOW", "UNKNOWN")
        },
        "quality_disposition_counts": {
            name: disposition_counts.get(name, 0)
            for name in (
                "PRIMARY_ROUTE_CANDIDATE_PARSER_UNAVAILABLE",
                "QUALITY_REVIEW_REQUIRED",
                "OWNER_REVIEW_REQUIRED",
                "EXPLICIT_ERROR_NO_FALLBACK",
                "UNSUPPORTED_EXPLICIT_NO_FALLBACK",
            )
        },
        "explicit_disposition_count": sum(
            item["explicit_disposition"] is True for item in values
        ),
        "results_with_error_codes": sum(bool(item["errors"]) for item in values),
        "silent_drop_count": sum(item["silent_drop"] is True for item in values),
        "parser_output_produced_count": sum(bool(item["output_refs"]) for item in values),
        "fallback_execution_count": sum(
            item["fallback_execution_performed"] is True for item in values
        ),
    }


def _expected_metrics(contract: Mapping[str, Any]) -> dict[str, Any]:
    expected = contract["quality_metrics_contract"]
    return {
        "scenario_count": expected["required_scenario_count"],
        "passed_scenario_count": expected["required_passed_scenario_count"],
        "scenario_pass_rate": expected["required_scenario_pass_rate"],
        "governed_format_expected_count": expected["required_governed_format_count"],
        "governed_format_observed_count": expected["required_governed_format_count"],
        "governed_format_coverage_ratio": expected[
            "required_governed_format_coverage_ratio"
        ],
        "governed_route_family_count": expected[
            "required_governed_route_family_count"
        ],
        "selected_candidate_route_id_count": expected[
            "required_selected_candidate_route_id_count"
        ],
        "confidence_counts": expected["required_confidence_counts"],
        "quality_disposition_counts": expected[
            "required_quality_disposition_counts"
        ],
        "explicit_disposition_count": expected[
            "required_explicit_disposition_count"
        ],
        "results_with_error_codes": expected["required_results_with_error_codes"],
        "silent_drop_count": expected["required_silent_drop_count"],
        "parser_output_produced_count": expected[
            "required_parser_output_produced_count"
        ],
        "fallback_execution_count": expected["required_fallback_execution_count"],
    }


def _failure_classification(
    contract: Mapping[str, Any], scenario_results: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    classifications = {}
    for name, spec in contract["failure_classification_contract"].items():
        exact = True
        for scenario_id in spec["scenario_ids"]:
            scenario = scenario_results[scenario_id]
            exact = exact and (
                scenario["errors"] == spec["error_codes"]
                and scenario["quality_disposition"] == spec["disposition"]
                and scenario["parser_dispatch_performed"] is False
                and scenario["parser_execution_performed"] is False
                and scenario["fallback_execution_performed"] is False
                and scenario["silent_drop"] is False
            )
        item = copy.deepcopy(spec)
        item["fail_closed"] = exact
        classifications[name] = item
    return classifications


def build_stage046_phase4_delivery_report(
    contract: Any = None, *, contract_path: Path = CONTRACT_PATH
) -> dict[str, Any]:
    if contract is None:
        contract = load_delivery_contract(contract_path)
    checks = validate_delivery_contract(contract)
    contract_valid = bool(checks) and all(checks.values())
    if not contract_valid or not isinstance(contract, Mapping):
        return _blank_report(checks)

    try:
        phase3_module = _load_module(PHASE3_CHECKER_PATH, "stage046_phase3_for_p4")
        phase3_report = phase3_module.build_stage046_phase3_report()
        scenario_results = phase3_report["scenario_results"]
        parser_samples = _parser_output_samples(contract)
        fallback_logs = _fallback_log_samples(contract, scenario_results)
        metrics = _quality_metrics(scenario_results)
        failures = _failure_classification(contract, scenario_results)
    except (KeyError, TypeError, ValueError, RuntimeError, OSError):
        return _blank_report(
            checks,
            contract_valid=True,
            delivery_checks_performed=True,
        )

    false_effect_keys = (
        "source_file_open_performed",
        "filesystem_scan_performed",
        "file_hash_performed",
        "file_type_redetection_performed",
        "ids_business_source_read_performed",
        "raw_metadata_content_accessed",
        "parser_dispatch_performed",
        "parser_execution_performed",
        "fallback_execution_performed",
        "parser_output_produced",
        "persistent_state_write_performed",
        "database_connection_performed",
        "runtime_output_written",
        "production_runtime_activation_performed",
        "whole_stage_review_performed",
        "batch_review_performed",
        "github_upload_allowed",
        "app_reinstall_allowed",
    )
    phase3_valid = (
        phase3_report.get("valid") is True
        and phase3_report.get("result") == PHASE3_VALID_RESULT
        and phase3_report.get("scenario_count") == 14
        and phase3_report.get("passed_scenario_count") == 14
        and phase3_report.get("explicit_disposition_count") == 14
        and phase3_report.get("silent_drop_count") == 0
        and isinstance(scenario_results, Mapping)
        and list(scenario_results) == SCENARIOS
        and all(phase3_report.get(name) is False for name in false_effect_keys)
    )
    samples_valid = (
        list(parser_samples) == ROUTE_IDS
        and all(
            set(sample["output"]) == set(PARSER_OUTPUT_FIELDS)
            and sample["output"] == DEFAULT_OUTPUT
            and sample["sample_status"] == "SCHEMA_ONLY_NOT_EXECUTED"
            and sample["parser_version"] == "UNASSIGNED_NOT_IMPLEMENTED"
            and sample["parser_dispatch_performed"] is False
            and sample["parser_execution_performed"] is False
            for sample in parser_samples.values()
        )
    )
    fallback_fields = set(contract["fallback_log_contract"]["required_log_fields"])
    fallback_specs = contract["fallback_log_contract"]["log_samples"]
    fallback_valid = (
        len(fallback_logs) == 14
        and [item["scenario_id"] for item in fallback_logs] == SCENARIOS
        and all(set(item) == fallback_fields for item in fallback_logs)
        and all(
            item["quality_disposition"] == spec["quality_disposition"]
            and item["fallback_state"] == spec["fallback_state"]
            and item["attempted"] is False
            and item["attempt_count"] == 0
            and item["silent_drop"] is False
            and item["parser_switch_performed"] is False
            for item, spec in zip(fallback_logs, fallback_specs)
        )
    )
    metrics_valid = metrics == _expected_metrics(contract)
    failures_valid = failures == contract["failure_classification_contract"]
    truth_flags = contract["truth_flags"]
    no_effects = all(truth_flags[name] is False for name in FALSE_TRUTH_FLAGS)
    delivery_checks = {
        "phase3_scenarios_replayed_valid": phase3_valid,
        "parser_output_schema_samples_valid": samples_valid,
        "fallback_log_samples_valid": fallback_valid,
        "quality_metrics_valid": metrics_valid,
        "failure_classification_valid": failures_valid,
        "truth_flags_valid": (
            set(truth_flags) == TRUE_TRUTH_FLAGS | FALSE_TRUTH_FLAGS
        ),
        "no_runtime_or_external_effects": no_effects,
    }
    delivery_valid = all(delivery_checks.values())
    owner_feedback = " ".join(contract["owner_feedback_contract"].values())
    report: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": "STAGE-046",
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
    report = build_stage046_phase4_delivery_report()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
