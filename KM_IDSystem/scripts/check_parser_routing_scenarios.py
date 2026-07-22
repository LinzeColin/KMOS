#!/usr/bin/env python3
"""Validate STAGE-046 Phase 3 metadata-only parser-routing scenarios."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping
from zipfile import BadZipFile, ZipFile


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
CONTRACT_PATH = (
    ROOT
    / "docs"
    / "pursuing_goal"
    / "ids_v0_1"
    / "parser_routing"
    / "stage046_parser_routing_scenarios_contract.json"
)
PHASE2_CHECKER_PATH = ROOT / "scripts" / "check_parser_routing_runtime.py"

SCENARIO_CONTRACT_ID = "ids.parser_routing.v0_1.stage046.p3.scenarios"
ROUTER_VERSION = "ids.parser_router.v0_1.stage046.p2"
PASS_RESULT = "PASS_ISOLATED_PARSER_ROUTING_SCENARIOS_PARSER_DISABLED"
NEXT_GATE = "IDS-STAGE046-P4-GATE"
CANONICAL_CONTRACT_SHA256 = (
    "8dcb04dfce730ef038d7c12bd8e61f0308a8f98daeb716f3e31bef613df2d96b"
)

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

PHASE2_BINDING = {
    "commit": "18c45ee39522891abe4ef65ed609eb5482f2f148",
    "root_tree": "ae7b08d3bc0bab21c2523dfd9a5e756b7d6a840d",
    "kmids_tree": "0e549aaf1c476fa6d926c12ad444db66921164b5",
    "parent": "c82e4e928b167c718d462dc8cef3eed5b5dbb3ea",
    "required_ancestor_of_head": True,
}

PHASE2_ARTIFACTS = {
    "stage046_phase2_evidence": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/"
            "STAGE046_PHASE2_PARSER_ROUTING_SLICE.md"
        ),
        "sha256": (
            "1ec339b03296724fe6e68d4992fa92a1eedd7ced018673285ffb7a6eb27f1435"
        ),
    },
    "stage046_phase2_contract": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/parser_routing/"
            "stage046_parser_routing_runtime_contract.json"
        ),
        "sha256": (
            "d1772c08581d04a9b7932f1a74fcfe44877056973df559c2396fb69f9b1e3aab"
        ),
    },
    "stage046_phase2_checker": {
        "ref": "KM_IDSystem/scripts/check_parser_routing_runtime.py",
        "sha256": (
            "e65e2bd30527f42e25e0fde89b2f2dfc84550a36ab25aa0b57d2e9caa7629412"
        ),
    },
    "stage046_phase2_tests": {
        "ref": (
            "KM_IDSystem/docs/pursuing_goal/ids_v0_1/tests/"
            "test_stage046_parser_routing_runtime.py"
        ),
        "sha256": (
            "021940f65fdbf5f976e9b3e9ebad84f74abc666d481a41175f306ef1f75fdf9b"
        ),
    },
    "stage046_phase2_run": {
        "ref": "KM_IDSystem/machine/runs/2026-07-20-stage046-p2-local.json",
        "sha256": (
            "322a593202657673a92701d8498f5a62a3854b2d9ff96697cb20afcc3527b8aa"
        ),
    },
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

SCENARIO_SPECS = {
    "pdf_high_candidate_parser_unavailable": (
        "PDF", "TYPE_CONFIRMED", "HIGH", False
    ),
    "docx_high_candidate_parser_unavailable": (
        "DOCX", "TYPE_CONFIRMED", "HIGH", False
    ),
    "xlsx_high_candidate_parser_unavailable": (
        "XLSX", "TYPE_CONFIRMED", "HIGH", False
    ),
    "csv_medium_quality_review": (
        "CSV", "TYPE_PROVISIONAL", "MEDIUM", False
    ),
    "txt_medium_quality_review": (
        "TXT", "TYPE_PROVISIONAL", "MEDIUM", False
    ),
    "png_high_candidate_parser_unavailable": (
        "PNG", "TYPE_CONFIRMED", "HIGH", False
    ),
    "jpeg_high_candidate_parser_unavailable": (
        "JPEG", "TYPE_CONFIRMED", "HIGH", False
    ),
    "tiff_high_candidate_parser_unavailable": (
        "TIFF", "TYPE_CONFIRMED", "HIGH", False
    ),
    "unknown_requires_owner_review": (
        "UNKNOWN", "TYPE_UNKNOWN_REVIEW_REQUIRED", "UNKNOWN", False
    ),
    "corrupt_input_blocks_explicitly": (
        "CORRUPT_OR_UNREADABLE", "TYPE_INPUT_BLOCKED", "UNKNOWN", False
    ),
    "conflict_requires_owner_review": (
        "UNKNOWN", "TYPE_CONFLICT_REVIEW_REQUIRED", "UNKNOWN", False
    ),
    "extension_only_low_requires_owner_review": (
        "PDF", "TYPE_PROVISIONAL", "LOW", False
    ),
    "unsupported_format_is_explicit": (
        "UNSUPPORTED", "TYPE_UNSUPPORTED", "UNKNOWN", False
    ),
    "instruction_like_text_cannot_override_policy": (
        "TXT", "TYPE_PROVISIONAL", "MEDIUM", True
    ),
}

EXPECTED_OUTCOMES = {
    "pdf_high_candidate_parser_unavailable": (
        "PDF", "TYPE_CONFIRMED", "HIGH",
        "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE", "ROUTE_PDF",
        "PDF_PARSER", "PRIMARY_ROUTE_CANDIDATE_PARSER_UNAVAILABLE",
    ),
    "docx_high_candidate_parser_unavailable": (
        "DOCX", "TYPE_CONFIRMED", "HIGH",
        "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE", "ROUTE_OOXML_WORD",
        "OOXML_WORD_PARSER", "PRIMARY_ROUTE_CANDIDATE_PARSER_UNAVAILABLE",
    ),
    "xlsx_high_candidate_parser_unavailable": (
        "XLSX", "TYPE_CONFIRMED", "HIGH",
        "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE",
        "ROUTE_OOXML_WORKBOOK", "OOXML_WORKBOOK_PARSER",
        "PRIMARY_ROUTE_CANDIDATE_PARSER_UNAVAILABLE",
    ),
    "csv_medium_quality_review": (
        "CSV", "TYPE_PROVISIONAL", "MEDIUM", "ROUTE_REVIEW_REQUIRED",
        None, None, "QUALITY_REVIEW_REQUIRED",
    ),
    "txt_medium_quality_review": (
        "TXT", "TYPE_PROVISIONAL", "MEDIUM", "ROUTE_REVIEW_REQUIRED",
        None, None, "QUALITY_REVIEW_REQUIRED",
    ),
    "png_high_candidate_parser_unavailable": (
        "PNG", "TYPE_CONFIRMED", "HIGH",
        "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE", "ROUTE_IMAGE",
        "IMAGE_PARSER", "PRIMARY_ROUTE_CANDIDATE_PARSER_UNAVAILABLE",
    ),
    "jpeg_high_candidate_parser_unavailable": (
        "JPEG", "TYPE_CONFIRMED", "HIGH",
        "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE", "ROUTE_IMAGE",
        "IMAGE_PARSER", "PRIMARY_ROUTE_CANDIDATE_PARSER_UNAVAILABLE",
    ),
    "tiff_high_candidate_parser_unavailable": (
        "TIFF", "TYPE_CONFIRMED", "HIGH",
        "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE", "ROUTE_IMAGE",
        "IMAGE_PARSER", "PRIMARY_ROUTE_CANDIDATE_PARSER_UNAVAILABLE",
    ),
    "unknown_requires_owner_review": (
        "UNKNOWN", "TYPE_UNKNOWN_REVIEW_REQUIRED", "UNKNOWN",
        "ROUTE_REVIEW_REQUIRED", None, None, "OWNER_REVIEW_REQUIRED",
    ),
    "corrupt_input_blocks_explicitly": (
        "CORRUPT_OR_UNREADABLE", "TYPE_INPUT_BLOCKED", "UNKNOWN",
        "ROUTE_BLOCKED", None, None, "EXPLICIT_ERROR_NO_FALLBACK",
    ),
    "conflict_requires_owner_review": (
        "UNKNOWN", "TYPE_CONFLICT_REVIEW_REQUIRED", "UNKNOWN",
        "ROUTE_REVIEW_REQUIRED", None, None, "OWNER_REVIEW_REQUIRED",
    ),
    "extension_only_low_requires_owner_review": (
        "PDF", "TYPE_PROVISIONAL", "LOW", "ROUTE_REVIEW_REQUIRED",
        None, None, "OWNER_REVIEW_REQUIRED",
    ),
    "unsupported_format_is_explicit": (
        "UNSUPPORTED", "TYPE_UNSUPPORTED", "UNKNOWN", "ROUTE_UNSUPPORTED",
        None, None, "UNSUPPORTED_EXPLICIT_NO_FALLBACK",
    ),
    "instruction_like_text_cannot_override_policy": (
        "TXT", "TYPE_PROVISIONAL", "MEDIUM", "ROUTE_REVIEW_REQUIRED",
        None, None, "QUALITY_REVIEW_REQUIRED",
    ),
}

RESULT_INVARIANTS_BY_ACTION = {
    "ROUTE_BLOCKED_PARSER_IMPLEMENTATION_UNAVAILABLE": {
        "errors": ["PARSER_IMPLEMENTATION_UNAVAILABLE"],
        "route_fact_level": "CANDIDATE",
        "route_candidate_selected": True,
        "dispatch_block_reason": "PARSER_IMPLEMENTATION_UNAVAILABLE",
    },
    "ROUTE_REVIEW_REQUIRED": {
        "errors": ["DETECTION_REVIEW_REQUIRED"],
        "route_fact_level": "REVIEW_REQUIRED",
        "route_candidate_selected": False,
        "dispatch_block_reason": "NOT_APPLICABLE",
    },
    "ROUTE_UNSUPPORTED": {
        "errors": ["FILE_TYPE_UNSUPPORTED"],
        "route_fact_level": "UNSUPPORTED",
        "route_candidate_selected": False,
        "dispatch_block_reason": "NOT_APPLICABLE",
    },
    "ROUTE_BLOCKED": {
        "errors": ["DETECTION_INPUT_BLOCKED"],
        "route_fact_level": "BLOCKED",
        "route_candidate_selected": False,
        "dispatch_block_reason": "NOT_APPLICABLE",
    },
}

GOVERNED_ROUTES = {
    "PDF": "ROUTE_PDF",
    "DOCX": "ROUTE_OOXML_WORD",
    "XLSX": "ROUTE_OOXML_WORKBOOK",
    "CSV": "ROUTE_DELIMITED_TEXT",
    "TXT": "ROUTE_PLAIN_TEXT",
    "PNG": "ROUTE_IMAGE",
    "JPEG": "ROUTE_IMAGE",
    "TIFF": "ROUTE_IMAGE",
}

ROOT_KEYS = {
    "schema_version", "stage", "phase", "task_id", "acceptance_id",
    "execution_mode", "scenario_contract_id", "router_version",
    "contract_state", "next_gate", "source_binding",
    "phase2_commit_binding", "phase2_artifact_bindings",
    "scenario_catalog", "format_coverage", "scenario_expectations",
    "fallback_quality_contract", "instruction_text_contract",
    "result_contract", "phase4_entry_gate", "rollback_contract",
    "truth_flags",
}


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _source_live() -> bool:
    try:
        archive_path = Path(SOURCE_BINDING["source_archive_path"])
        roadmap_path = Path(SOURCE_BINDING["roadmap_path"])
        instructions_path = Path(SOURCE_BINDING["instructions_path"])
        if (
            not archive_path.is_file()
            or _sha256(archive_path) != SOURCE_BINDING["source_archive_sha256"]
            or _sha256(roadmap_path) != SOURCE_BINDING["roadmap_sha256"]
            or _sha256(instructions_path)
            != SOURCE_BINDING["instructions_sha256"]
        ):
            return False
        with ZipFile(archive_path) as archive:
            matches = [
                name
                for name in archive.namelist()
                if name == SOURCE_BINDING["source_member"]
            ]
            if len(matches) != SOURCE_BINDING["source_member_match_count"]:
                return False
            member_sha = hashlib.sha256(archive.read(matches[0])).hexdigest()
        return member_sha == SOURCE_BINDING["source_member_sha256"]
    except (OSError, KeyError, TypeError, ValueError, BadZipFile):
        return False


def _phase2_commit_live() -> bool:
    commit = PHASE2_BINDING["commit"]
    try:
        observed = subprocess.check_output(
            ["git", "show", "-s", "--format=%H%n%T%n%P", commit],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).splitlines()
        kmids_tree = subprocess.check_output(
            ["git", "rev-parse", f"{commit}:KM_IDSystem"],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=REPO_ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    except (OSError, subprocess.CalledProcessError):
        return False
    return (
        observed
        == [
            commit,
            PHASE2_BINDING["root_tree"],
            PHASE2_BINDING["parent"],
        ]
        and kmids_tree == PHASE2_BINDING["kmids_tree"]
        and PHASE2_BINDING["required_ancestor_of_head"] is True
        and ancestor
    )


def _phase2_artifacts_live() -> bool:
    try:
        return all(
            (REPO_ROOT / item["ref"]).is_file()
            and _sha256(REPO_ROOT / item["ref"]) == item["sha256"]
            for item in PHASE2_ARTIFACTS.values()
        )
    except (OSError, KeyError, TypeError):
        return False


def validate_scenario_contract(contract: Any) -> dict[str, bool]:
    """Fail closed unless the complete P3 contract and frozen P2 inputs match."""
    value: Mapping[str, Any] = contract if isinstance(contract, Mapping) else {}
    fallback = value.get("fallback_quality_contract", {})
    instruction = value.get("instruction_text_contract", {})
    result_contract = value.get("result_contract", {})
    truth = value.get("truth_flags", {})
    checks = {
        "root_exact_shape": (
            isinstance(contract, Mapping) and set(value) == ROOT_KEYS
        ),
        "canonical_contract_identity": (
            _canonical_sha256(value) == CANONICAL_CONTRACT_SHA256
        ),
        "identity_exact": (
            value.get("schema_version")
            == "ids.stage046.parser_routing.phase3.scenarios.v1"
            and value.get("stage") == "STAGE-046"
            and value.get("phase") == "Phase 3"
            and value.get("task_id") == "IDS-V0_1-STAGE046-P3"
            and value.get("acceptance_id") == "ACC-STAGE-046"
            and value.get("execution_mode")
            == "ISOLATED_NON_PRODUCTION_METADATA_ONLY_PARSER_ROUTING_SCENARIOS"
            and value.get("scenario_contract_id") == SCENARIO_CONTRACT_ID
            and value.get("router_version") == ROUTER_VERSION
            and value.get("contract_state")
            == "PHASE3_SCENARIOS_ENABLED_PARSER_FALLBACK_AND_OUTPUT_DISABLED"
            and value.get("next_gate") == NEXT_GATE
        ),
        "source_binding_exact": value.get("source_binding") == SOURCE_BINDING,
        "source_live": _source_live(),
        "phase2_commit_bound": (
            value.get("phase2_commit_binding") == PHASE2_BINDING
            and _phase2_commit_live()
        ),
        "phase2_artifacts_exact": (
            value.get("phase2_artifact_bindings") == PHASE2_ARTIFACTS
        ),
        "phase2_artifacts_live": _phase2_artifacts_live(),
        "scenario_catalog_exact": value.get("scenario_catalog") == SCENARIOS,
        "scenario_expectations_complete": (
            isinstance(value.get("scenario_expectations"), Mapping)
            and set(value["scenario_expectations"]) == set(SCENARIOS)
        ),
        "fallback_quality_fail_closed": (
            isinstance(fallback, Mapping)
            and fallback.get("every_scenario_requires_explicit_disposition")
            is True
            and fallback.get(
                "all_non_high_quality_results_require_review_or_error"
            )
            is True
            and fallback.get("silent_drop_allowed_count") == 0
            and fallback.get("parser_dispatch_allowed") is False
            and fallback.get("parser_execution_allowed") is False
            and fallback.get("fallback_execution_allowed") is False
            and fallback.get("fallback_log_claim_allowed") is False
            and fallback.get("fallback_runtime_owner") == "STAGE-048"
        ),
        "instruction_text_fail_closed": (
            isinstance(instruction, Mapping)
            and instruction.get("required_label")
            == "UNTRUSTED_EVIDENCE_TEXT"
            and instruction.get("required_interpretation") == "EVIDENCE_ONLY"
            and instruction.get("route_must_match_non_instruction_baseline")
            is True
            and instruction.get("system_rule_override_allowed") is False
            and instruction.get("tool_authorization_allowed") is False
            and instruction.get("policy_override_allowed") is False
            and instruction.get("prompt_injection_scan_allowed") is False
            and instruction.get("scanner_runtime_owner") == "STAGE-050"
        ),
        "critical_result_invariants_exact": (
            isinstance(result_contract, Mapping)
            and result_contract.get("detection_result_identity_required") is True
            and result_contract.get("exact_invariants_by_route_action")
            == RESULT_INVARIANTS_BY_ACTION
            and result_contract.get("parser_version_required")
            == "UNASSIGNED_NOT_IMPLEMENTED"
            and result_contract.get("critical_result_invariants_participate_in_pass")
            is True
        ),
        "truth_flags_fail_closed": (
            isinstance(truth, Mapping)
            and truth.get("isolated_metadata_only_routing_scenarios_performed")
            is True
            and truth.get("parser_dispatch_performed") is False
            and truth.get("parser_execution_performed") is False
            and truth.get("fallback_execution_performed") is False
            and truth.get("prompt_injection_scan_performed") is False
            and truth.get("parser_output_produced") is False
            and truth.get("persistent_state_write_performed") is False
            and truth.get("whole_stage_review_performed") is False
            and truth.get("batch_review_performed") is False
            and truth.get("github_upload_allowed") is False
            and truth.get("app_reinstall_allowed") is False
        ),
    }
    return checks


def _routing_request(
    phase2: Any,
    *,
    index: int,
    detected_type: str,
    state: str,
    confidence: str,
    marker: bool,
) -> dict[str, Any]:
    token = f"{index:x}"
    return phase2.build_routing_request(
        detection_request_id="detection:sha256:" + token * 64,
        source_fingerprint_ref="fingerprint:sha256:" + token * 64,
        source_identity_ref=f"source:stage046:p3:{index:02d}",
        detected_type=detected_type,
        detection_state=state,
        detection_confidence=confidence,
        detection_evidence_ref=f"evidence:stage045:stage046:p3:{index:02d}",
        evidence_text_marker_applied=marker,
        requested_at="2026-07-22T00:00:00Z",
    )


def _route_outcome(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "detected_type": result.get("detected_type"),
        "detection_state": result.get("detection_state"),
        "detection_confidence": result.get("detection_confidence"),
        "route_action": result.get("route_action"),
        "candidate_route_id": result.get("candidate_route_id"),
        "parser_family": result.get("parser_family"),
    }


def _quality_disposition(result: Mapping[str, Any]) -> str:
    key = (
        f"{result.get('detection_state')}:"
        f"{result.get('detection_confidence')}"
    )
    mapping = {
        "TYPE_CONFIRMED:HIGH": (
            "PRIMARY_ROUTE_CANDIDATE_PARSER_UNAVAILABLE"
        ),
        "TYPE_PROVISIONAL:MEDIUM": "QUALITY_REVIEW_REQUIRED",
        "TYPE_PROVISIONAL:LOW": "OWNER_REVIEW_REQUIRED",
        "TYPE_CONFLICT_REVIEW_REQUIRED:UNKNOWN": "OWNER_REVIEW_REQUIRED",
        "TYPE_UNKNOWN_REVIEW_REQUIRED:UNKNOWN": "OWNER_REVIEW_REQUIRED",
        "TYPE_INPUT_BLOCKED:UNKNOWN": "EXPLICIT_ERROR_NO_FALLBACK",
        "TYPE_UNSUPPORTED:UNKNOWN": "UNSUPPORTED_EXPLICIT_NO_FALLBACK",
    }
    return mapping.get(key, "INVALID_RESULT_FAIL_CLOSED")


def _outcome_tuple(result: Mapping[str, Any], disposition: str) -> tuple[Any, ...]:
    return (
        result.get("detected_type"),
        result.get("detection_state"),
        result.get("detection_confidence"),
        result.get("route_action"),
        result.get("candidate_route_id"),
        result.get("parser_family"),
        disposition,
    )


def _summarize(
    name: str,
    result: Mapping[str, Any],
    *,
    route_matches_baseline: bool | None = None,
) -> dict[str, Any]:
    disposition = _quality_disposition(result)
    route_action = result.get("route_action")
    expected_invariants = RESULT_INVARIANTS_BY_ACTION.get(route_action, {})
    detection_result_id = result.get("detection_result_id")
    identity_valid = (
        isinstance(detection_result_id, str)
        and detection_result_id.startswith("detection-result:sha256:")
        and len(detection_result_id) == len("detection-result:sha256:") + 64
        and all(
            character in "0123456789abcdef"
            for character in detection_result_id.removeprefix(
                "detection-result:sha256:"
            )
        )
        and result.get("detection_result_identity_status")
        == "PROJECTION_DIGEST_VERIFIED"
    )
    result_invariants_exact = (
        bool(expected_invariants)
        and all(result.get(key) == expected for key, expected in expected_invariants.items())
        and result.get("parser_version") == "UNASSIGNED_NOT_IMPLEMENTED"
        and result.get("parser_version_status") == "RECORDED_UNASSIGNED"
        and identity_valid
    )
    forbidden_effects_absent = (
        all(
            result.get(field) is False
            for field in (
                "parser_dispatch_performed",
                "parser_execution_performed",
                "fallback_execution_performed",
                "prompt_injection_scan_performed",
                "parser_output_produced",
                "high_confidence_evidence_write_performed",
                "source_file_open_performed",
                "file_type_redetection_performed",
                "persistent_state_write_performed",
                "production_runtime_activation_performed",
            )
        )
        and result.get("persisted") is False
        and result.get("output_refs") == []
        and result.get("system_instruction_allowed") is False
        and result.get("tool_authorization_allowed") is False
        and result.get("policy_override_allowed") is False
    )
    expected = EXPECTED_OUTCOMES[name]
    passed = (
        _outcome_tuple(result, disposition) == expected
        and forbidden_effects_absent
        and route_matches_baseline is not False
        and result_invariants_exact
    )
    detected_type = result.get("detected_type")
    return {
        "status": "PASS" if passed else "FAIL_CLOSED",
        "router_version": result.get("router_version"),
        "detected_type": detected_type,
        "detection_state": result.get("detection_state"),
        "detection_confidence": result.get("detection_confidence"),
        "route_action": result.get("route_action"),
        "governed_route_id": GOVERNED_ROUTES.get(detected_type),
        "candidate_route_id": result.get("candidate_route_id"),
        "parser_family": result.get("parser_family"),
        "parser_version": result.get("parser_version"),
        "parser_version_status": result.get("parser_version_status"),
        "detection_result_id": detection_result_id,
        "detection_result_identity_status": result.get(
            "detection_result_identity_status"
        ),
        "route_fact_level": result.get("route_fact_level"),
        "route_candidate_selected": result.get("route_candidate_selected"),
        "result_invariants_exact": result_invariants_exact,
        "quality_disposition": disposition,
        "explicit_disposition": disposition != "INVALID_RESULT_FAIL_CLOSED",
        "silent_drop": disposition == "INVALID_RESULT_FAIL_CLOSED",
        "errors": result.get("errors"),
        "evidence_text_label": result.get("evidence_text_label"),
        "evidence_text_interpretation": result.get(
            "evidence_text_interpretation"
        ),
        "route_outcome": _route_outcome(result),
        "route_matches_non_instruction_baseline": route_matches_baseline,
        "system_rule_override_performed": (
            result.get("system_instruction_allowed") is not False
            or result.get("policy_override_allowed") is not False
        ),
        "tool_authorization_performed": (
            result.get("tool_authorization_allowed") is not False
        ),
        "prompt_injection_scan_performed": result.get(
            "prompt_injection_scan_performed"
        ),
        "output_refs": result.get("output_refs"),
        "parser_dispatch_performed": result.get("parser_dispatch_performed"),
        "parser_execution_performed": result.get("parser_execution_performed"),
        "fallback_execution_performed": result.get(
            "fallback_execution_performed"
        ),
    }


def _invalid_request_proof(
    phase2: Any,
    valid_request: Mapping[str, Any],
) -> dict[str, Any]:
    extra_override = copy.deepcopy(dict(valid_request))
    extra_override["requested_parser"] = "CALLER_FORGED_PARSER"
    forged_id = copy.deepcopy(dict(valid_request))
    forged_id["routing_request_id"] = "routing:sha256:" + "0" * 64
    extra_result = phase2.evaluate_parser_route(extra_override)
    forged_result = phase2.evaluate_parser_route(forged_id)
    extra_rejected = extra_result.get("errors") == ["INVALID_ROUTING_REQUEST"]
    forged_rejected = forged_result.get("errors") == ["INVALID_ROUTING_REQUEST"]
    return {
        "extra_parser_override_rejected": extra_rejected,
        "forged_routing_id_rejected": forged_rejected,
        "rejected_request_count": sum((extra_rejected, forged_rejected)),
        "parser_dispatch_performed": any(
            item.get("parser_dispatch_performed") is True
            for item in (extra_result, forged_result)
        ),
    }


def build_stage046_phase3_report() -> dict[str, Any]:
    try:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        contract = {}
    contract_checks = validate_scenario_contract(contract)

    phase2_valid = False
    scenario_results: dict[str, dict[str, Any]] = {}
    instruction_baseline: dict[str, Any] = {}
    invalid_proof = {
        "extra_parser_override_rejected": False,
        "forged_routing_id_rejected": False,
        "rejected_request_count": 0,
        "parser_dispatch_performed": False,
    }
    try:
        phase2 = _load_module(PHASE2_CHECKER_PATH, "stage046_phase2_router")
        phase2_report = phase2.build_stage046_phase2_report()
        phase2_valid = phase2_report.get("valid") is True
        requests = {}
        raw_results = {}
        for index, name in enumerate(SCENARIOS, start=1):
            detected_type, state, confidence, marker = SCENARIO_SPECS[name]
            request = _routing_request(
                phase2,
                index=index,
                detected_type=detected_type,
                state=state,
                confidence=confidence,
                marker=marker,
            )
            requests[name] = request
            raw_results[name] = phase2.evaluate_parser_route(request)

        instruction_name = "instruction_like_text_cannot_override_policy"
        detected_type, state, confidence, _marker = SCENARIO_SPECS[
            instruction_name
        ]
        baseline_request = _routing_request(
            phase2,
            index=len(SCENARIOS),
            detected_type=detected_type,
            state=state,
            confidence=confidence,
            marker=False,
        )
        baseline_result = phase2.evaluate_parser_route(baseline_request)
        instruction_outcome = _route_outcome(raw_results[instruction_name])
        baseline_outcome = _route_outcome(baseline_result)
        route_matches_baseline = instruction_outcome == baseline_outcome
        instruction_baseline = {"route_outcome": baseline_outcome}

        scenario_results = {
            name: _summarize(
                name,
                result,
                route_matches_baseline=(
                    route_matches_baseline if name == instruction_name else None
                ),
            )
            for name, result in raw_results.items()
        }
        invalid_proof = _invalid_request_proof(
            phase2,
            requests[SCENARIOS[0]],
        )
    except (OSError, RuntimeError, TypeError, ValueError, KeyError):
        phase2_valid = False

    scenario_checks = {
        name: item.get("status") == "PASS"
        for name, item in scenario_results.items()
    }
    passed_count = sum(scenario_checks.values())
    explicit_count = sum(
        item.get("explicit_disposition") is True
        for item in scenario_results.values()
    )
    silent_drop_count = sum(
        item.get("silent_drop") is True
        for item in scenario_results.values()
    )
    invalid_proof_valid = (
        invalid_proof["extra_parser_override_rejected"] is True
        and invalid_proof["forged_routing_id_rejected"] is True
        and invalid_proof["rejected_request_count"] == 2
        and invalid_proof["parser_dispatch_performed"] is False
    )
    valid = (
        bool(contract_checks)
        and all(contract_checks.values())
        and phase2_valid
        and list(scenario_results) == SCENARIOS
        and len(scenario_results) == 14
        and all(scenario_checks.values())
        and explicit_count == 14
        and silent_drop_count == 0
        and invalid_proof_valid
    )
    return {
        "schema_version": "ids.stage046.parser_routing.phase3.report.v1",
        "stage": "STAGE-046",
        "phase": "Phase 3",
        "task_id": "IDS-V0_1-STAGE046-P3",
        "acceptance_id": "ACC-STAGE-046",
        "execution_mode": (
            "ISOLATED_NON_PRODUCTION_METADATA_ONLY_PARSER_ROUTING_SCENARIOS"
        ),
        "valid": valid,
        "result": PASS_RESULT if valid else "FAIL_CLOSED",
        "contract_checks": contract_checks,
        "phase2_router_valid": phase2_valid,
        "scenario_checks": scenario_checks,
        "scenario_count": len(scenario_results),
        "passed_scenario_count": passed_count,
        "explicit_disposition_count": explicit_count,
        "silent_drop_count": silent_drop_count,
        "scenario_results": scenario_results,
        "instruction_baseline": instruction_baseline,
        "phase2_invalid_request_rejection_proof": invalid_proof,
        "next_gate": NEXT_GATE if valid else "IDS-STAGE046-P3-GATE",
        "source_file_open_performed": False,
        "filesystem_scan_performed": False,
        "file_hash_performed": False,
        "file_type_redetection_performed": False,
        "ids_business_source_read_performed": False,
        "raw_metadata_content_accessed": False,
        "parser_dispatch_performed": False,
        "parser_execution_performed": False,
        "fallback_execution_performed": False,
        "differential_parser_evaluation_performed": False,
        "prompt_injection_scan_performed": False,
        "parser_output_produced": False,
        "high_confidence_evidence_write_performed": False,
        "persistent_state_write_performed": False,
        "database_connection_performed": False,
        "runtime_output_written": False,
        "production_runtime_activation_performed": False,
        "whole_stage_review_performed": False,
        "batch_review_performed": False,
        "github_upload_allowed": False,
        "app_reinstall_allowed": False,
    }


def main() -> int:
    report = build_stage046_phase3_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
