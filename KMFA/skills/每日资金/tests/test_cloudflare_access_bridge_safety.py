"""Safety contracts for the one-shot Cloudflare Access history-probe bridge."""

from __future__ import annotations

import importlib.util
import json
import stat
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from daily_funds.access_bridge import (  # noqa: E402
    ACCESS_BRIDGE_SCHEMA,
    AccessBridgeInputError,
    PROJECTION_PATH,
    PROBE_PATH,
    RECOVERY_PATH,
    capture_policy,
    capture_service_token,
    control_application_payload,
    control_application_policy_state,
    diagnose_orphaned_bridge_resources,
    diagnose_bridge_target,
    orphaned_bridge_run_tag,
    orphaned_bridge_resource_ids,
    owned_bridge_resource_ids,
    policy_payload,
    projection_poll_state,
    probe_poll_state,
    probe_start_poll_state,
    recovery_poll_state,
    recovery_start_poll_state,
    resolve_bridge_target,
    service_token_payload,
    summarize_recovery_start_response,
    summarize_recovery_response,
    summarize_projection_response,
    summarize_probe_start_response,
    summarize_probe_response,
)


APP_ID = "2d7ac813-4f60-4d2f-9c69-8d5294e4c7fe"
SERVICE_TOKEN_ID = "20b0c6f3-77f1-4591-8f4a-d643709b42cf"
POLICY_ID = "a2b3c4d5-1e2f-4a5b-8c9d-0e1f2a3b4c5d"
AUDIENCE = "a" * 64


def _write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _probe_headers(path: Path, *, origin_marker: bool = True) -> Path:
    marker = b"X-KMFA-Daily-Funds-Probe: v1\r\n" if origin_marker else b""
    path.write_bytes(b"HTTP/2 200\r\n" + marker + b"Cache-Control: private, no-store\r\n\r\n")
    return path


def _recovery_headers(path: Path, *, origin_marker: bool = True) -> Path:
    marker = b"X-KMFA-Daily-Funds-Recovery: v1\r\n" if origin_marker else b""
    path.write_bytes(b"HTTP/2 200\r\n" + marker + b"Cache-Control: private, no-store\r\n\r\n")
    return path


def _projection_headers(path: Path, *, origin_marker: bool = True) -> Path:
    marker = b"X-KMFA-Daily-Funds-Projection-Probe: v1\r\n" if origin_marker else b""
    path.write_bytes(b"HTTP/2 200\r\n" + marker + b"Cache-Control: private, no-store\r\n\r\n")
    return path


def _target_inputs(tmp_path: Path, *, apps: list[object] | None = None) -> Path:
    access_apps = tmp_path / "apps.json"
    _write(access_apps, {
        "success": True,
        "result_info": {"total_pages": 1},
        "result": apps if apps is not None else [{
            "id": APP_ID,
            "aud": AUDIENCE,
            "type": "self_hosted",
            "domain": f"kmfa.linzezhang.com{PROBE_PATH}",
        }],
    })
    return access_apps


def _valid_probe(
    *,
    state: str = "COMPLETED",
    continuation: str = "SECOND_PAGE_TERMINAL",
    record_list_shape: str = "NOT_OBSERVED",
) -> dict[str, object]:
    cursor = {
        "NOT_STARTED": "NOT_STARTED",
        "FIRST_PAGE_TERMINAL": "FIRST_PAGE_TERMINAL",
        "SECOND_PAGE_TERMINAL": "OPAQUE_CURSOR_REUSED_SECOND_PAGE_TERMINAL",
        "SECOND_PAGE_CONTINUES": "OPAQUE_CURSOR_REUSED_SECOND_PAGE_CONTINUES",
        "GROUP_HISTORY_FALLBACK_FIRST_PAGE_TERMINAL": "GROUP_HISTORY_FALLBACK_FIRST_PAGE_TERMINAL",
        "GROUP_HISTORY_FALLBACK_SECOND_PAGE_TERMINAL": "GROUP_HISTORY_FALLBACK_OPAQUE_CURSOR_REUSED_SECOND_PAGE_TERMINAL",
        "GROUP_HISTORY_FALLBACK_SECOND_PAGE_CONTINUES": "GROUP_HISTORY_FALLBACK_OPAQUE_CURSOR_REUSED_SECOND_PAGE_CONTINUES",
        "GROUP_HISTORY_V2_FIRST_PAGE_TERMINAL": "GROUP_HISTORY_V2_FIRST_PAGE_TERMINAL",
        "GROUP_HISTORY_V2_SECOND_PAGE_TERMINAL": "GROUP_HISTORY_V2_PROVIDER_MILLISECOND_CURSOR_REUSED_SECOND_PAGE_TERMINAL",
        "GROUP_HISTORY_V2_SECOND_PAGE_CONTINUES": "GROUP_HISTORY_V2_PROVIDER_MILLISECOND_CURSOR_REUSED_SECOND_PAGE_CONTINUES",
    }[continuation]
    machine = (
        "DWS_GROUP_HISTORY_PROBE_COMPLETED"
        if state == "COMPLETED" and continuation.startswith("GROUP_HISTORY_V2_")
        else "DWS_HISTORY_PROBE_COMPLETED" if state == "COMPLETED" else "DWS_HISTORY_PROBE_RUNNING"
    )
    return {
        "state": state,
        "machine_code": machine,
        "updated_at": "2026-08-09T00:00:00Z",
        "expires_at": "2026-08-09T00:10:00Z",
        "continuation_state": continuation,
        "cursor_transcript": cursor,
        "record_list_shape": record_list_shape,
    }


def _valid_projection(*, oci_backup: str = "OK") -> dict[str, str]:
    return {
        "schema_version": "kmfa.daily_funds.projection_probe.v1",
        "state": "PUBLISHED",
        "d1_projection": "VERIFIED",
        "r2_mirror": "VERIFIED",
        "oci_backup": oci_backup,
        "readonly_projection": "VERIFIED",
    }


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "cloudflare_access_bridge_manager_test",
        ROOT / "scripts" / "manage_cloudflare_access_bridge.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_bridge_resolves_only_one_exact_control_child_application(tmp_path: Path) -> None:
    access_apps = _target_inputs(tmp_path)

    assert resolve_bridge_target(access_apps, PROBE_PATH) == {
        "app_id": APP_ID,
        "origin": "https://kmfa.linzezhang.com",
    }


@pytest.mark.parametrize("domain", [
    "kmfa.linzezhang.com/*",
    "kmfa.linzezhang.com/ops/*",
    "kmfa.linzezhang.com/ops/api/daily-funds/*",
    "kmfa.linzezhang.com/",
    "http://kmfa.linzezhang.com/ops/api/daily-funds/history-probe",
    "localhost/ops/api/daily-funds/history-probe",
])
def test_bridge_rejects_broad_or_non_https_access_targets(tmp_path: Path, domain: str) -> None:
    access_apps = _target_inputs(tmp_path, apps=[{
        "id": APP_ID,
        "aud": AUDIENCE,
        "type": "self_hosted",
        "domain": domain,
    }])

    with pytest.raises(AccessBridgeInputError):
        resolve_bridge_target(access_apps, PROBE_PATH)


def test_bridge_rejects_ambiguous_or_paginated_access_application_list(tmp_path: Path) -> None:
    duplicate = {
        "id": "b3b4c5d6-1e2f-4a5b-8c9d-0e1f2a3b4c5d",
        "aud": AUDIENCE,
        "type": "self_hosted",
        "domain": f"kmfa.linzezhang.com{PROBE_PATH}",
    }
    access_apps = _target_inputs(tmp_path, apps=[{
        "id": APP_ID,
        "aud": AUDIENCE,
        "type": "self_hosted",
        "domain": f"kmfa.linzezhang.com{PROBE_PATH}",
    }, duplicate])
    with pytest.raises(AccessBridgeInputError):
        resolve_bridge_target(access_apps, PROBE_PATH)

    payload = json.loads(access_apps.read_text(encoding="utf-8"))
    payload["result"] = [payload["result"][0]]
    payload["result_info"] = {"total_pages": 2}
    _write(access_apps, payload)
    with pytest.raises(AccessBridgeInputError):
        resolve_bridge_target(access_apps, PROBE_PATH)


def test_bridge_target_diagnostic_is_finite_and_values_free(tmp_path: Path) -> None:
    access_apps = _target_inputs(tmp_path)
    assert diagnose_bridge_target(access_apps, PROBE_PATH) == "RESOLVED"

    access_apps = _target_inputs(tmp_path)
    _write(access_apps, {"success": True, "result_info": {"total_pages": 2}, "result": []})
    assert diagnose_bridge_target(access_apps, PROBE_PATH) == "ACCESS_APP_LIST_INCOMPLETE"

    _write(access_apps, {"success": True, "result": [{
        "id": APP_ID,
        "aud": "c" * 64,
        "type": "self_hosted",
        "domain": f"private-target.example.com{PROBE_PATH}",
    }]})
    assert diagnose_bridge_target(access_apps, PROBE_PATH) == "CONTROL_APP_MISSING"

    _write(access_apps, {"success": True, "result": [{
        "id": APP_ID,
        "aud": AUDIENCE,
        "type": "self_hosted",
        "domain": "kmfa.linzezhang.com/",
    }]})
    assert diagnose_bridge_target(access_apps, PROBE_PATH) == "CONTROL_APP_MISSING"

    _write(access_apps, {"success": True, "result": [{
        "id": APP_ID,
        "aud": AUDIENCE,
        "type": "self_hosted",
        "domain": f"kmfa.linzezhang.com{PROBE_PATH}",
    }, {
        "id": "b3b4c5d6-1e2f-4a5b-8c9d-0e1f2a3b4c5d",
        "aud": AUDIENCE,
        "type": "self_hosted",
        "domain": f"kmfa.linzezhang.com{PROBE_PATH}",
    }]})
    assert diagnose_bridge_target(access_apps, PROBE_PATH) == "CONTROL_APP_AMBIGUOUS"
    assert diagnose_bridge_target(access_apps, "/ops/api/daily-funds/untrusted") == "CONTROL_PATH_INVALID"


def test_bridge_rejects_an_effective_destination_broader_than_the_fixed_control(tmp_path: Path) -> None:
    access_apps = _target_inputs(tmp_path, apps=[{
        "id": APP_ID,
        "aud": AUDIENCE,
        "type": "self_hosted",
        "domain": "kmfa.linzezhang.com/ops/*",
        "destinations": [
            {"type": "public", "uri": "kmfa.linzezhang.com/ops/*"},
            {"type": "public", "uri": "kmfa.linzezhang.com/*"},
        ],
    }])

    with pytest.raises(AccessBridgeInputError):
        resolve_bridge_target(access_apps, PROBE_PATH)


def test_bridge_uses_new_destinations_when_legacy_domain_is_stale(tmp_path: Path) -> None:
    """Cloudflare can retain a legacy root domain after a path migration."""

    access_apps = _target_inputs(tmp_path, apps=[{
        "id": APP_ID,
        "aud": AUDIENCE,
        "type": "self_hosted",
        "domain": "kmfa.linzezhang.com/",
        "destinations": [
            {"type": "public", "uri": f"kmfa.linzezhang.com{PROBE_PATH}"},
        ],
    }])

    assert resolve_bridge_target(access_apps, PROBE_PATH) == {
        "app_id": APP_ID,
        "origin": "https://kmfa.linzezhang.com",
    }


def test_bridge_rejects_new_destinations_with_mixed_origins(tmp_path: Path) -> None:
    access_apps = _target_inputs(tmp_path, apps=[{
        "id": APP_ID,
        "aud": AUDIENCE,
        "type": "self_hosted",
        "destinations": [
            {"type": "public", "uri": f"kmfa.linzezhang.com{PROBE_PATH}"},
            {"type": "public", "uri": f"other.example.com{PROBE_PATH}"},
        ],
    }])

    with pytest.raises(AccessBridgeInputError):
        resolve_bridge_target(access_apps, PROBE_PATH)


def test_bridge_rejects_a_different_fixed_control_path(tmp_path: Path) -> None:
    access_apps = _target_inputs(tmp_path, apps=[{
        "id": APP_ID,
        "aud": AUDIENCE,
        "type": "self_hosted",
        "domain": f"kmfa.linzezhang.com{RECOVERY_PATH}",
        "destinations": [{"type": "public", "uri": f"kmfa.linzezhang.com{RECOVERY_PATH}"}],
    }])

    with pytest.raises(AccessBridgeInputError):
        resolve_bridge_target(access_apps, PROBE_PATH)


def test_control_application_payload_and_policy_state_are_fixed_and_values_free(tmp_path: Path) -> None:
    assert control_application_payload(PROBE_PATH) == {
        "name": "kmfa-daily-funds-history-probe-control",
        "domain": f"kmfa.linzezhang.com{PROBE_PATH}",
        "type": "self_hosted",
        "app_launcher_visible": False,
    }
    assert control_application_payload(RECOVERY_PATH) == {
        "name": "kmfa-daily-funds-recovery-control",
        "domain": f"kmfa.linzezhang.com{RECOVERY_PATH}",
        "type": "self_hosted",
        "app_launcher_visible": False,
    }
    assert control_application_payload(PROJECTION_PATH) == {
        "name": "kmfa-daily-funds-projection-probe-control",
        "domain": f"kmfa.linzezhang.com{PROJECTION_PATH}",
        "type": "self_hosted",
        "app_launcher_visible": False,
    }
    with pytest.raises(AccessBridgeInputError):
        control_application_payload("/ops/api/daily-funds/untrusted")

    policies = tmp_path / "policies.json"
    _write(policies, {"success": True, "result_info": {"total_pages": 1}, "result": []})
    assert control_application_policy_state(policies) == "EMPTY"
    _write(policies, {"success": True, "result_info": {"total_pages": 1}, "result": [{"untrusted": "must-not-escape"}]})
    assert control_application_policy_state(policies) == "NOT_EMPTY"
    _write(policies, {"success": True, "result_info": {"total_pages": 2}, "result": []})
    assert control_application_policy_state(policies) == "INVALID"


def test_service_token_and_policy_payload_are_short_lived_and_app_specific() -> None:
    service = service_token_payload("12345-1")
    policy = policy_payload(SERVICE_TOKEN_ID, "12345-1")

    assert service == {
        "name": "kmfa-daily-funds-history-probe-12345-1",
        "duration": "60m",
    }
    assert policy == {
        "name": "kmfa-daily-funds-history-probe-12345-1",
        "decision": "non_identity",
        "include": [{"service_token": {"token_id": SERVICE_TOKEN_ID}}],
    }
    assert "precedence" not in policy
    assert "exclude" not in policy


def test_owned_resource_reconcile_selects_only_the_exact_run_tag(tmp_path: Path) -> None:
    service_tokens = tmp_path / "service-tokens.json"
    policies = tmp_path / "policies.json"
    _write(service_tokens, {
        "success": True,
        "result_info": {"total_pages": 1},
        "result": [
            {"id": SERVICE_TOKEN_ID, "name": "kmfa-daily-funds-history-probe-312-1"},
            {"id": POLICY_ID, "name": "kmfa-daily-funds-history-probe-unrelated"},
        ],
    })
    _write(policies, {
        "success": True,
        "result_info": {"total_pages": 1},
        "result": [
            {"id": POLICY_ID, "name": "kmfa-daily-funds-history-probe-312-1"},
            {"id": SERVICE_TOKEN_ID, "name": "kmfa-daily-funds-history-probe-312-10"},
        ],
    })

    assert owned_bridge_resource_ids(service_tokens, policies, "312-1") == {
        "service_token_ids": (SERVICE_TOKEN_ID,),
        "policy_ids": (POLICY_ID,),
    }

    manager = _load_script()
    material = tmp_path / "owned.env"
    assert manager.main([
        "write-owned-resource-env", "--service-tokens", str(service_tokens),
        "--policies", str(policies), "--run-tag", "312-1", "--output", str(material),
    ]) == 0
    assert stat.S_IMODE(material.stat().st_mode) == 0o600
    text = material.read_text(encoding="utf-8")
    assert SERVICE_TOKEN_ID in text and POLICY_ID in text
    assert "unrelated" not in text
    assert manager.main([
        "owned-resource-state", "--service-tokens", str(service_tokens),
        "--policies", str(policies), "--run-tag", "312-1",
    ]) == 0


def test_owned_resource_reconcile_rejects_a_paginated_provider_list(tmp_path: Path) -> None:
    service_tokens = tmp_path / "service-tokens.json"
    policies = tmp_path / "policies.json"
    _write(service_tokens, {
        "success": True,
        "result_info": {"total_pages": 2},
        "result": [],
    })
    _write(policies, {"success": True, "result": []})

    with pytest.raises(AccessBridgeInputError):
        owned_bridge_resource_ids(service_tokens, policies, "312-1")


def test_orphaned_resource_reconcile_requires_one_exact_expired_policy(tmp_path: Path) -> None:
    service_tokens = tmp_path / "service-tokens.json"
    policies = tmp_path / "policies.json"
    resource_name = "kmfa-daily-funds-history-probe-312-1"
    _write(service_tokens, {"success": True, "result_info": {"total_pages": 1}, "result": []})
    _write(policies, {
        "success": True,
        "result_info": {"total_pages": 1},
        "result": [{
            "id": POLICY_ID,
            "name": resource_name,
            "decision": "non_identity",
            "include": [{"service_token": {"token_id": SERVICE_TOKEN_ID}}],
        }],
    })

    assert orphaned_bridge_resource_ids(service_tokens, policies) == {
        "service_token_ids": (),
        "policy_ids": (POLICY_ID,),
    }

    manager = _load_script()
    material = tmp_path / "orphaned.env"
    assert manager.main([
        "write-orphaned-resource-env", "--service-tokens", str(service_tokens),
        "--policies", str(policies), "--output", str(material),
    ]) == 0
    assert stat.S_IMODE(material.stat().st_mode) == 0o600
    assert POLICY_ID in material.read_text(encoding="utf-8")


def test_orphaned_resource_reconcile_retires_one_completed_exact_short_lived_pair(tmp_path: Path) -> None:
    service_tokens = tmp_path / "service-tokens.json"
    policies = tmp_path / "policies.json"
    resource_name = "kmfa-daily-funds-history-probe-312-1"
    _write(service_tokens, {
        "success": True,
        "result_info": {"total_pages": 1},
        "result": [{
            "id": SERVICE_TOKEN_ID,
            "name": resource_name,
            "duration": "60m",
        }],
    })
    _write(policies, {
        "success": True,
        "result_info": {"total_pages": 1},
        "result": [{
            "id": POLICY_ID,
            "name": resource_name,
            "decision": "non_identity",
            "include": [{"service_token": {"token_id": SERVICE_TOKEN_ID}}],
        }],
    })

    assert orphaned_bridge_run_tag(policies) == "312-1"
    assert orphaned_bridge_resource_ids(
        service_tokens,
        policies,
        retired_run_tag="312-1",
    ) == {
        "service_token_ids": (SERVICE_TOKEN_ID,),
        "policy_ids": (POLICY_ID,),
    }

    manager = _load_script()
    tag_material = tmp_path / "orphaned-run-tag.env"
    assert manager.main([
        "write-orphaned-run-tag-env", "--policies", str(policies), "--output", str(tag_material),
    ]) == 0
    assert stat.S_IMODE(tag_material.stat().st_mode) == 0o600
    assert "CF_ACCESS_ORPHANED_RUN_TAG" in tag_material.read_text(encoding="utf-8")

    material = tmp_path / "retired-orphaned.env"
    assert manager.main([
        "write-orphaned-resource-env", "--service-tokens", str(service_tokens),
        "--policies", str(policies), "--retired-run-tag", "312-1", "--output", str(material),
    ]) == 0
    text = material.read_text(encoding="utf-8")
    assert SERVICE_TOKEN_ID in text and POLICY_ID in text


def test_orphaned_resource_diagnostic_is_finite_and_values_free(tmp_path: Path) -> None:
    service_tokens = tmp_path / "service-tokens.json"
    policies = tmp_path / "policies.json"
    resource_name = "kmfa-daily-funds-history-probe-312-1"
    _write(service_tokens, {"success": True, "result_info": {"total_pages": 1}, "result": []})
    _write(policies, {
        "success": True,
        "result_info": {"total_pages": 1},
        "result": [{
            "id": POLICY_ID,
            "name": resource_name,
            "decision": "non_identity",
            "include": [{"service_token": {"token_id": SERVICE_TOKEN_ID}}],
        }],
    })

    assert diagnose_orphaned_bridge_resources(service_tokens, policies) == "TOKEN_ABSENT"

    payload = json.loads(service_tokens.read_text(encoding="utf-8"))
    payload["result"] = [{
        "id": SERVICE_TOKEN_ID,
        "name": resource_name,
        "duration": "60m",
    }]
    _write(service_tokens, payload)
    assert diagnose_orphaned_bridge_resources(service_tokens, policies) == "TOKEN_COMPLETED_RUN_CANDIDATE"

    payload["result"][0]["duration"] = "24h"
    _write(service_tokens, payload)
    assert diagnose_orphaned_bridge_resources(service_tokens, policies) == "TOKEN_DURATION_UNEXPECTED"

    manager = _load_script()
    assert manager.main([
        "diagnose-orphaned-bridge", "--service-tokens", str(service_tokens), "--policies", str(policies),
    ]) == 0


def test_orphaned_resource_reconcile_preserves_a_policy_while_its_token_exists(tmp_path: Path) -> None:
    service_tokens = tmp_path / "service-tokens.json"
    policies = tmp_path / "policies.json"
    _write(service_tokens, {
        "success": True,
        "result_info": {"total_pages": 1},
        "result": [{"id": SERVICE_TOKEN_ID, "name": "kmfa-daily-funds-history-probe-312-1"}],
    })
    _write(policies, {
        "success": True,
        "result_info": {"total_pages": 1},
        "result": [{
            "id": POLICY_ID,
            "name": "kmfa-daily-funds-history-probe-312-1",
            "decision": "non_identity",
            "include": [{"service_token": {"token_id": SERVICE_TOKEN_ID}}],
        }],
    })

    with pytest.raises(AccessBridgeInputError):
        orphaned_bridge_resource_ids(service_tokens, policies)
    with pytest.raises(AccessBridgeInputError):
        orphaned_bridge_resource_ids(service_tokens, policies, retired_run_tag="312-2")

    payload = json.loads(service_tokens.read_text(encoding="utf-8"))
    payload["result"][0]["duration"] = "24h"
    _write(service_tokens, payload)
    with pytest.raises(AccessBridgeInputError):
        orphaned_bridge_resource_ids(service_tokens, policies, retired_run_tag="312-1")


@pytest.mark.parametrize("policy", (
    {"id": POLICY_ID, "name": "operator-policy", "decision": "non_identity", "include": [{"service_token": {"token_id": SERVICE_TOKEN_ID}}]},
    {"id": POLICY_ID, "name": "kmfa-daily-funds-history-probe-312-1", "decision": "allow", "include": [{"service_token": {"token_id": SERVICE_TOKEN_ID}}]},
    {"id": POLICY_ID, "name": "kmfa-daily-funds-history-probe-312-1", "decision": "non_identity", "include": [{"email": {"email": "owner@example.com"}}]},
))
def test_orphaned_resource_reconcile_preserves_any_non_ephemeral_policy(
    tmp_path: Path,
    policy: dict[str, object],
) -> None:
    service_tokens = tmp_path / "service-tokens.json"
    policies = tmp_path / "policies.json"
    _write(service_tokens, {"success": True, "result_info": {"total_pages": 1}, "result": []})
    _write(policies, {"success": True, "result_info": {"total_pages": 1}, "result": [policy]})

    with pytest.raises(AccessBridgeInputError):
        orphaned_bridge_resource_ids(service_tokens, policies)


def test_capture_and_summary_never_expose_service_secret_or_source_value(tmp_path: Path) -> None:
    secret = "service-secret-must-not-escape"
    response = tmp_path / "service-token.json"
    _write(response, {
        "success": True,
        "result": {
            "id": SERVICE_TOKEN_ID,
            "client_id": "client-id.access",
            "client_secret": secret,
        },
    })
    material = capture_service_token(response)
    assert material["client_secret"] == secret
    assert secret not in json.dumps({"id": material["service_token_id"]})

    probe = tmp_path / "probe.json"
    payload = _valid_probe()
    payload["raw_source_value"] = "source-value-must-not-escape"
    _write(probe, payload)
    summary = summarize_probe_response(
        probe,
        response_headers_path=_probe_headers(tmp_path / "probe.headers"),
        http_status="200",
        curl_exit=0,
    )
    rendered = json.dumps(summary)
    assert summary["transport"] == "INVALID_RESPONSE"
    assert secret not in rendered
    assert "source-value-must-not-escape" not in rendered


def test_probe_receipt_proves_cursor_reuse_without_storing_a_cursor(tmp_path: Path) -> None:
    response = tmp_path / "probe.json"
    _write(response, _valid_probe())

    summary = summarize_probe_response(
        response,
        response_headers_path=_probe_headers(tmp_path / "probe.headers"),
        http_status="200",
        curl_exit=0,
    )
    assert summary == {
        "schema_version": ACCESS_BRIDGE_SCHEMA,
        "transport": "OK",
        "probe_state": "COMPLETED",
        "continuation_state": "SECOND_PAGE_TERMINAL",
        "cursor_transcript": "OPAQUE_CURSOR_REUSED_SECOND_PAGE_TERMINAL",
        "record_list_shape": "NOT_OBSERVED",
        "machine_code": "DWS_HISTORY_PROBE_COMPLETED",
        "result": "HISTORY_PROBE_COMPLETED",
    }
    receipt = tmp_path / "receipt.json"
    _write(receipt, summary)
    assert probe_poll_state(receipt) == "COMPLETED"
    assert "opaque-page" not in json.dumps(summary)


def test_probe_receipt_rejects_untrusted_record_list_shape(tmp_path: Path) -> None:
    response = tmp_path / "probe.json"
    raw_shape = "source-value-must-not-escape"
    _write(response, _valid_probe(record_list_shape=raw_shape))

    summary = summarize_probe_response(
        response,
        response_headers_path=_probe_headers(tmp_path / "probe.headers"),
        http_status="200",
        curl_exit=0,
    )

    assert summary["transport"] == "INVALID_RESPONSE"
    assert raw_shape not in json.dumps(summary)


def test_probe_receipt_keeps_the_recordless_window_fallback_explicit(tmp_path: Path) -> None:
    response = tmp_path / "probe.json"
    _write(response, _valid_probe(continuation="GROUP_HISTORY_FALLBACK_SECOND_PAGE_TERMINAL"))

    summary = summarize_probe_response(
        response,
        response_headers_path=_probe_headers(tmp_path / "probe.headers"),
        http_status="200",
        curl_exit=0,
    )

    assert summary["result"] == "HISTORY_PROBE_COMPLETED"
    assert summary["continuation_state"] == "GROUP_HISTORY_FALLBACK_SECOND_PAGE_TERMINAL"
    assert summary["cursor_transcript"] == "GROUP_HISTORY_FALLBACK_OPAQUE_CURSOR_REUSED_SECOND_PAGE_TERMINAL"
    receipt = tmp_path / "receipt.json"
    _write(receipt, summary)
    assert probe_poll_state(receipt) == "COMPLETED"


def test_probe_receipt_keeps_provider_millisecond_continuation_distinct_from_opaque_search(tmp_path: Path) -> None:
    response = tmp_path / "probe.json"
    _write(response, _valid_probe(continuation="GROUP_HISTORY_V2_SECOND_PAGE_TERMINAL"))

    summary = summarize_probe_response(
        response,
        response_headers_path=_probe_headers(tmp_path / "probe.headers"),
        http_status="200",
        curl_exit=0,
    )

    assert summary["result"] == "GROUP_HISTORY_PROBE_COMPLETED"
    assert summary["machine_code"] == "DWS_GROUP_HISTORY_PROBE_COMPLETED"
    assert summary["continuation_state"] == "GROUP_HISTORY_V2_SECOND_PAGE_TERMINAL"
    assert summary["cursor_transcript"] == "GROUP_HISTORY_V2_PROVIDER_MILLISECOND_CURSOR_REUSED_SECOND_PAGE_TERMINAL"
    receipt = tmp_path / "receipt.json"
    _write(receipt, summary)
    assert probe_poll_state(receipt) == "COMPLETED"
    assert "nextCursor" not in json.dumps(summary)


@pytest.mark.parametrize(
    ("http_status", "curl_exit", "expected_transport", "expected_result", "expected_poll"),
    [
        ("401", 0, "HTTP_DENIED", "HISTORY_PROBE_START_ACCESS_OR_ORIGIN_DENIED", "TERMINAL_NOT_MET"),
        ("403", 0, "HTTP_DENIED", "HISTORY_PROBE_START_ACCESS_OR_ORIGIN_DENIED", "TERMINAL_NOT_MET"),
        ("302", 0, "HTTP_REDIRECT", "HISTORY_PROBE_START_HTTP_UNAVAILABLE", "TERMINAL_NOT_MET"),
        ("409", 0, "HTTP_CONFLICT", "HISTORY_PROBE_ALREADY_PENDING", "POLL"),
        ("422", 0, "HTTP_BODY_REJECTED", "HISTORY_PROBE_START_BODY_REJECTED", "TERMINAL_NOT_MET"),
        ("503", 0, "HTTP_CONTROL_UNAVAILABLE", "HISTORY_PROBE_START_CONTROL_UNAVAILABLE", "TERMINAL_NOT_MET"),
        ("000", 28, "TRANSPORT_FAILED", "HISTORY_PROBE_START_TRANSPORT_FAILED", "TERMINAL_NOT_MET"),
    ],
)
def test_probe_start_receipt_is_finite_and_only_pending_is_pollable(
    tmp_path: Path,
    http_status: str,
    curl_exit: int,
    expected_transport: str,
    expected_result: str,
    expected_poll: str,
) -> None:
    response = tmp_path / "probe-start.json"
    _write(response, {"untrusted": "source-value-must-not-escape"})

    summary = summarize_probe_start_response(
        response,
        response_headers_path=_probe_headers(tmp_path / "probe-start.headers"),
        http_status=http_status,
        curl_exit=curl_exit,
    )

    assert summary == {
        "schema_version": ACCESS_BRIDGE_SCHEMA,
        "transport": expected_transport,
        "result": expected_result,
    }
    _write(response, summary)
    assert probe_start_poll_state(response) == expected_poll
    assert "source-value-must-not-escape" not in json.dumps(summary)


def test_probe_start_accepts_only_the_fixed_queued_receipt(tmp_path: Path) -> None:
    response = tmp_path / "probe-start.json"
    headers = _probe_headers(tmp_path / "probe-start.headers")
    _write(response, {
        "state": "REQUESTED",
        "machine_code": "DWS_HISTORY_PROBE_QUEUED",
        "updated_at": "2026-08-09T00:00:00Z",
        "expires_at": "2026-08-09T00:10:00Z",
        "continuation_state": "NOT_STARTED",
        "cursor_transcript": "NOT_STARTED",
        "record_list_shape": "NOT_OBSERVED",
    })

    summary = summarize_probe_start_response(
        response,
        response_headers_path=headers,
        http_status="202",
        curl_exit=0,
    )

    assert summary == {
        "schema_version": ACCESS_BRIDGE_SCHEMA,
        "transport": "OK",
        "result": "HISTORY_PROBE_REQUESTED",
    }
    _write(response, summary)
    assert probe_start_poll_state(response) == "POLL"

    _write(response, {"state": "REQUESTED", "opaque_request_id": "must-not-escape"})
    malformed = summarize_probe_start_response(
        response,
        response_headers_path=headers,
        http_status="202",
        curl_exit=0,
    )
    assert malformed["result"] == "HISTORY_PROBE_START_INVALID_RESPONSE"
    assert "must-not-escape" not in json.dumps(malformed)


def test_probe_start_does_not_attribute_an_unmarked_503_to_the_control_volume(tmp_path: Path) -> None:
    response = tmp_path / "probe-start.json"
    _write(response, {"untrusted": "edge-body-must-not-escape"})

    summary = summarize_probe_start_response(
        response,
        response_headers_path=_probe_headers(tmp_path / "probe-start.headers", origin_marker=False),
        http_status="503",
        curl_exit=0,
    )

    assert summary == {
        "schema_version": ACCESS_BRIDGE_SCHEMA,
        "transport": "HTTP_UPSTREAM_UNAVAILABLE",
        "result": "HISTORY_PROBE_START_UPSTREAM_UNAVAILABLE",
    }
    assert "edge-body-must-not-escape" not in json.dumps(summary)


def test_recovery_receipt_accepts_only_fixed_recovery_states(tmp_path: Path) -> None:
    response = tmp_path / "recovery.json"
    headers = _recovery_headers(tmp_path / "recovery.headers")
    _write(response, {
        "state": "SUCCEEDED",
        "machine_code": "DAILY_FUNDS_RECOVERY_PUBLISHED_NEEDS_REVIEW",
        "updated_at": "2026-08-09T00:00:00Z",
        "expires_at": "2026-08-09T00:50:00Z",
        "completed_steps": ["RAW_ARCHIVE_AUDIT", "RAW_COVERAGE_REPAIR", "RAW_FACT_REPLAY"],
        "active_step": "NONE",
    })

    summary = summarize_recovery_response(
        response,
        response_headers_path=headers,
        http_status="200",
        curl_exit=0,
    )

    assert summary == {
        "schema_version": ACCESS_BRIDGE_SCHEMA,
        "transport": "OK",
        "recovery_state": "SUCCEEDED",
        "completed_step_count": "3",
        "active_step": "NONE",
        "machine_code": "DAILY_FUNDS_RECOVERY_PUBLISHED_NEEDS_REVIEW",
        "result": "RECOVERY_PUBLISHED_NEEDS_REVIEW",
    }
    _write(response, summary)
    assert recovery_poll_state(response) == "PUBLISHED_NEEDS_REVIEW"

    _write(response, {
        "state": "FAILED",
        "machine_code": "DAILY_FUNDS_RECOVERY_AUDIT_SOURCE_MISSING",
        "updated_at": "2026-08-25T10:00:00Z",
        "expires_at": "2026-08-25T10:50:00Z",
        "completed_steps": [],
        "active_step": "RAW_ARCHIVE_AUDIT",
    })
    failure = summarize_recovery_response(
        response,
        response_headers_path=headers,
        http_status="200",
        curl_exit=0,
    )
    assert failure == {
        "schema_version": ACCESS_BRIDGE_SCHEMA,
        "transport": "OK",
        "recovery_state": "FAILED",
        "completed_step_count": "0",
        "active_step": "RAW_ARCHIVE_AUDIT",
        "machine_code": "DAILY_FUNDS_RECOVERY_AUDIT_SOURCE_MISSING",
        "result": "NOT_MET",
    }
    _write(response, failure)
    assert recovery_poll_state(response) == "TERMINAL_NOT_MET"

    _write(response, {
        "state": "RUNNING",
        "machine_code": "DAILY_FUNDS_RECOVERY_RUNNING",
        "updated_at": "2026-08-09T00:00:00Z",
        "expires_at": "2026-08-09T00:50:00Z",
        "completed_steps": ["RAW_ARCHIVE_AUDIT"],
        "active_step": "RAW_COVERAGE_REPAIR",
        "private_raw": "must-not-escape",
    })
    malformed = summarize_recovery_response(
        response,
        response_headers_path=headers,
        http_status="200",
        curl_exit=0,
    )
    assert malformed["result"] == "NOT_MET"
    assert "must-not-escape" not in json.dumps(malformed)

    _write(response, {
        "state": "RUNNING",
        "machine_code": "DAILY_FUNDS_RECOVERY_RUNNING",
        "updated_at": "2026-08-09T00:00:00Z",
        "expires_at": "2026-08-09T06:00:00Z",
        "completed_steps": [],
        "active_step": "RAW_ARCHIVE_AUDIT",
    })
    active = summarize_recovery_response(
        response,
        response_headers_path=headers,
        http_status="200",
        curl_exit=0,
    )
    _write(response, active)
    assert recovery_poll_state(response) == "ASYNC_RUNNING"


@pytest.mark.parametrize(
    ("http_status", "origin_marker", "expected_transport"),
    [
        ("204", False, "HTTP_UNEXPECTED_SUCCESS_STATUS"),
        ("302", False, "HTTP_REDIRECT"),
        ("404", False, "HTTP_CLIENT_ERROR"),
        ("502", False, "HTTP_UPSTREAM_SERVER_ERROR"),
        ("502", True, "HTTP_CONTROL_SERVER_ERROR"),
    ],
)
def test_recovery_receipt_classifies_unexpected_statuses_without_exposing_response(
    tmp_path: Path,
    http_status: str,
    origin_marker: bool,
    expected_transport: str,
) -> None:
    response = tmp_path / "recovery.json"
    _write(response, {"untrusted": "must-not-escape"})

    summary = summarize_recovery_response(
        response,
        response_headers_path=_recovery_headers(tmp_path / "recovery.headers", origin_marker=origin_marker),
        http_status=http_status,
        curl_exit=0,
    )

    assert summary["transport"] == expected_transport
    assert summary["result"] == "NOT_MET"
    assert "must-not-escape" not in json.dumps(summary)


@pytest.mark.parametrize("transport", ["TRANSPORT_FAILED", "HTTP_UPSTREAM_SERVER_ERROR"])
def test_recovery_poll_retries_only_fixed_upstream_transients(tmp_path: Path, transport: str) -> None:
    receipt = tmp_path / "receipt.json"
    _write(receipt, {
        "schema_version": ACCESS_BRIDGE_SCHEMA,
        "transport": transport,
        "recovery_state": "UNCLASSIFIED",
        "completed_step_count": "UNCLASSIFIED",
        "active_step": "UNCLASSIFIED",
        "machine_code": "UNCLASSIFIED",
        "result": "NOT_MET",
    })

    assert recovery_poll_state(receipt) == "RETRY"


def test_recovery_poll_keeps_control_server_errors_terminal(tmp_path: Path) -> None:
    receipt = tmp_path / "receipt.json"
    _write(receipt, {
        "schema_version": ACCESS_BRIDGE_SCHEMA,
        "transport": "HTTP_CONTROL_SERVER_ERROR",
        "recovery_state": "UNCLASSIFIED",
        "completed_step_count": "UNCLASSIFIED",
        "active_step": "UNCLASSIFIED",
        "machine_code": "UNCLASSIFIED",
        "result": "NOT_MET",
    })

    assert recovery_poll_state(receipt) == "TERMINAL_NOT_MET"


def test_projection_probe_receipt_requires_full_storage_and_readonly_projection(tmp_path: Path) -> None:
    response = tmp_path / "projection.json"
    headers = _projection_headers(tmp_path / "projection.headers")
    _write(response, _valid_projection())

    summary = summarize_projection_response(
        response,
        response_headers_path=headers,
        http_status="200",
        curl_exit=0,
    )

    assert summary == {
        "schema_version": ACCESS_BRIDGE_SCHEMA,
        "transport": "OK",
        "projection_state": "PUBLISHED",
        "d1_projection": "VERIFIED",
        "r2_mirror": "VERIFIED",
        "oci_backup": "OK",
        "readonly_projection": "VERIFIED",
        "result": "PROJECTION_VERIFIED",
    }
    _write(response, summary)
    assert projection_poll_state(response) == "COMPLETED"

    _write(response, _valid_projection(oci_backup="LAG"))
    lagging = summarize_projection_response(
        response,
        response_headers_path=headers,
        http_status="200",
        curl_exit=0,
    )
    assert lagging["result"] == "PROJECTION_NEEDS_REVIEW"
    _write(response, lagging)
    assert projection_poll_state(response) == "TERMINAL_NOT_MET"

    _write(response, {
        "schema_version": "kmfa.daily_funds.projection_probe.v1",
        "state": "UNAVAILABLE",
        "d1_projection": "UNVERIFIED",
        "r2_mirror": "UNVERIFIED",
        "oci_backup": "UNKNOWN",
        "readonly_projection": "UNVERIFIED",
        "untrusted": "must-not-escape",
    })
    malformed = summarize_projection_response(
        response,
        response_headers_path=headers,
        http_status="200",
        curl_exit=0,
    )
    assert malformed["result"] == "NOT_MET"
    assert "must-not-escape" not in json.dumps(malformed)

    unmarked = summarize_projection_response(
        response,
        response_headers_path=_projection_headers(tmp_path / "unmarked.headers", origin_marker=False),
        http_status="200",
        curl_exit=0,
    )
    assert unmarked["transport"] == "HTTP_ORIGIN_UNVERIFIED"


def test_recovery_start_receipt_is_fixed_and_only_pending_is_pollable(tmp_path: Path) -> None:
    response = tmp_path / "recovery-start.json"
    headers = _recovery_headers(tmp_path / "recovery-start.headers")
    _write(response, {
        "state": "REQUESTED",
        "machine_code": "DAILY_FUNDS_RECOVERY_QUEUED",
        "updated_at": "2026-08-09T00:00:00Z",
        "expires_at": "2026-08-09T00:50:00Z",
        "completed_steps": [],
        "active_step": "RAW_ARCHIVE_AUDIT",
    })

    summary = summarize_recovery_start_response(
        response,
        response_headers_path=headers,
        http_status="202",
        curl_exit=0,
    )
    assert summary == {
        "schema_version": ACCESS_BRIDGE_SCHEMA,
        "transport": "OK",
        "result": "RECOVERY_REQUESTED",
    }
    _write(response, summary)
    assert recovery_start_poll_state(response) == "POLL"

    _write(response, {"untrusted": "must-not-escape"})
    denied = summarize_recovery_start_response(
        response,
        response_headers_path=headers,
        http_status="403",
        curl_exit=0,
    )
    assert denied == {
        "schema_version": ACCESS_BRIDGE_SCHEMA,
        "transport": "HTTP_DENIED",
        "result": "RECOVERY_START_ACCESS_OR_ORIGIN_DENIED",
    }
    assert "must-not-escape" not in json.dumps(denied)

    redirected = summarize_recovery_start_response(
        response,
        response_headers_path=headers,
        http_status="302",
        curl_exit=0,
    )
    assert redirected == {
        "schema_version": ACCESS_BRIDGE_SCHEMA,
        "transport": "HTTP_REDIRECT",
        "result": "RECOVERY_START_HTTP_UNAVAILABLE",
    }


def test_bridge_manager_writes_private_material_and_only_prints_finite_receipt(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manager = _load_script()
    access_apps = _target_inputs(tmp_path)
    target = tmp_path / "target.env"
    assert manager.main([
        "resolve-target", "--access-apps", str(access_apps), "--control-path", PROBE_PATH,
        "--output", str(target),
    ]) == 0
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert "kmfa.linzezhang.com" in target.read_text(encoding="utf-8")
    assert capsys.readouterr().out == ""

    assert manager.main([
        "diagnose-target", "--access-apps", str(access_apps), "--control-path", PROBE_PATH,
    ]) == 0
    output = capsys.readouterr().out
    assert output == "RESOLVED\n"
    assert "kmfa.linzezhang.com" not in output

    control_payload = tmp_path / "control-app.json"
    assert manager.main([
        "write-control-app-payload", "--control-path", RECOVERY_PATH,
        "--output", str(control_payload),
    ]) == 0
    assert stat.S_IMODE(control_payload.stat().st_mode) == 0o600
    assert capsys.readouterr().out == ""

    response = tmp_path / "probe.json"
    headers = _probe_headers(tmp_path / "probe.headers")
    _write(response, _valid_probe())
    assert manager.main([
        "summarize-probe", "--response", str(response), "--headers", str(headers), "--http-status", "200", "--curl-exit", "0",
    ]) == 0
    output = capsys.readouterr().out
    assert json.loads(output)["result"] == "HISTORY_PROBE_COMPLETED"
    assert "kmfa.linzezhang.com" not in output
    assert "service-secret" not in output

    projection = tmp_path / "projection.json"
    projection_headers = _projection_headers(tmp_path / "projection.headers")
    _write(projection, _valid_projection())
    assert manager.main([
        "summarize-projection", "--response", str(projection), "--headers", str(projection_headers), "--http-status", "200", "--curl-exit", "0",
    ]) == 0
    output = capsys.readouterr().out
    assert json.loads(output)["result"] == "PROJECTION_VERIFIED"
    assert "kmfa.linzezhang.com" not in output
    assert "service-secret" not in output


def test_workflow_bridge_is_manual_main_only_fixed_route_and_cleanup_scoped() -> None:
    workflow = (ROOT.parents[2] / ".github" / "workflows" / "coolify-ops.yml").read_text(encoding="utf-8")
    start = workflow.index("受控读取或触发每日资金固定任务")
    end = workflow.find("\n      - name:", start + 1)
    step = workflow[start:] if end == -1 else workflow[start:end]

    assert "inputs.mode == 'daily-funds-history-probe-bridge'" in step
    assert "inputs.mode == 'daily-funds-recovery-bridge'" in step
    assert "inputs.mode == 'daily-funds-recovery-status-bridge'" in step
    assert "inputs.mode == 'daily-funds-projection-probe-bridge'" in step
    assert "CONTROL_MODE: ${{ inputs.mode }}" in step
    assert 'case "${CONTROL_MODE:-}" in' in step
    assert 'GITHUB_REF:-}" = "refs/heads/main"' in step
    assert "access/service_tokens" in step
    assert "/access/apps/${CF_ACCESS_APP_ID}/policies" in step
    assert "CF-Access-Client-Secret" in step
    assert "CONTROL_PATH=/ops/api/daily-funds/history-probe" in step
    assert "CONTROL_PATH=/ops/api/daily-funds/recovery" in step
    assert "CONTROL_PATH=/ops/api/daily-funds/projection-probe" in step
    assert "CONTROL_KIND=RECOVERY_STATUS" in step
    assert "CONTROL_KIND=PROJECTION" in step
    assert '"$CONTROL_ORIGIN$CONTROL_PATH"' in step
    assert "diagnose-target" in step
    assert "--coolify-env" not in step
    assert '$BASE/api/v1/applications/$APP/envs' not in step
    assert "CONTROL_APP_MISSING" in step
    assert "CONTROL_APP_AMBIGUOUS" in step
    assert "write-control-app-payload" in step
    assert "control-app-policy-state" in step
    assert "CONTROL_ACCESS_POLICY_NOT_EMPTY" in step
    assert "GH_TOKEN: ${{ github.token }}" in step
    assert "capture-service-token-id" in step
    assert "capture-policy" in step
    assert "summarize-probe-start" in step
    assert "summarize-recovery-start" in step
    assert "summarize-projection" in step
    assert '-D "$output.headers"' in step
    assert "probe-post.json.headers" in step
    assert "probe-get.json.headers" in step
    assert "probe-start-poll-state" in step
    assert "recovery-start-poll-state" in step
    assert "CONTROL_POLL_ATTEMPTS=3" in step
    assert "ASYNC_RUNNING)" in step
    assert "RECOVERY_ASYNC_RUNNING" in step
    assert 'if [ "$CONTROL_KIND" = "HISTORY" ] || [ "$CONTROL_KIND" = "RECOVERY" ]; then' in step
    assert "RECOVERY|RECOVERY_STATUS)" in step
    assert "PROJECTION) test \"$probe_outcome\" = \"PROJECTION_VERIFIED\" ;;" in step
    assert "RETRY)" in step
    assert "sleep 10" in step
    policy_ready = step.index("policy_created=1")
    access_settle = step.index("sleep 10", policy_ready)
    status_post_guard = step.index('if [ "$CONTROL_KIND" = "HISTORY" ] || [ "$CONTROL_KIND" = "RECOVERY" ]; then')
    assert policy_ready < access_settle < status_post_guard
    assert "reconcile_owned_resources()" in step
    assert "reconcile_orphaned_control_policy()" in step
    assert "write-owned-resource-env" in step
    assert "write-orphaned-resource-env" in step
    assert "write-orphaned-run-tag-env" in step
    assert "diagnose-orphaned-bridge" in step
    assert "--retired-run-tag" in step
    assert "/actions/runs/${orphaned_run_id}/attempts/${orphaned_run_attempt}" in step
    assert "UNRECONCILABLE_${orphaned_diagnostic}" in step
    assert "RUN_LOOKUP_UNAVAILABLE" in step
    assert "RUN_NOT_COMPLETED" in step
    assert "RUN_IDENTITY_INVALID" in step
    assert "owned-resource-state" in step
    assert "orphaned_bridge=RECONCILED" in step
    assert "request_cf DELETE" in step
    assert "duration" not in step  # duration is fixed in the Python allowlist, not workflow input.
    assert "inputs.command" not in step
    assert "--data @\"$payload\"" in step
    assert "rm -rf" not in step

    assert "permissions:\n  actions: read\n  contents: read" in workflow

    assert "daily-funds-history-probe-cleanup" in workflow
    assert "daily-funds-recovery-cleanup" in workflow
    assert "daily-funds-projection-probe-cleanup" in workflow
    assert "inputs.bridge_run_tag" in workflow
    assert "RUN_TAG_INVALID" in workflow
    cleanup_start = workflow.index("清理指定每日资金控制路径的短时 Access 身份")
    cleanup_end = workflow.find("\n      - name:", cleanup_start + 1)
    cleanup_step = workflow[cleanup_start:] if cleanup_end == -1 else workflow[cleanup_start:cleanup_end]
    assert "CONTROL_MODE: ${{ inputs.mode }}" in cleanup_step
    assert 'case "${CONTROL_MODE:-}" in' in cleanup_step


def test_workflow_recovery_restart_is_main_only_and_target_verified() -> None:
    workflow = (ROOT.parents[2] / ".github" / "workflows" / "coolify-ops.yml").read_text(encoding="utf-8")
    start = workflow.index("受控重启每日资金恢复目标")
    end = workflow.find("\n      - name:", start + 1)
    step = workflow[start:] if end == -1 else workflow[start:end]

    assert "inputs.mode == 'daily-funds-recovery-restart'" in step
    assert 'GITHUB_REF:-}" = "refs/heads/main"' in step
    assert "daily_funds_recovery_restart=MAIN_REF_REQUIRED" in step
    assert "daily_funds_recovery_restart=APP_REQUIRED" in step
    assert 'payload.get("name") != "kmfa-kmos-p1"' in step
    assert 'payload.get("build_pack") != "dockercompose"' in step
    assert '"$BASE/api/v1/applications/$APP/restart"' in step
    assert "daily_funds_recovery_restart=REQUESTED" in step
    assert "daily-funds-recovery-restart.json" in step
    assert "trap 'rm -f" in step
    assert "json.dumps" not in step
    assert "inputs.command" not in step


def test_workflow_component_restart_requires_an_exact_compose_component_mapping() -> None:
    workflow = (ROOT.parents[2] / ".github" / "workflows" / "coolify-ops.yml").read_text(encoding="utf-8")
    start = workflow.index("精确重启每日资金组件")
    end = workflow.index("只读分类每日资金运行拓扑", start)
    step = workflow[start:end]

    assert "daily-funds-recovery-component-restart" in workflow
    assert "inputs.mode == 'daily-funds-recovery-component-restart'" in step
    assert 'GITHUB_REF:-}" = "refs/heads/main"' in step
    assert "daily_funds_component_restart=MAIN_REF_REQUIRED" in step
    assert "daily_funds_component_restart=APP_REQUIRED" in step
    assert "daily_funds_component_restart=APP_INVALID" in step
    assert 'app.get("name") != "kmfa-kmos-p1"' in step
    assert 'app.get("build_pack") != "dockercompose"' in step
    assert '"docker_compose_raw"' in step
    assert "def runtime_key(record: dict):" in step
    assert 'for key in ("environment_id", "destination_id", "destination_type"):' in step
    assert "target_runtime = runtime_key(app)" in step
    assert "TARGET_RUNTIME_BINDING_UNAVAILABLE" in step
    assert "runtime_key(service) != target_runtime" in step
    assert "contains_daily_funds_component(compose)" in step
    assert 'component.get("name") == "daily-funds"' in step
    assert '"$BASE/api/v1/services"' in step
    assert '"$BASE/api/v1/services/$service_uuid/applications"' in step
    assert '"$BASE/api/v1/services/$service_uuid/applications/$component_uuid/restart"' in step
    assert "SERVICE_COMPONENT_MAP_UNAVAILABLE" in step
    assert "SERVICE_COMPONENT_NOT_UNIQUE" in step
    assert "daily_funds_component_restart=REQUESTED" in step
    assert "daily-funds-component-restart.json" in step
    assert "trap 'rm -f" in step
    assert "json.dumps" not in step
    assert "inputs.command" not in step


def test_workflow_force_rebuild_uses_the_documented_deploy_route_only() -> None:
    workflow = (ROOT.parents[2] / ".github" / "workflows" / "coolify-ops.yml").read_text(encoding="utf-8")
    start = workflow.index("受控强制重建每日资金恢复目标")
    end = workflow.index("前进每日资金受控源码并重建", start)
    step = workflow[start:end]

    assert "daily-funds-recovery-force-rebuild" in workflow
    assert "inputs.mode == 'daily-funds-recovery-force-rebuild'" in step
    assert 'GITHUB_REF:-}" = "refs/heads/main"' in step
    assert "daily_funds_force_rebuild=MAIN_REF_REQUIRED" in step
    assert "daily_funds_force_rebuild=APP_REQUIRED" in step
    assert "daily_funds_force_rebuild=APP_INVALID" in step
    assert 'app.get("name") != "kmfa-kmos-p1"' in step
    assert 'app.get("build_pack") != "dockercompose"' in step
    assert 'compose_location = normalize_path(record.get("docker_compose_location"), allow_empty=False)' in step
    assert "COMPOSE_LOCATION_STATE_UNAVAILABLE" in step
    assert 'location_fields = ("base_directory", "docker_compose_location")' in step
    assert '("KMFA", "deploy/coolify/docker-compose.yml")' in step
    assert "expected_compose_location" in step
    assert "jq -r '.requires_collection'" in step
    assert "jq -er '.requires_collection'" not in step
    assert '"docker_compose_custom_start_command"' in step
    assert '"docker_compose_custom_build_command"' in step
    assert "COMPOSE_COMMAND_STATE_UNAVAILABLE" in step
    assert "COMPOSE_COMMAND_CONFIGURED" in step
    assert '"$BASE/api/v1/applications"' in step
    assert "APPLICATION_COLLECTION_TARGET_UNAVAILABLE" in step
    assert "daily_funds_force_rebuild_command_source=COLLECTION" in step
    assert '"$BASE/api/v1/deployments/applications/$APP"' in step
    assert "DEPLOYMENT_ALREADY_ACTIVE" in step
    assert "terminal_statuses" in step
    assert "active_records" in step
    assert '"finished"' in step
    assert '"$BASE/api/v1/deploy?uuid=$APP&force=true"' in step
    assert '"$BASE/api/v1/deployments/$deployment_uuid"' in step
    assert "daily_funds_force_rebuild_deployment=QUEUED" in step
    assert "daily_funds_force_rebuild=FINISHED" in step
    assert "-X PATCH" not in step
    assert "--force-recreate" not in step
    assert "json.dumps" not in step
    assert "inputs.command" not in step
    assert "rm -rf" not in step
