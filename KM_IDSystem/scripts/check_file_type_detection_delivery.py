#!/usr/bin/env python3
"""Fail-closed STAGE-045 Phase 4 delivery checker.

The checker replays the committed Phase 3 in-memory scenario checker and derives
schema-only parser-output samples, non-runtime fallback-log samples, quality
metrics, and bounded failure classifications. It never opens an IDS business
source file and never dispatches a parser or fallback runtime.
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
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
BASE = PROJECT_ROOT / "docs/pursuing_goal/ids_v0_1"
CONTRACT_PATH = (
    BASE
    / "file_type_detection/stage045_file_type_detection_delivery_contract.json"
)
PHASE3_CHECKER_PATH = PROJECT_ROOT / "scripts/check_file_type_detection_scenarios.py"

SCHEMA_VERSION = "ids.stage045.file_type_detection.phase4.delivery.v1"
REPORT_SCHEMA_VERSION = "ids.stage045.file_type_detection.phase4.report.v1"
TASK_ID = "IDS-V0_1-STAGE045-P4"
ACCEPTANCE_ID = "ACC-STAGE-045"
P4_GATE = "IDS-STAGE045-P4-GATE"
REVIEW_GATE = "IDS-STAGE045-REVIEW-GATE"
VALID_RESULT = "PASS_ISOLATED_FILE_TYPE_DETECTION_CLOSEOUT_PARSER_DISABLED"
PHASE3_VALID_RESULT = "PASS_ISOLATED_FILE_TYPE_DETECTION_SCENARIOS_PARSER_DISABLED"
DETECTOR_VERSION = "ids.file_type_detector.v0_1.stage045.p2"

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
    "source_archive_path": "/Users/linzezhang/Downloads/IDS_Taskpack_v0_1_only_中文修订版.zip",
    "source_archive_sha256": "55b782e338610aab6361b7945bb5e290ba60038a06cc765c7c2da801734db6d3",
    "source_member": "IDS_v0_1_Final_Chinese_Revised/stages/STAGE-045_文件类型检测.md",
    "source_member_match_count": 1,
    "source_member_sha256": "4eac237a7f63d764cf71789d4949a5168cbe8fe24e1fe7eb816baabe04bb4d27",
    "roadmap_path": "/Users/linzezhang/Downloads/IDS_Codex开发Roadmap_v0_1_only_中文修订版.txt",
    "roadmap_sha256": "a193fd2c44c51d634bf7887a1a6baf7e5199d9a8535e4211e35e97588e2e21a6",
    "instructions_path": "/Users/linzezhang/Downloads/IDS_Codex使用说明_v0_1_only_中文修订版.txt",
    "instructions_sha256": "ce456e06136d5ecc56cd7c9dc926abb5894817dda87bf7667588bf85211794f8",
    "source_verification_status": "SOURCE_VERIFIED",
}

EXPECTED_PHASE3_COMMIT = {
    "commit": "dea3c486aceaaa34837aa4a6c9262a907e8dccba",
    "root_tree": "ae1dfb9d1135cf578857fda9d6368ef0e2b4a4e7",
    "kmids_tree": "2a95d14bee023d2c1a3f4965a3206d0299c4b74d",
    "parent": "082565a958459fb4b9ad2b951a74982c30311a03",
    "required_ancestor_of_head": True,
}
FINAL_REVIEW_BASELINE_COMMIT = "76027b8dc89e325c212d492d7f5df88357ea7112"

EXPECTED_UPSTREAM = {
    "stage045_phase3_contract": {
        "ref": "KM_IDSystem/docs/pursuing_goal/ids_v0_1/file_type_detection/stage045_file_type_detection_scenarios_contract.json",
        "sha256": "3bb5b7e6ebc0a44f6f9b54090c9f382146c8e3c88b1df2d9d0336ca7692c99b6",
    },
    "stage045_phase3_checker": {
        "ref": "KM_IDSystem/scripts/check_file_type_detection_scenarios.py",
        "sha256": "ef3cdaf66c235becfaa4458ee2343ba9091d4ee05fa4f0ca36c9afa06d69e349",
    },
    "stage045_phase3_tests": {
        "ref": "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/test_stage045_file_type_detection_scenarios.py",
        "sha256": "8a6cae96dabe32bb34febdfe540ba36b7dd30e78a7bd80bdd0062d47377132c2",
    },
    "stage045_phase3_evidence": {
        "ref": "KM_IDSystem/docs/pursuing_goal/ids_v0_1/STAGE045_PHASE3_FILE_TYPE_DETECTION_SCENARIOS.md",
        "sha256": "e47906c732ac4136128dc839943ae2002cc8daff83b28feed3e04ad21400cea1",
    },
    "stage045_phase3_run": {
        "ref": "KM_IDSystem/machine/runs/2026-07-20-stage045-p3-local.json",
        "sha256": "a0e348b09d072d45eef57ac1dfe5953ff812b1f7463b76428af251061bd22384",
    },
}

PARSER_ROUTES = [
    "PDF_PARSER",
    "OOXML_WORD_PARSER",
    "OOXML_WORKBOOK_PARSER",
    "DELIMITED_TEXT_PARSER",
    "PLAIN_TEXT_PARSER",
    "IMAGE_PARSER",
]
PARSER_OUTPUT_FIELDS = [
    "text",
    "tables",
    "pages",
    "sections",
    "confidence",
    "errors",
]
DEFAULT_OUTPUT = {
    "text": None,
    "tables": [],
    "pages": [],
    "sections": [],
    "confidence": "UNKNOWN",
    "errors": [],
}
EXPECTED_PARSER_SAMPLES = {
    "sample_status": "SCHEMA_ONLY_NOT_EXECUTED",
    "required_output_fields": PARSER_OUTPUT_FIELDS,
    "route_candidates": PARSER_ROUTES,
    "parser_version_placeholder": "UNASSIGNED_STAGE046",
    "default_output": DEFAULT_OUTPUT,
    "content_fields_are_untrusted_evidence": True,
    "schema_sample_is_runtime_output": False,
    "parser_dispatch_allowed": False,
    "parser_execution_allowed": False,
    "parser_output_write_allowed": False,
    "high_confidence_evidence_write_allowed": False,
    "empty_runtime_output_silent_success_allowed": False,
}

FALLBACK_SAMPLE_SPECS = [
    (
        "matching_csv_text_route_candidate",
        "FALLBACK_REVIEW_REQUIRED",
        "QUALITY_REVIEW_REQUIRED",
    ),
    (
        "matching_txt_text_route_candidate",
        "FALLBACK_REVIEW_REQUIRED",
        "QUALITY_REVIEW_REQUIRED",
    ),
    (
        "instruction_like_text_cannot_override_system_policy",
        "FALLBACK_REVIEW_REQUIRED",
        "QUALITY_REVIEW_REQUIRED",
    ),
    (
        "unknown_binary_requires_owner_review",
        "FALLBACK_UNSUPPORTED",
        "OWNER_REVIEW_REQUIRED",
    ),
    (
        "corrupt_zip_blocks_with_explicit_error",
        "FALLBACK_FAILED_EXPLICITLY",
        "EXPLICIT_ERROR_NO_FALLBACK",
    ),
    (
        "conflicting_signature_mime_extension_requires_review",
        "FALLBACK_REVIEW_REQUIRED",
        "OWNER_REVIEW_REQUIRED",
    ),
    (
        "extension_only_low_confidence_requires_review",
        "FALLBACK_REVIEW_REQUIRED",
        "OWNER_REVIEW_REQUIRED",
    ),
]
FALLBACK_LOG_FIELDS = [
    "scenario_id",
    "sample_status",
    "detected_type",
    "detection_state",
    "confidence",
    "route_candidate",
    "fallback_state",
    "quality_disposition",
    "error_codes",
    "attempted",
    "attempt_count",
    "silent_drop",
    "parser_switch_performed",
    "runtime_owner",
]
EXPECTED_FALLBACK_LOG = {
    "sample_status": "DERIVED_CONTROL_LOG_SAMPLE_NOT_RUNTIME",
    "runtime_owner": "STAGE-048",
    "required_log_fields": FALLBACK_LOG_FIELDS,
    "log_samples": [
        {
            "scenario_id": scenario_id,
            "fallback_state": fallback_state,
            "quality_disposition": disposition,
            "attempted": False,
            "attempt_count": 0,
            "silent_drop": False,
            "parser_switch_performed": False,
        }
        for scenario_id, fallback_state, disposition in FALLBACK_SAMPLE_SPECS
    ],
    "required_log_sample_count": 7,
    "runtime_log_available": False,
    "fallback_execution_allowed": False,
    "silent_drop_allowed_count": 0,
    "silent_parser_switch_allowed": False,
}

EXPECTED_QUALITY = {
    "required_scenario_count": 14,
    "required_passed_scenario_count": 14,
    "required_scenario_pass_rate": 1.0,
    "required_supported_format_count": 8,
    "required_supported_format_coverage_ratio": 1.0,
    "required_confidence_counts": {
        "HIGH": 7,
        "MEDIUM": 3,
        "LOW": 1,
        "UNKNOWN": 3,
    },
    "required_quality_disposition_counts": {
        "PRIMARY_ROUTE_CANDIDATE_ONLY": 7,
        "QUALITY_REVIEW_REQUIRED": 3,
        "OWNER_REVIEW_REQUIRED": 3,
        "EXPLICIT_ERROR_NO_FALLBACK": 1,
    },
    "required_non_high_quality_result_count": 7,
    "required_explicitly_disposed_non_high_quality_count": 7,
    "required_results_with_error_codes": 3,
    "required_silent_drop_count": 0,
    "required_parser_output_produced_count": 0,
}

EXPECTED_FAILURES = {
    "UNKNOWN_BINARY": {
        "scenario_id": "unknown_binary_requires_owner_review",
        "detection_state": "TYPE_UNKNOWN_REVIEW_REQUIRED",
        "error_codes": ["NO_RELIABLE_TYPE_SIGNAL"],
        "disposition": "OWNER_REVIEW_REQUIRED",
        "fallback_state": "FALLBACK_UNSUPPORTED",
        "fail_closed": True,
    },
    "CORRUPT_ZIP_CONTAINER": {
        "scenario_id": "corrupt_zip_blocks_with_explicit_error",
        "detection_state": "TYPE_INPUT_BLOCKED",
        "error_codes": ["CORRUPT_ZIP_CONTAINER"],
        "disposition": "EXPLICIT_ERROR_NO_FALLBACK",
        "fallback_state": "FALLBACK_FAILED_EXPLICITLY",
        "fail_closed": True,
    },
    "SIGNAL_TYPE_CONFLICT": {
        "scenario_id": "conflicting_signature_mime_extension_requires_review",
        "detection_state": "TYPE_CONFLICT_REVIEW_REQUIRED",
        "error_codes": ["SIGNAL_TYPE_CONFLICT"],
        "disposition": "OWNER_REVIEW_REQUIRED",
        "fallback_state": "FALLBACK_REVIEW_REQUIRED",
        "fail_closed": True,
    },
    "EXTENSION_ONLY_LOW_CONFIDENCE": {
        "scenario_id": "extension_only_low_confidence_requires_review",
        "detection_state": "TYPE_PROVISIONAL",
        "error_codes": [],
        "disposition": "OWNER_REVIEW_REQUIRED",
        "fallback_state": "FALLBACK_REVIEW_REQUIRED",
        "fail_closed": True,
    },
}

SUPPORTED_FORMATS = ["PDF", "DOCX", "XLSX", "CSV", "TXT", "PNG", "JPEG", "TIFF"]
EXPECTED_SUPPORT_BOUNDARY = {
    "detection_candidate_formats": SUPPORTED_FORMATS,
    "failure_sentinel_types": ["UNKNOWN", "CORRUPT_OR_UNREADABLE"],
    "candidate_only_parser_routes": PARSER_ROUTES,
    "available_parser_routes": [],
    "not_claimed_format_classes": [
        "LEGACY_BINARY_OFFICE",
        "GENERIC_ARCHIVE",
        "AUDIO",
        "VIDEO",
        "EXECUTABLE",
        "UNRECOGNIZED_BINARY",
    ],
    "parser_runtime_available": False,
    "fallback_runtime_available": False,
    "detection_support_does_not_imply_parser_support": True,
    "unknown_unlisted_or_ambiguous_input_action": "OWNER_REVIEW_OR_EXPLICIT_ERROR",
}

EXPECTED_VERSION_EVIDENCE = {
    "detector_version": DETECTOR_VERSION,
    "parser_contract_owner": "STAGE-046",
    "parser_output_contract_owner": "STAGE-047",
    "fallback_runtime_owner": "STAGE-048",
    "parser_versions": {route: "UNASSIGNED_NOT_IMPLEMENTED" for route in PARSER_ROUTES},
}

ROLLBACK_STEPS = [
    "STOP_ON_INVALID_DELIVERY_CONTRACT",
    "RESTORE_PHASE3_SCENARIO_ONLY_STATE",
    "DISCARD_PHASE4_SCHEMA_SAMPLES_AND_DERIVED_LOGS",
    "PRESERVE_STAGE045_PHASE1_PHASE3_EVIDENCE",
    "KEEP_PARSER_FALLBACK_AND_PERSISTENCE_DISABLED",
    "PRESERVE_ORIGINAL_MANIFEST_EVIDENCE_AUDIT_REPORT_AND_INDEX_ARTIFACTS",
    "DO_NOT_OPEN_SCAN_HASH_PARSE_MOVE_OVERWRITE_OR_DELETE_REAL_SOURCE_PATHS",
]
EXPECTED_ROLLBACK = {
    "rollback_target_commit": EXPECTED_PHASE3_COMMIT["commit"],
    "rollback_target_kmids_tree": EXPECTED_PHASE3_COMMIT["kmids_tree"],
    "rollback_target_state": "PHASE3_SCENARIOS_ENABLED_PARSER_AND_FALLBACK_DISABLED",
    "configuration_change_performed": False,
    "parser_configuration_file_created": False,
    "steps": ROLLBACK_STEPS,
    "destructive_rollback_allowed": False,
}

EXPECTED_REVIEW_GATE = {
    "next_task_id": "IDS-V0_1-STAGE045-REVIEW",
    "must_run_separately": True,
    "phase4_may_mark_stage_reviewed": False,
    "stage046_entry_allowed": False,
    "batch_review_allowed": False,
    "github_upload_allowed": False,
    "app_reinstall_allowed": False,
}

EXPECTED_LIMITS = [
    "PARSER_OUTPUT_SAMPLES_ARE_SCHEMA_ONLY_NOT_RUNTIME_OUTPUT",
    "FALLBACK_LOG_SAMPLES_ARE_DERIVED_CONTROL_EVIDENCE_NOT_RUNTIME_LOGS",
    "NO_PARSER_VERSION_ASSIGNED_OR_IMPLEMENTED",
    "NO_PARSER_DISPATCH_EXECUTION_OR_OUTPUT",
    "NO_FALLBACK_EXECUTION_OR_RUNTIME_LOG",
    "NO_REAL_SOURCE_FILE_ACCESS_OR_FORMAT_PROBE",
    "NO_PRODUCTION_QUALITY_CALIBRATION",
    "NO_EVIDENCE_PROMOTION_OR_PERSISTENCE",
    "NO_STAGE045_WHOLE_STAGE_REVIEW_IN_THIS_RUN",
    "NO_STAGE046_ENTRY_IN_THIS_RUN",
    "STATIC_CLOSEOUT_IS_NOT_PRODUCTION_READINESS",
]

EXPECTED_OWNER_FEEDBACK = {
    "status_zh": "Stage045 步骤四隔离交付证据已收口；检测场景通过，但未执行解析器或回退。",
    "quality_zh": "十四个场景全部通过、支持格式覆盖为八类且静默丢弃为零；七个非高质量结果均有明确复核或错误处置。",
    "boundary_zh": "六类 parser route 仍只是候选，parser 版本尚未分配；样例仅说明输出结构，fallback 日志仅由步骤三控制证据派生。",
    "limit_zh": "下一步只能在独立 run 进行整阶段复审；本证据不是生产就绪证明。",
}

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
    "stage046_entry_allowed",
}
EXPECTED_TRUTH_FLAGS = {
    **{name: True for name in TRUE_TRUTH_FLAGS},
    **{name: False for name in FALSE_TRUTH_FLAGS},
}


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


def _source_binding_valid(value: Any) -> bool:
    if value != EXPECTED_SOURCE:
        return False
    try:
        archive = Path(value["source_archive_path"])
        roadmap = Path(value["roadmap_path"])
        instructions = Path(value["instructions_path"])
        if not all(path.is_file() for path in (archive, roadmap, instructions)):
            return False
        if _sha256(archive) != value["source_archive_sha256"]:
            return False
        if _sha256(roadmap) != value["roadmap_sha256"]:
            return False
        if _sha256(instructions) != value["instructions_sha256"]:
            return False
        with zipfile.ZipFile(archive) as bundle:
            matches = [
                name for name in bundle.namelist() if name == value["source_member"]
            ]
            if len(matches) != value["source_member_match_count"]:
                return False
            return _sha256_bytes(bundle.read(matches[0])) == value["source_member_sha256"]
    except (KeyError, OSError, zipfile.BadZipFile):
        return False


def _git_output(*args: str) -> Optional[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _phase3_commit_bound(value: Any) -> bool:
    if value != EXPECTED_PHASE3_COMMIT:
        return False
    commit = value["commit"]
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
    )
    if ancestor.returncode != 0:
        return False
    return (
        _git_output("rev-parse", f"{commit}^{{tree}}") == value["root_tree"]
        and _git_output("rev-parse", f"{commit}:KM_IDSystem")
        == value["kmids_tree"]
        and _git_output("rev-parse", f"{commit}^") == value["parent"]
    )


def _safe_repo_ref(value: Any) -> bool:
    if not isinstance(value, str) or not value.startswith("KM_IDSystem/"):
        return False
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts


def _final_review_bytes(relative: str) -> Optional[bytes]:
    completed = subprocess.run(
        ["git", "show", f"{FINAL_REVIEW_BASELINE_COMMIT}:{relative}"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout


def _upstream_bindings_valid(value: Any) -> bool:
    if value != EXPECTED_UPSTREAM:
        return False
    for binding in value.values():
        relative = binding.get("ref") if isinstance(binding, Mapping) else None
        if not _safe_repo_ref(relative):
            return False
        reviewed = _final_review_bytes(relative)
        if reviewed is None or _sha256_bytes(reviewed) != binding.get("sha256"):
            return False
    return True


def load_delivery_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def validate_delivery_contract(contract: Any) -> dict[str, bool]:
    mapping = contract if isinstance(contract, Mapping) else {}
    return {
        "root_shape_exact": set(mapping) == EXPECTED_ROOT_KEYS,
        "identity_exact": (
            mapping.get("schema_version") == SCHEMA_VERSION
            and mapping.get("stage") == "STAGE-045"
            and mapping.get("phase") == "Phase 4"
            and mapping.get("task_id") == TASK_ID
            and mapping.get("acceptance_id") == ACCEPTANCE_ID
            and mapping.get("execution_mode")
            == "ISOLATED_NON_PRODUCTION_FILE_TYPE_DETECTION_CLOSEOUT"
            and mapping.get("valid_result") == VALID_RESULT
            and mapping.get("contract_state")
            == "PHASE4_CLOSEOUT_EVIDENCE_ENABLED_PARSER_AND_FALLBACK_DISABLED"
            and mapping.get("stage_review_status") == "pending_next_run"
            and mapping.get("next_gate") == REVIEW_GATE
        ),
        "source_binding_live": _source_binding_valid(mapping.get("source_binding")),
        "phase3_commit_bound": _phase3_commit_bound(
            mapping.get("phase3_commit_binding")
        ),
        "upstream_bindings_indexed": _upstream_bindings_valid(
            mapping.get("upstream_bindings")
        ),
        "parser_output_samples_exact": mapping.get("parser_output_samples_contract")
        == EXPECTED_PARSER_SAMPLES,
        "fallback_log_contract_exact": mapping.get("fallback_log_contract")
        == EXPECTED_FALLBACK_LOG,
        "quality_metrics_contract_exact": mapping.get("quality_metrics_contract")
        == EXPECTED_QUALITY,
        "failure_classification_exact": mapping.get(
            "failure_classification_contract"
        )
        == EXPECTED_FAILURES,
        "support_boundary_exact": mapping.get("support_boundary")
        == EXPECTED_SUPPORT_BOUNDARY,
        "version_evidence_exact": mapping.get("version_evidence_contract")
        == EXPECTED_VERSION_EVIDENCE,
        "configuration_rollback_exact": mapping.get("configuration_rollback")
        == EXPECTED_ROLLBACK,
        "review_gate_exact": mapping.get("review_gate") == EXPECTED_REVIEW_GATE,
        "known_limits_exact": mapping.get("known_limits") == EXPECTED_LIMITS,
        "owner_feedback_exact": mapping.get("owner_feedback_contract")
        == EXPECTED_OWNER_FEEDBACK,
        "truth_flags_exact": mapping.get("truth_flags") == EXPECTED_TRUTH_FLAGS,
    }


def _blank_report(
    contract_checks: Optional[Mapping[str, bool]] = None,
    *,
    contract_valid: bool = False,
    delivery_checks_performed: bool = False,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": "STAGE-045",
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
        "non_high_quality_scenario_ids": [],
        "quality_metrics": {},
        "failure_classification": {},
        "support_boundary": {},
        "version_evidence": {},
        "configuration_rollback": {},
        "known_limits": [],
        "stage_review_status": "not_started",
        "next_gate": P4_GATE,
        "execution_ready": False,
        "owner_feedback_zh": "Stage045 步骤四合同无效，已失败关闭且未生成交付证据。",
        "result": "FAIL_CLOSED_INVALID_DELIVERY_CONTRACT",
        "valid": False,
    }
    report.update({name: False for name in EXPECTED_TRUTH_FLAGS})
    return report


def _parser_output_samples(contract: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    sample_contract = contract["parser_output_samples_contract"]
    return {
        route: {
            "sample_status": sample_contract["sample_status"],
            "route_candidate": route,
            "parser_version": sample_contract["parser_version_placeholder"],
            "output": copy.deepcopy(sample_contract["default_output"]),
            "content_fields_are_untrusted_evidence": sample_contract[
                "content_fields_are_untrusted_evidence"
            ],
            "parser_execution_performed": False,
        }
        for route in sample_contract["route_candidates"]
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
                "confidence": scenario["confidence"],
                "route_candidate": scenario["route_candidate"],
                "fallback_state": spec["fallback_state"],
                "quality_disposition": scenario["quality_disposition"],
                "error_codes": copy.deepcopy(scenario["errors"]),
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
    confidence_counts = Counter(item["confidence"] for item in values)
    disposition_counts = Counter(item["quality_disposition"] for item in values)
    non_high = [item for item in values if item["confidence"] != "HIGH"]
    explicit_dispositions = {
        "QUALITY_REVIEW_REQUIRED",
        "OWNER_REVIEW_REQUIRED",
        "EXPLICIT_ERROR_NO_FALLBACK",
    }
    observed_formats = {
        item["detected_type"]
        for item in values
        if item["detected_type"] in SUPPORTED_FORMATS
    }
    scenario_count = len(values)
    passed_count = sum(item["status"] == "PASS" for item in values)
    return {
        "scenario_count": scenario_count,
        "passed_scenario_count": passed_count,
        "scenario_pass_rate": passed_count / scenario_count if scenario_count else 0.0,
        "supported_format_expected_count": len(SUPPORTED_FORMATS),
        "supported_format_observed_count": len(observed_formats),
        "supported_format_coverage_ratio": len(observed_formats)
        / len(SUPPORTED_FORMATS),
        "confidence_counts": {
            name: confidence_counts.get(name, 0)
            for name in ("HIGH", "MEDIUM", "LOW", "UNKNOWN")
        },
        "quality_disposition_counts": {
            name: disposition_counts.get(name, 0)
            for name in (
                "PRIMARY_ROUTE_CANDIDATE_ONLY",
                "QUALITY_REVIEW_REQUIRED",
                "OWNER_REVIEW_REQUIRED",
                "EXPLICIT_ERROR_NO_FALLBACK",
            )
        },
        "non_high_quality_result_count": len(non_high),
        "explicitly_disposed_non_high_quality_count": sum(
            item["quality_disposition"] in explicit_dispositions for item in non_high
        ),
        "results_with_error_codes": sum(bool(item["errors"]) for item in values),
        "silent_drop_count": sum(
            not item["quality_disposition"] and not item["errors"] for item in values
        ),
        "parser_output_produced_count": sum(bool(item["output_refs"]) for item in values),
    }


def _failure_classification(
    contract: Mapping[str, Any], scenario_results: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    classifications = {}
    for name, spec in contract["failure_classification_contract"].items():
        scenario = scenario_results[spec["scenario_id"]]
        exact = (
            scenario["detection_state"] == spec["detection_state"]
            and scenario["errors"] == spec["error_codes"]
            and scenario["quality_disposition"] == spec["disposition"]
            and not scenario["parser_dispatch_performed"]
            and not scenario["parser_execution_performed"]
            and not scenario["fallback_execution_performed"]
        )
        classifications[name] = {
            "scenario_id": spec["scenario_id"],
            "detection_state": scenario["detection_state"],
            "error_codes": copy.deepcopy(scenario["errors"]),
            "disposition": scenario["quality_disposition"],
            "fallback_state": spec["fallback_state"],
            "fail_closed": exact,
        }
    return classifications


def _expected_metrics(contract: Mapping[str, Any]) -> dict[str, Any]:
    expected = contract["quality_metrics_contract"]
    return {
        "scenario_count": expected["required_scenario_count"],
        "passed_scenario_count": expected["required_passed_scenario_count"],
        "scenario_pass_rate": expected["required_scenario_pass_rate"],
        "supported_format_expected_count": expected["required_supported_format_count"],
        "supported_format_observed_count": expected["required_supported_format_count"],
        "supported_format_coverage_ratio": expected[
            "required_supported_format_coverage_ratio"
        ],
        "confidence_counts": expected["required_confidence_counts"],
        "quality_disposition_counts": expected[
            "required_quality_disposition_counts"
        ],
        "non_high_quality_result_count": expected[
            "required_non_high_quality_result_count"
        ],
        "explicitly_disposed_non_high_quality_count": expected[
            "required_explicitly_disposed_non_high_quality_count"
        ],
        "results_with_error_codes": expected["required_results_with_error_codes"],
        "silent_drop_count": expected["required_silent_drop_count"],
        "parser_output_produced_count": expected[
            "required_parser_output_produced_count"
        ],
    }


def build_stage045_phase4_delivery_report(
    contract: Any = None, *, contract_path: Path = CONTRACT_PATH
) -> dict[str, Any]:
    if contract is None:
        contract = load_delivery_contract(contract_path)
    checks = validate_delivery_contract(contract)
    contract_valid = bool(checks) and all(checks.values())
    if not contract_valid or not isinstance(contract, Mapping):
        return _blank_report(checks)

    try:
        phase3_module = _load_module(PHASE3_CHECKER_PATH, "stage045_phase3_for_p4")
        phase3_report = phase3_module.build_stage045_phase3_report()
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
        "ids_business_source_read_performed",
        "raw_metadata_content_accessed",
        "parser_dispatch_performed",
        "parser_execution_performed",
        "fallback_execution_performed",
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
        and phase3_report.get("silent_drop_count") == 0
        and isinstance(scenario_results, Mapping)
        and len(scenario_results) == 14
        and all(phase3_report.get(name) is False for name in false_effect_keys)
    )
    samples_valid = (
        set(parser_samples) == set(PARSER_ROUTES)
        and all(
            set(sample["output"]) == set(PARSER_OUTPUT_FIELDS)
            and sample["output"] == DEFAULT_OUTPUT
            and sample["sample_status"] == "SCHEMA_ONLY_NOT_EXECUTED"
            and sample["parser_version"] == "UNASSIGNED_STAGE046"
            and sample["parser_execution_performed"] is False
            for sample in parser_samples.values()
        )
    )
    log_scenario_ids = [item["scenario_id"] for item in fallback_logs]
    fallback_logs_valid = (
        len(fallback_logs) == 7
        and log_scenario_ids
        == [scenario_id for scenario_id, _, _ in FALLBACK_SAMPLE_SPECS]
        and all(set(item) == set(FALLBACK_LOG_FIELDS) for item in fallback_logs)
        and all(
            item["quality_disposition"] == spec[2]
            and item["fallback_state"] == spec[1]
            and item["attempted"] is False
            and item["attempt_count"] == 0
            and item["silent_drop"] is False
            and item["parser_switch_performed"] is False
            for item, spec in zip(fallback_logs, FALLBACK_SAMPLE_SPECS)
        )
    )
    metrics_valid = metrics == _expected_metrics(contract)
    failures_valid = failures == contract["failure_classification_contract"]
    truth_flags = contract["truth_flags"]
    no_effects = all(truth_flags[name] is False for name in FALSE_TRUTH_FLAGS)
    delivery_checks = {
        "phase3_scenarios_replayed_valid": phase3_valid,
        "parser_output_schema_samples_valid": samples_valid,
        "fallback_log_samples_valid": fallback_logs_valid,
        "quality_metrics_valid": metrics_valid,
        "failure_classification_valid": failures_valid,
        "support_boundary_valid": contract["support_boundary"]
        == EXPECTED_SUPPORT_BOUNDARY,
        "version_and_rollback_valid": (
            contract["version_evidence_contract"] == EXPECTED_VERSION_EVIDENCE
            and contract["configuration_rollback"] == EXPECTED_ROLLBACK
        ),
        "truth_flags_valid": truth_flags == EXPECTED_TRUTH_FLAGS,
        "no_runtime_or_external_effects": no_effects,
    }
    delivery_valid = all(delivery_checks.values())
    owner_feedback = " ".join(contract["owner_feedback_contract"].values())
    report: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": "STAGE-045",
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
        "non_high_quality_scenario_ids": log_scenario_ids,
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
    report = build_stage045_phase4_delivery_report()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
