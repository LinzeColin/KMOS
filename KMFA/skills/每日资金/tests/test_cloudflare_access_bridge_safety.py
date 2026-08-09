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
    capture_policy,
    capture_service_token,
    policy_payload,
    probe_poll_state,
    probe_start_poll_state,
    resolve_bridge_target,
    service_token_payload,
    summarize_probe_start_response,
    summarize_probe_response,
)


APP_ID = "2d7ac813-4f60-4d2f-9c69-8d5294e4c7fe"
SERVICE_TOKEN_ID = "20b0c6f3-77f1-4591-8f4a-d643709b42cf"
POLICY_ID = "a2b3c4d5-1e2f-4a5b-8c9d-0e1f2a3b4c5d"
AUDIENCE = "a" * 64


def _write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _target_inputs(tmp_path: Path, *, apps: list[object] | None = None) -> tuple[Path, Path]:
    envs = tmp_path / "envs.json"
    access_apps = tmp_path / "apps.json"
    _write(envs, [
        {"key": "KMFA_CLOUDFLARE_ACCESS_AUD", "value": f"{AUDIENCE},{'b' * 64}"},
        {"key": "KMFA_CLOUDFLARE_ACCESS_AUD", "value": f"{AUDIENCE},{'b' * 64}"},
    ])
    _write(access_apps, {
        "success": True,
        "result_info": {"total_pages": 1},
        "result": apps if apps is not None else [{
            "id": APP_ID,
            "aud": AUDIENCE,
            "type": "self_hosted",
            "domain": "kmfa.example.com/ops/*",
        }],
    })
    return envs, access_apps


def _valid_probe(*, state: str = "COMPLETED", continuation: str = "SECOND_PAGE_TERMINAL") -> dict[str, object]:
    cursor = {
        "NOT_STARTED": "NOT_STARTED",
        "FIRST_PAGE_TERMINAL": "FIRST_PAGE_TERMINAL",
        "SECOND_PAGE_TERMINAL": "OPAQUE_CURSOR_REUSED_SECOND_PAGE_TERMINAL",
        "SECOND_PAGE_CONTINUES": "OPAQUE_CURSOR_REUSED_SECOND_PAGE_CONTINUES",
    }[continuation]
    machine = "DWS_HISTORY_PROBE_COMPLETED" if state == "COMPLETED" else "DWS_HISTORY_PROBE_RUNNING"
    return {
        "state": state,
        "machine_code": machine,
        "updated_at": "2026-08-09T00:00:00Z",
        "expires_at": "2026-08-09T00:10:00Z",
        "continuation_state": continuation,
        "cursor_transcript": cursor,
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


def test_bridge_resolves_only_one_narrow_configured_ops_application(tmp_path: Path) -> None:
    envs, access_apps = _target_inputs(tmp_path)

    assert resolve_bridge_target(envs, access_apps) == {
        "app_id": APP_ID,
        "origin": "https://kmfa.example.com",
    }


@pytest.mark.parametrize("domain", ["kmfa.example.com/*", "kmfa.example.com/", "http://kmfa.example.com/ops/*", "localhost/ops/*"])
def test_bridge_rejects_broad_or_non_https_access_targets(tmp_path: Path, domain: str) -> None:
    envs, access_apps = _target_inputs(tmp_path, apps=[{
        "id": APP_ID,
        "aud": AUDIENCE,
        "type": "self_hosted",
        "domain": domain,
    }])

    with pytest.raises(AccessBridgeInputError):
        resolve_bridge_target(envs, access_apps)


def test_bridge_rejects_ambiguous_or_paginated_access_application_list(tmp_path: Path) -> None:
    duplicate = {
        "id": "b3b4c5d6-1e2f-4a5b-8c9d-0e1f2a3b4c5d",
        "aud": AUDIENCE,
        "type": "self_hosted",
        "domain": "kmfa.example.com/ops/api/*",
    }
    envs, access_apps = _target_inputs(tmp_path, apps=[{
        "id": APP_ID,
        "aud": AUDIENCE,
        "type": "self_hosted",
        "domain": "kmfa.example.com/ops/*",
    }, duplicate])
    with pytest.raises(AccessBridgeInputError):
        resolve_bridge_target(envs, access_apps)

    payload = json.loads(access_apps.read_text(encoding="utf-8"))
    payload["result"] = [payload["result"][0]]
    payload["result_info"] = {"total_pages": 2}
    _write(access_apps, payload)
    with pytest.raises(AccessBridgeInputError):
        resolve_bridge_target(envs, access_apps)


def test_bridge_rejects_an_effective_destination_broader_than_the_fixed_ops_probe(tmp_path: Path) -> None:
    envs, access_apps = _target_inputs(tmp_path, apps=[{
        "id": APP_ID,
        "aud": AUDIENCE,
        "type": "self_hosted",
        "domain": "kmfa.example.com/ops/*",
        "destinations": [
            {"type": "public", "uri": "kmfa.example.com/ops/*"},
            {"type": "public", "uri": "kmfa.example.com/*"},
        ],
    }])

    with pytest.raises(AccessBridgeInputError):
        resolve_bridge_target(envs, access_apps)


def test_bridge_uses_new_destinations_when_legacy_domain_is_stale(tmp_path: Path) -> None:
    """Cloudflare can retain a legacy root domain after a path migration."""

    envs, access_apps = _target_inputs(tmp_path, apps=[{
        "id": APP_ID,
        "aud": AUDIENCE,
        "type": "self_hosted",
        "domain": "kmfa.example.com/",
        "destinations": [
            {"type": "public", "uri": "kmfa.example.com/ops"},
            {"type": "public", "uri": "kmfa.example.com/ops/*"},
        ],
    }])

    assert resolve_bridge_target(envs, access_apps) == {
        "app_id": APP_ID,
        "origin": "https://kmfa.example.com",
    }


def test_bridge_rejects_new_destinations_with_mixed_origins(tmp_path: Path) -> None:
    envs, access_apps = _target_inputs(tmp_path, apps=[{
        "id": APP_ID,
        "aud": AUDIENCE,
        "type": "self_hosted",
        "destinations": [
            {"type": "public", "uri": "kmfa.example.com/ops/*"},
            {"type": "public", "uri": "other.example.com/ops/*"},
        ],
    }])

    with pytest.raises(AccessBridgeInputError):
        resolve_bridge_target(envs, access_apps)


def test_bridge_requires_a_probe_covering_path_beside_exact_ops_landing_path(tmp_path: Path) -> None:
    envs, access_apps = _target_inputs(tmp_path, apps=[{
        "id": APP_ID,
        "aud": AUDIENCE,
        "type": "self_hosted",
        "domain": "kmfa.example.com/ops",
        "destinations": [{"type": "public", "uri": "kmfa.example.com/ops"}],
    }])

    with pytest.raises(AccessBridgeInputError):
        resolve_bridge_target(envs, access_apps)


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
    summary = summarize_probe_response(probe, http_status="200", curl_exit=0)
    rendered = json.dumps(summary)
    assert summary["transport"] == "INVALID_RESPONSE"
    assert secret not in rendered
    assert "source-value-must-not-escape" not in rendered


def test_probe_receipt_proves_cursor_reuse_without_storing_a_cursor(tmp_path: Path) -> None:
    response = tmp_path / "probe.json"
    _write(response, _valid_probe())

    summary = summarize_probe_response(response, http_status="200", curl_exit=0)
    assert summary == {
        "schema_version": ACCESS_BRIDGE_SCHEMA,
        "transport": "OK",
        "probe_state": "COMPLETED",
        "continuation_state": "SECOND_PAGE_TERMINAL",
        "cursor_transcript": "OPAQUE_CURSOR_REUSED_SECOND_PAGE_TERMINAL",
        "machine_code": "DWS_HISTORY_PROBE_COMPLETED",
        "result": "HISTORY_PROBE_COMPLETED",
    }
    receipt = tmp_path / "receipt.json"
    _write(receipt, summary)
    assert probe_poll_state(receipt) == "COMPLETED"
    assert "opaque-page" not in json.dumps(summary)


@pytest.mark.parametrize(
    ("http_status", "curl_exit", "expected_transport", "expected_result", "expected_poll"),
    [
        ("401", 0, "HTTP_DENIED", "HISTORY_PROBE_START_ACCESS_OR_ORIGIN_DENIED", "TERMINAL_NOT_MET"),
        ("403", 0, "HTTP_DENIED", "HISTORY_PROBE_START_ACCESS_OR_ORIGIN_DENIED", "TERMINAL_NOT_MET"),
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

    summary = summarize_probe_start_response(response, http_status=http_status, curl_exit=curl_exit)

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
    _write(response, {
        "state": "REQUESTED",
        "machine_code": "DWS_HISTORY_PROBE_QUEUED",
        "updated_at": "2026-08-09T00:00:00Z",
        "expires_at": "2026-08-09T00:10:00Z",
        "continuation_state": "NOT_STARTED",
        "cursor_transcript": "NOT_STARTED",
    })

    summary = summarize_probe_start_response(response, http_status="202", curl_exit=0)

    assert summary == {
        "schema_version": ACCESS_BRIDGE_SCHEMA,
        "transport": "OK",
        "result": "HISTORY_PROBE_REQUESTED",
    }
    _write(response, summary)
    assert probe_start_poll_state(response) == "POLL"

    _write(response, {"state": "REQUESTED", "opaque_request_id": "must-not-escape"})
    malformed = summarize_probe_start_response(response, http_status="202", curl_exit=0)
    assert malformed["result"] == "HISTORY_PROBE_START_INVALID_RESPONSE"
    assert "must-not-escape" not in json.dumps(malformed)


def test_bridge_manager_writes_private_material_and_only_prints_finite_receipt(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manager = _load_script()
    envs, access_apps = _target_inputs(tmp_path)
    target = tmp_path / "target.env"
    assert manager.main([
        "resolve-target", "--coolify-env", str(envs), "--access-apps", str(access_apps), "--output", str(target),
    ]) == 0
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert "kmfa.example.com" in target.read_text(encoding="utf-8")
    assert capsys.readouterr().out == ""

    response = tmp_path / "probe.json"
    _write(response, _valid_probe())
    assert manager.main([
        "summarize-probe", "--response", str(response), "--http-status", "200", "--curl-exit", "0",
    ]) == 0
    output = capsys.readouterr().out
    assert json.loads(output)["result"] == "HISTORY_PROBE_COMPLETED"
    assert "kmfa.example.com" not in output
    assert "service-secret" not in output


def test_workflow_bridge_is_manual_main_only_fixed_route_and_cleanup_scoped() -> None:
    workflow = (ROOT.parents[2] / ".github" / "workflows" / "coolify-ops.yml").read_text(encoding="utf-8")
    start = workflow.index("受控触发每日资金固定历史探针")
    end = workflow.find("\n      - name:", start + 1)
    step = workflow[start:] if end == -1 else workflow[start:end]

    assert "inputs.mode == 'daily-funds-history-probe-bridge'" in step
    assert 'GITHUB_REF:-}" = "refs/heads/main"' in step
    assert "access/service_tokens" in step
    assert "/access/apps/${CF_ACCESS_APP_ID}/policies" in step
    assert "CF-Access-Client-Secret" in step
    assert '"$PROBE_ORIGIN/ops/api/daily-funds/history-probe"' in step
    assert "capture-service-token-id" in step
    assert "capture-policy" in step
    assert "summarize-probe-start" in step
    assert "probe-start-poll-state" in step
    assert "sleep 10" in step
    assert '"$REQUEST_STATUS" = "200" ] && ! python3' in step
    assert "204 has no JSON body" in step
    assert "request_cf DELETE" in step
    assert "duration" not in step  # duration is fixed in the Python allowlist, not workflow input.
    assert "inputs.command" not in step
    assert "--data @\"$payload\"" in step
    assert "rm -rf" not in step
