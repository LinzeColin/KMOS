"""Safety contracts for the values-free Cloudflare Access audit candidate."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from daily_funds.access_audit import ACCESS_AUDIT_SCHEMA, summarize_access_audit


def _write_reply(path: Path, result: object, *, secret: str = "") -> None:
    path.write_text(
        json.dumps({"success": True, "result": result, "errors": [{"message": secret}]}),
        encoding="utf-8",
    )


def _responses(tmp_path: Path, *, secret: str) -> dict[str, tuple[Path, str, int]]:
    token_verify = tmp_path / "token-verify.json"
    apps = tmp_path / "apps.json"
    service_tokens = tmp_path / "service-tokens.json"
    policies = tmp_path / "policies.json"
    _write_reply(token_verify, {"id": secret}, secret=secret)
    _write_reply(apps, [{"id": secret}], secret=secret)
    _write_reply(service_tokens, [{"client_id": secret}], secret=secret)
    _write_reply(policies, [{"id": secret}], secret=secret)
    return {
        "token_verify": (token_verify, "200", 0),
        "apps_read": (apps, "200", 0),
        "service_tokens_read": (service_tokens, "200", 0),
        "policies_read": (policies, "200", 0),
    }


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "cloudflare_access_audit_summary_test",
        ROOT / "scripts" / "summarize_cloudflare_access_audit.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_access_audit_is_values_free_even_when_provider_reply_contains_sensitive_fields(tmp_path: Path) -> None:
    secret = "never-print-provider-response-value"
    summary = summarize_access_audit(_responses(tmp_path, secret=secret))
    rendered = json.dumps(summary, ensure_ascii=False)

    assert summary == {
        "schema_version": ACCESS_AUDIT_SCHEMA,
        "checks": {
            "token_verify": "OK",
            "apps_read": "OK",
            "service_tokens_read": "OK",
            "policies_read": "OK",
        },
        "read_capability": "VERIFIED",
        "request_scope": "GET_ONLY_NO_CLOUDFLARE_MUTATION",
        "service_auth_write_scope": "UNKNOWN_NOT_TESTED",
    }
    assert secret not in rendered


@pytest.mark.parametrize(
    ("http_status", "curl_exit", "expected"),
    (("403", 0, "DENIED"), ("429", 0, "UNAVAILABLE"), ("200", 28, "TRANSPORT_FAILED")),
)
def test_access_audit_fails_closed_for_denied_unavailable_or_transport_response(
    tmp_path: Path,
    http_status: str,
    curl_exit: int,
    expected: str,
) -> None:
    response = tmp_path / "response.json"
    _write_reply(response, {"id": "private"})
    summary = summarize_access_audit({"token_verify": (response, http_status, curl_exit)})

    assert summary["checks"]["token_verify"] == expected
    assert summary["read_capability"] == "NOT_VERIFIED"
    assert summary["service_auth_write_scope"] == "UNKNOWN_NOT_TESTED"


def test_access_audit_script_never_echoes_the_ephemeral_response(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    secret = "access-response-must-not-reach-actions-log"
    responses = _responses(tmp_path, secret=secret)
    argv: list[str] = []
    for check, (path, http_status, curl_exit) in responses.items():
        argv.extend(("--response", check, http_status, str(curl_exit), str(path)))
    assert _load_script().main(argv) == 0
    output = capsys.readouterr().out

    assert json.loads(output)["read_capability"] == "VERIFIED"
    assert secret not in output


def test_coolify_workflow_audit_is_manual_get_only_and_uses_the_values_free_summary() -> None:
    workflow = (ROOT.parents[2] / ".github" / "workflows" / "coolify-ops.yml").read_text(encoding="utf-8")
    start = workflow.index("只读核对每日资金 Cloudflare Access 能力")
    end = workflow.find("\n      - name:", start + 1)
    audit_step = workflow[start:] if end == -1 else workflow[start:end]

    assert "inputs.mode == 'daily-funds-access-audit'" in audit_step
    assert 'GITHUB_REF:-}" = "refs/heads/main"' in audit_step
    assert "--request GET" in audit_step
    assert "summarize_cloudflare_access_audit.py" in audit_step
    assert "service_tokens" in audit_step
    assert "policies" in audit_step
    assert "-X POST" not in audit_step
    assert "-X PATCH" not in audit_step
    assert "-X DELETE" not in audit_step
