"""S04/P4.3 AC-WS-003 secret hygiene and revocable-session contract."""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import walking_skeleton as skeleton
from app.main import app
from app.secret_hygiene import CONTENT_SECURITY_POLICY, REDACTED, redact_secrets

BASE = "/public-api/walking-skeleton/v1"
RECOVERY_CANARY = "kmfa-r1-" + ("R" * 43)
ACCESS_CANARY = "kmfa-a1-" + ("A" * 43)
DEVICE_CANARY = "kmfa-d1-" + ("D" * 22)


@pytest.fixture
def hygiene_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    state = tmp_path / "secret-hygiene"
    monkeypatch.setenv("KMFA_WALKING_SKELETON_ENABLED", "1")
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(state))
    monkeypatch.delenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", raising=False)
    return state


@pytest.fixture
def secure_client(hygiene_store: Path):
    del hygiene_store
    with TestClient(
        app,
        base_url="https://kmfa.test",
        headers={"Origin": "https://kmfa.test"},
    ) as client:
        yield client


def _create(client: TestClient) -> tuple[dict, str, str]:
    response = client.post(
        f"{BASE}/workspaces",
        json={"project_name": "P4.3 synthetic secret hygiene"},
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert "access_token" not in payload
    session_token = response.cookies.get(skeleton.SESSION_COOKIE_NAME)
    assert skeleton.ACCESS_TOKEN_RE.fullmatch(session_token)
    return payload, session_token, response.headers["set-cookie"]


def _clear_client_cookies(client: TestClient) -> None:
    client.cookies.clear()


def test_browser_session_is_protected_cookie_only_and_same_origin_authorizes(
    secure_client: TestClient,
):
    payload, session_token, set_cookie = _create(secure_client)
    workspace_id = payload["workspace"]["workspace_id"]
    lowered = set_cookie.lower()

    assert set_cookie.startswith(f"{skeleton.SESSION_COOKIE_NAME}=")
    assert "httponly" in lowered
    assert "secure" in lowered
    assert "samesite=strict" in lowered
    assert f"path={BASE}".lower() in lowered
    assert "max-age=3600" in lowered
    assert "domain=" not in lowered
    assert session_token not in json.dumps(payload)
    assert payload["session_transport"] == "secure-http-only-cookie"
    assert payload["session_revocable"] is True

    workspace = secure_client.get(f"{BASE}/workspaces/{workspace_id}")
    assert workspace.status_code == 200
    assert workspace.json()["workspace_id"] == workspace_id
    assert workspace.headers["cache-control"] == "private, no-store"
    assert "cookie" in workspace.headers["vary"].lower()


def test_explicit_revocation_clears_cookie_and_old_bearer_replay_fails(
    hygiene_store: Path,
    secure_client: TestClient,
):
    payload, session_token, _ = _create(secure_client)
    workspace_id = payload["workspace"]["workspace_id"]

    revoked = secure_client.delete(f"{BASE}/sessions/current")
    assert revoked.status_code == 204
    assert revoked.headers["x-kmfa-session-transport"] == "revoked"
    cleared = revoked.headers["set-cookie"].lower()
    assert "max-age=0" in cleared
    assert "httponly" in cleared
    assert "secure" in cleared
    assert "samesite=strict" in cleared

    _clear_client_cookies(secure_client)
    replay = secure_client.get(
        f"{BASE}/workspaces/{workspace_id}",
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert replay.status_code == 404
    assert session_token not in replay.text

    connection = sqlite3.connect(hygiene_store / "walking_skeleton.sqlite3")
    try:
        token_count = connection.execute(
            "SELECT COUNT(*) FROM access_tokens WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()[0]
        actions = [
            row[0]
            for row in connection.execute(
                "SELECT action FROM audit_events WHERE workspace_id = ? ORDER BY seq",
                (workspace_id,),
            )
        ]
    finally:
        connection.close()
    assert token_count == 0
    assert actions == ["workspace_created", "workspace_session_revoked"]


def test_conflicting_cookie_and_bearer_revocation_fails_closed(
    secure_client: TestClient,
):
    created, first_token, _ = _create(secure_client)
    workspace_id = created["workspace"]["workspace_id"]
    exchanged = secure_client.post(
        f"{BASE}/sessions",
        json={
            "workspace_id": workspace_id,
            "workspace_secret": created["recovery_code"],
        },
    )
    second_token = exchanged.cookies.get(skeleton.SESSION_COOKIE_NAME)
    assert exchanged.status_code == 200
    assert skeleton.ACCESS_TOKEN_RE.fullmatch(second_token)
    assert second_token != first_token

    cross_origin = secure_client.delete(
        f"{BASE}/sessions/current",
        headers={"Origin": "https://sibling.kmfa.test"},
    )
    assert cross_origin.status_code == 403
    assert cross_origin.json() == {
        "detail": "cross_origin_session_request_rejected"
    }
    assert "set-cookie" not in cross_origin.headers

    conflict = secure_client.delete(
        f"{BASE}/sessions/current",
        headers={"Authorization": f"Bearer {first_token}"},
    )
    assert conflict.status_code == 404
    assert conflict.json() == {"detail": "workspace_not_found"}
    assert "set-cookie" not in conflict.headers

    _clear_client_cookies(secure_client)
    for token in (first_token, second_token):
        assert (
            secure_client.get(
                f"{BASE}/workspaces/{workspace_id}",
                headers={"Authorization": f"Bearer {token}"},
            ).status_code
            == 200
        )


def test_secret_rotation_revokes_every_old_session_and_issues_one_replacement(
    hygiene_store: Path,
    secure_client: TestClient,
):
    created, first_token, _ = _create(secure_client)
    workspace_id = created["workspace"]["workspace_id"]
    workspace_secret = created["recovery_code"]

    exchanged = secure_client.post(
        f"{BASE}/sessions",
        json={
            "workspace_id": workspace_id,
            "workspace_secret": workspace_secret,
        },
    )
    assert exchanged.status_code == 200
    second_token = exchanged.cookies.get(skeleton.SESSION_COOKIE_NAME)
    assert skeleton.ACCESS_TOKEN_RE.fullmatch(second_token)
    assert second_token != first_token
    assert "access_token" not in exchanged.json()

    rotated = secure_client.post(
        f"{BASE}/workspaces/{workspace_id}/recovery-secret/rotate"
    )
    assert rotated.status_code == 200, rotated.text
    rotation = rotated.json()
    replacement_token = rotated.cookies.get(skeleton.SESSION_COOKIE_NAME)
    assert skeleton.ACCESS_TOKEN_RE.fullmatch(replacement_token)
    assert replacement_token not in {first_token, second_token}
    assert "access_token" not in rotation
    assert rotation["existing_sessions_revoked"] is True
    assert rotation["revoked_session_count"] == 2

    _clear_client_cookies(secure_client)
    for old_token in (first_token, second_token):
        replay = secure_client.get(
            f"{BASE}/workspaces/{workspace_id}",
            headers={"Authorization": f"Bearer {old_token}"},
        )
        assert replay.status_code == 404
        assert old_token not in replay.text
    replacement = secure_client.get(
        f"{BASE}/workspaces/{workspace_id}",
        headers={"Authorization": f"Bearer {replacement_token}"},
    )
    assert replacement.status_code == 200

    connection = sqlite3.connect(hygiene_store / "walking_skeleton.sqlite3")
    try:
        token_count = connection.execute(
            "SELECT COUNT(*) FROM access_tokens WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()[0]
        actions = [
            row[0]
            for row in connection.execute(
                "SELECT action FROM audit_events WHERE workspace_id = ? ORDER BY seq",
                (workspace_id,),
            )
        ]
    finally:
        connection.close()
    assert token_count == 1
    assert actions == [
        "workspace_created",
        "workspace_session_exchanged",
        "workspace_sessions_revoked",
        "workspace_secret_rotated",
    ]


def test_url_path_query_referer_and_errors_never_echo_recovery_canary(
    secure_client: TestClient,
):
    status = secure_client.get(f"{BASE}/status")
    assert status.status_code == 200
    assert status.headers["content-security-policy"] == CONTENT_SECURITY_POLICY
    assert status.headers["referrer-policy"] == "no-referrer"
    assert status.headers["x-kmfa-secret-hygiene"] == "enforced"
    assert status.headers["strict-transport-security"].startswith("max-age=31536000")
    assert "connect-src 'self'" in status.headers["content-security-policy"]
    assert status.json()["secret_hygiene"] == {
        "session_transport": "secure-http-only-cookie",
        "cookie": {
            "name": skeleton.SESSION_COOKIE_NAME,
            "secure": True,
            "http_only": True,
            "same_site": "Strict",
            "path": BASE,
            "max_age_seconds": 3600,
        },
        "revocation": f"{BASE}/sessions/current",
        "legacy_bearer_compatible_until_expiry": True,
        "browser_receives_access_token": False,
        "same_origin_cookie_mutations_required": True,
        "runtime_telemetry": "none",
    }

    query_rejected = secure_client.get(
        f"{BASE}/status",
        params={"workspace_secret": RECOVERY_CANARY},
    )
    referer_rejected = secure_client.get(
        f"{BASE}/status",
        headers={"Referer": f"https://outside.invalid/?secret={RECOVERY_CANARY}"},
    )
    encoded_canary = RECOVERY_CANARY.replace("-", "%2D")
    encoded_rejected = secure_client.get(
        f"{BASE}/status?workspace_secret={encoded_canary}"
    )
    double_encoded_canary = encoded_canary.replace("%", "%25")
    double_encoded_rejected = secure_client.get(
        f"{BASE}/status?workspace_secret={double_encoded_canary}"
    )
    path_rejected = secure_client.get(f"{BASE}/{RECOVERY_CANARY}")
    encoded_path_rejected = secure_client.get(f"{BASE}/{encoded_canary}")
    double_encoded_path_rejected = secure_client.get(
        f"{BASE}/{double_encoded_canary}"
    )
    invalid_recovery = secure_client.post(
        f"{BASE}/recoveries",
        json={"recovery_code": RECOVERY_CANARY},
    )
    overlong_canary = f"{RECOVERY_CANARY}X"
    invalid_schema = secure_client.post(
        f"{BASE}/recoveries",
        json={"recovery_code": overlong_canary},
    )
    for response in (
        query_rejected,
        referer_rejected,
        encoded_rejected,
        double_encoded_rejected,
        path_rejected,
        encoded_path_rejected,
        double_encoded_path_rejected,
    ):
        assert response.status_code == 400
        assert response.json() == {"detail": "secret_in_url_rejected"}
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert response.headers["x-robots-tag"] == "noindex, nofollow, noarchive"
    assert invalid_recovery.status_code == 404
    assert invalid_recovery.json() == {"detail": "recovery_not_found"}
    assert invalid_schema.status_code == 422
    assert invalid_schema.json() == {"detail": "request_validation_failed"}
    assert overlong_canary not in invalid_schema.text
    assert all(
        RECOVERY_CANARY not in response.text
        for response in (
            query_rejected,
            referer_rejected,
            encoded_rejected,
            double_encoded_rejected,
            path_rejected,
            encoded_path_rejected,
            double_encoded_path_rejected,
            invalid_recovery,
            invalid_schema,
        )
    )

    created, _, _ = _create(secure_client)
    workspace_id = created["workspace"]["workspace_id"]
    events = secure_client.get(f"{BASE}/workspaces/{workspace_id}/audit-events")
    assert events.status_code == 200
    assert RECOVERY_CANARY not in events.text
    assert created["recovery_code"] not in events.text
    assert events.headers["cache-control"] == "private, no-store"


def test_process_log_redaction_removes_capabilities_assignments_and_exceptions(
    caplog: pytest.LogCaptureFixture,
):
    logger = logging.getLogger("kmfa.secret-hygiene-test")
    with caplog.at_level(logging.INFO, logger=logger.name):
        logger.info(
            "recovery=%s bearer=%s session_cookie=%s device_cookie=%s",
            RECOVERY_CANARY,
            f"Bearer {ACCESS_CANARY}",
            f"{skeleton.SESSION_COOKIE_NAME}={ACCESS_CANARY}",
            f"__Host-kmfa_device={DEVICE_CANARY}",
        )
        try:
            raise RuntimeError(
                f"workspace_secret={RECOVERY_CANARY} access_token={ACCESS_CANARY}"
            )
        except RuntimeError:
            logger.exception("synthetic capability error")

    rendered = caplog.text
    assert RECOVERY_CANARY not in rendered
    assert ACCESS_CANARY not in rendered
    assert DEVICE_CANARY not in rendered
    assert REDACTED in rendered
    assert RECOVERY_CANARY not in redact_secrets(
        f'{{"workspace_secret":"{RECOVERY_CANARY}"}}'
    )
    encoded_canary = RECOVERY_CANARY.replace("-", "%2D")
    assert encoded_canary not in redact_secrets(
        f"https://kmfa.test/?workspace_secret={encoded_canary}"
    )
    double_encoded_canary = encoded_canary.replace("%", "%25")
    assert double_encoded_canary not in redact_secrets(
        f"https://kmfa.test/?workspace_secret={double_encoded_canary}"
    )


def test_no_runtime_telemetry_dependency_and_raw_access_log_is_disabled():
    app_root = Path(__file__).resolve().parents[2]
    frontend_root = app_root / "frontend"
    package = json.loads((frontend_root / "package.json").read_text(encoding="utf-8"))
    dependency_names = {
        *package.get("dependencies", {}),
        *package.get("devDependencies", {}),
    }
    forbidden_dependencies = {
        "@sentry/browser",
        "@sentry/react",
        "@segment/analytics-next",
        "mixpanel-browser",
        "posthog-js",
        "amplitude-js",
        "newrelic",
    }
    assert dependency_names.isdisjoint(forbidden_dependencies)

    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((frontend_root / "src").rglob("*"))
        if path.is_file() and path.suffix in {".js", ".jsx", ".ts", ".tsx"}
    ).lower()
    for marker in (
        "sentry.init",
        "mixpanel.init",
        "posthog.init",
        "analytics.load",
        "gtag(",
        "newrelic",
    ):
        assert marker not in source_text

    main_source = (frontend_root / "src" / "main.jsx").read_text(encoding="utf-8")
    assert "[REDACTED_KMFA_CAPABILITY]" in main_source
    assert "values.map(redactBrowserDiagnostic)" in main_source

    dockerfile = (app_root / "backend" / "Dockerfile").read_text(encoding="utf-8")
    assert "--no-access-log" in dockerfile
    assert "--proxy-headers" in dockerfile
    assert '"--forwarded-allow-ips", "*"' in dockerfile
