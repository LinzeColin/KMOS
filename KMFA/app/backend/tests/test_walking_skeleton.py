"""S03/P3.4 TEST-QA-001 focused contract tests."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from app import walking_skeleton as skeleton
from app.main import app

client = TestClient(app)
BASE = "/public-api/walking-skeleton/v1"


@pytest.fixture
def enabled_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    state = tmp_path / "walking-state"
    monkeypatch.setenv("KMFA_WALKING_SKELETON_ENABLED", "1")
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(state))
    monkeypatch.delenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", raising=False)
    return state


def _create(project_name: str = "合成骨架项目") -> dict:
    response = client.post(f"{BASE}/workspaces", json={"project_name": project_name})
    assert response.status_code == 201, response.text
    payload = response.json()
    assert "access_token" not in payload
    payload["_session_token"] = response.cookies.get(skeleton.SESSION_COOKIE_NAME)
    assert skeleton.ACCESS_TOKEN_RE.fullmatch(payload["_session_token"])
    return payload


def _auth(created: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {created['_session_token']}"}


def _response_payload(response) -> dict:
    payload = response.json()
    assert "access_token" not in payload
    payload["_session_token"] = response.cookies.get(skeleton.SESSION_COOKIE_NAME)
    assert skeleton.ACCESS_TOKEN_RE.fullmatch(payload["_session_token"])
    return payload


def _upload(created: dict, content: bytes, name: str = "fixture.unknown"):
    workspace_id = created["workspace"]["workspace_id"]
    return client.put(
        f"{BASE}/workspaces/{workspace_id}/artifact",
        content=content,
        headers={
            **_auth(created),
            "X-KMFA-Filename": quote(name, safe=""),
            "Content-Type": "application/x-kmfa-unknown",
        },
    )


def test_flag_defaults_and_typos_fail_closed_without_creating_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    state = tmp_path / "must-not-exist"
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(state))
    for value in (None, "", "enable-ish", "truthy"):
        if value is None:
            monkeypatch.delenv("KMFA_WALKING_SKELETON_ENABLED", raising=False)
        else:
            monkeypatch.setenv("KMFA_WALKING_SKELETON_ENABLED", value)
        status = client.get(f"{BASE}/status")
        assert status.status_code == 200
        assert status.json() == {
            "enabled": False,
            "mode": "rollback",
            "preserves_existing_data": True,
            "stage_status": "early-skeleton-not-ga",
        }
        assert (
            client.post(f"{BASE}/workspaces", json={"project_name": "no"}).status_code
            == 404
        )
    assert not state.exists()


def test_enabled_status_is_honest_about_adapter_limits_and_hardening(enabled_store):
    payload = client.get(f"{BASE}/status").json()
    assert payload["enabled"] is True and payload["healthy"] is True
    assert payload["browser_storage"] is False
    assert payload["structured_store"] == "sqlite-durable-volume-adapter"
    assert payload["artifact_store"] == "private-filesystem-volume-adapter"
    assert payload["limits"] == {
        "max_artifacts": 1,
        "max_bytes": 8 * 1024 * 1024,
        "max_total_artifact_bytes": 512 * 1024 * 1024,
        "min_free_state_bytes": 128 * 1024 * 1024,
        "max_workspaces_total": 10_000,
        "max_active_sessions_per_workspace": 8,
        "max_audit_events_per_workspace": 10_000,
        "max_audit_events_total": 250_000,
        "file_types": "any-stored-attachment-only",
    }
    assert payload["abuse_control"]["policy_version"] == "p44-v1"
    assert payload["abuse_control"]["login_required"] is False
    assert payload["abuse_control"]["public_browse_exempt"] is True
    assert payload["stage_status"] == "early-skeleton-not-ga"
    assert "s3-compatible-object-store" in payload["hardening_pending"]
    assert "abuse-and-malware-controls" not in payload["hardening_pending"]


def test_unavailable_state_path_is_a_clear_503(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("synthetic blocker", encoding="utf-8")
    monkeypatch.setenv("KMFA_WALKING_SKELETON_ENABLED", "1")
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(blocked))
    status = client.get(f"{BASE}/status")
    created = client.post(f"{BASE}/workspaces", json={"project_name": "blocked"})
    assert status.status_code == 503
    assert created.status_code == 503
    assert status.json()["detail"] == "walking_skeleton_storage_unavailable"
    assert created.json()["detail"] == "walking_skeleton_storage_unavailable"


def test_create_returns_one_time_recovery_and_stores_only_capability_hashes(
    enabled_store: Path,
):
    created = _create()
    recovery = created["recovery_code"]
    access = created["_session_token"]
    assert skeleton.RECOVERY_CODE_RE.fullmatch(recovery)
    assert skeleton.ACCESS_TOKEN_RE.fullmatch(access)
    assert "access_token" not in created
    assert created["recovery_code_shown_once"] is True
    assert created["workspace"]["progress"] == 0
    assert created["workspace"]["artifact"] is None

    state_bytes = b"".join(
        path.read_bytes() for path in enabled_store.rglob("*") if path.is_file()
    )
    assert recovery.encode() not in state_bytes
    assert access.encode() not in state_bytes

    connection = sqlite3.connect(enabled_store / "walking_skeleton.sqlite3")
    try:
        recovery_hash = connection.execute(
            "SELECT recovery_hash FROM workspaces"
        ).fetchone()[0]
        token_hash = connection.execute(
            "SELECT token_hash FROM access_tokens"
        ).fetchone()[0]
    finally:
        connection.close()
    assert recovery_hash == hashlib.sha256(recovery.encode("ascii")).hexdigest()
    assert token_hash == hashlib.sha256(access.encode("ascii")).hexdigest()


def test_project_and_progress_save_require_the_ephemeral_capability(enabled_store):
    created = _create()
    workspace_id = created["workspace"]["workspace_id"]
    update = client.patch(
        f"{BASE}/workspaces/{workspace_id}",
        headers=_auth(created),
        json={"project_name": "已保存项目", "progress": 37},
    )
    assert update.status_code == 200
    assert update.json()["project_name"] == "已保存项目"
    assert update.json()["progress"] == 37
    assert client.get(f"{BASE}/workspaces/{workspace_id}").status_code == 404
    assert (
        client.get(
            f"{BASE}/workspaces/{workspace_id}",
            headers={"Authorization": "Bearer kmfa-a1-" + "x" * 43},
        ).status_code
        == 404
    )


def test_arbitrary_binary_is_outside_db_and_downloads_attachment_with_same_hash(
    enabled_store: Path,
):
    created = _create()
    content = b"\x00KMFA\xff\nsynthetic binary\x00" * 97
    uploaded = _upload(created, content, "合成样本.double.exe.unknown")
    assert uploaded.status_code == 200, uploaded.text
    artifact = uploaded.json()["artifact"]
    expected_hash = hashlib.sha256(content).hexdigest()
    assert artifact["sha256"] == expected_hash
    assert artifact["download_mode"] == "attachment-only"

    database = enabled_store / "walking_skeleton.sqlite3"
    assert content not in database.read_bytes()
    object_files = list((enabled_store / "objects").glob("*.blob"))
    assert len(object_files) == 1 and object_files[0].read_bytes() == content
    assert object_files[0].stat().st_mode & 0o777 == 0o600

    workspace_id = created["workspace"]["workspace_id"]
    downloaded = client.post(
        f"{BASE}/workspaces/{workspace_id}/artifact/download",
        headers=_auth(created),
    )
    assert downloaded.status_code == 200 and downloaded.content == content
    assert downloaded.headers["x-kmfa-artifact-sha256"] == expected_hash
    assert downloaded.headers["x-kmfa-artifact-mode"] == "attachment-only"
    assert downloaded.headers["x-content-type-options"] == "nosniff"
    assert downloaded.headers["content-type"].startswith("application/octet-stream")
    assert downloaded.headers["content-disposition"].startswith("attachment;")
    assert downloaded.headers["cache-control"] == "private, no-store"
    assert downloaded.headers["x-robots-tag"] == "noindex, nofollow, noarchive"


def test_recovery_issues_a_new_short_session_and_never_repeats_the_code(enabled_store):
    created = _create("重启后恢复")
    _upload(created, b"restart-persistent", "restart.fixture")
    workspace_id = created["workspace"]["workspace_id"]
    client.patch(
        f"{BASE}/workspaces/{workspace_id}",
        headers=_auth(created),
        json={"progress": 64},
    )

    recovered = client.post(
        f"{BASE}/recoveries",
        json={"recovery_code": created["recovery_code"]},
    )
    assert recovered.status_code == 200
    payload = _response_payload(recovered)
    assert payload["_session_token"] != created["_session_token"]
    assert payload["workspace"]["workspace_id"] == workspace_id
    assert payload["workspace"]["progress"] == 64
    assert (
        payload["workspace"]["artifact"]["sha256"]
        == hashlib.sha256(b"restart-persistent").hexdigest()
    )
    assert payload["recovery_code_shown_once"] is False
    assert "recovery_code" not in payload


def test_rollback_disables_actions_but_preserves_and_can_restore_data(
    enabled_store: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    created = _create()
    content = b"preserve-through-rollback"
    _upload(created, content)
    before = {
        path.relative_to(enabled_store): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in enabled_store.rglob("*")
        if path.is_file() and path.suffix == ".blob"
    }

    monkeypatch.setenv("KMFA_WALKING_SKELETON_ENABLED", "0")
    assert client.get(f"{BASE}/status").json()["mode"] == "rollback"
    assert (
        client.post(
            f"{BASE}/recoveries",
            json={"recovery_code": created["recovery_code"]},
        ).status_code
        == 404
    )
    after = {
        path.relative_to(enabled_store): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in enabled_store.rglob("*")
        if path.is_file() and path.suffix == ".blob"
    }
    assert after == before

    monkeypatch.setenv("KMFA_WALKING_SKELETON_ENABLED", "1")
    recovered = client.post(
        f"{BASE}/recoveries",
        json={"recovery_code": created["recovery_code"]},
    )
    recovered_payload = _response_payload(recovered)
    downloaded = client.post(
        f"{BASE}/workspaces/{recovered_payload['workspace']['workspace_id']}/artifact/download",
        headers=_auth(recovered_payload),
    )
    assert downloaded.content == content


def test_second_artifact_oversize_and_path_filename_fail_without_orphans(
    enabled_store: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    created = _create()
    traversal = _upload(created, b"x", "../../escape.bin")
    assert traversal.status_code == 422
    assert not list((enabled_store / "objects").glob("*.blob"))

    monkeypatch.setattr(skeleton, "MAX_ARTIFACT_BYTES", 4)
    oversized = _upload(created, b"12345", "large.bin")
    assert oversized.status_code == 413
    assert not list((enabled_store / "objects").glob("*.blob"))
    assert not list((enabled_store / "tmp").glob("*.part"))

    monkeypatch.setattr(skeleton, "MAX_ARTIFACT_BYTES", 8 * 1024 * 1024)
    assert _upload(created, b"first").status_code == 200
    assert _upload(created, b"second", "second.bin").status_code == 409
    assert len(list((enabled_store / "objects").glob("*.blob"))) == 1


def test_integrity_failure_is_fail_closed(enabled_store: Path):
    created = _create()
    assert _upload(created, b"original").status_code == 200
    object_path = next((enabled_store / "objects").glob("*.blob"))
    object_path.write_bytes(b"tampered")
    workspace_id = created["workspace"]["workspace_id"]
    response = client.post(
        f"{BASE}/workspaces/{workspace_id}/artifact/download",
        headers=_auth(created),
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "artifact_integrity_failed"


def test_audit_is_append_only_and_contains_actions_not_file_content(
    enabled_store: Path,
):
    created = _create()
    content = b"private synthetic bytes must not be audited"
    _upload(created, content)
    workspace_id = created["workspace"]["workspace_id"]
    client.patch(
        f"{BASE}/workspaces/{workspace_id}",
        headers=_auth(created),
        json={"progress": 10},
    )
    client.post(
        f"{BASE}/workspaces/{workspace_id}/artifact/download",
        headers=_auth(created),
    )
    recovered_response = client.post(
        f"{BASE}/recoveries", json={"recovery_code": created["recovery_code"]}
    )
    recovered = _response_payload(recovered_response)
    audit = client.get(
        f"{BASE}/workspaces/{workspace_id}/audit-events",
        headers=_auth(recovered),
    ).json()
    actions = [event["action"] for event in audit["events"]]
    assert audit["append_only"] is True
    assert actions == [
        "workspace_created",
        "artifact_uploaded",
        "workspace_saved",
        "artifact_download",
        "workspace_recovered",
    ]
    assert content not in str(audit).encode()

    connection = sqlite3.connect(enabled_store / "walking_skeleton.sqlite3")
    try:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE audit_events SET action='rewritten' WHERE seq=1")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("DELETE FROM audit_events WHERE seq=1")
    finally:
        connection.close()


def test_gets_do_not_mutate_business_or_audit_rows(enabled_store: Path):
    created = _create()
    workspace_id = created["workspace"]["workspace_id"]
    connection = sqlite3.connect(enabled_store / "walking_skeleton.sqlite3")
    try:
        before = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("workspaces", "artifacts", "access_tokens", "audit_events")
        }
    finally:
        connection.close()
    assert client.get(f"{BASE}/status").status_code == 200
    assert (
        client.get(
            f"{BASE}/workspaces/{workspace_id}", headers=_auth(created)
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"{BASE}/workspaces/{workspace_id}/audit-events", headers=_auth(created)
        ).status_code
        == 200
    )
    connection = sqlite3.connect(enabled_store / "walking_skeleton.sqlite3")
    try:
        after = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in before
        }
    finally:
        connection.close()
    assert after == before


def test_public_skeleton_stays_outside_private_ops_guard(
    enabled_store: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", "1")
    monkeypatch.delenv("KMFA_CLOUDFLARE_ACCESS_TEAM_DOMAIN", raising=False)
    monkeypatch.delenv("KMFA_CLOUDFLARE_ACCESS_AUD", raising=False)
    assert client.get(f"{BASE}/status").status_code == 200
    assert _create()["workspace"]["workspace_id"].startswith("ws_")
    assert client.get("/api/状态").status_code == 503


def test_public_responses_are_noindex_no_store_and_objects_have_no_public_route(
    enabled_store: Path,
):
    status = client.get(f"{BASE}/status")
    assert status.headers["cache-control"] == "private, no-store"
    assert status.headers["x-robots-tag"] == "noindex, nofollow, noarchive"
    created = _create()
    _upload(created, b"not-public")
    object_name = next((enabled_store / "objects").glob("*.blob")).name
    assert client.get(f"{BASE}/objects/{object_name}").status_code == 404
    assert client.get(f"/assets/{object_name}").status_code == 404


def test_expired_access_session_requires_recovery(enabled_store: Path):
    created = _create()
    workspace_id = created["workspace"]["workspace_id"]
    connection = sqlite3.connect(enabled_store / "walking_skeleton.sqlite3")
    try:
        connection.execute("UPDATE access_tokens SET expires_at='2000-01-01T00:00:00Z'")
        connection.commit()
    finally:
        connection.close()
    assert (
        client.get(
            f"{BASE}/workspaces/{workspace_id}", headers=_auth(created)
        ).status_code
        == 404
    )
    recovered = client.post(
        f"{BASE}/recoveries", json={"recovery_code": created["recovery_code"]}
    )
    assert recovered.status_code == 200


def test_deployment_defaults_off_and_mounts_a_named_state_volume():
    app_root = Path(__file__).resolve().parents[2]
    kmfa_root = app_root.parent
    local_compose = (app_root / "docker-compose.yml").read_text(encoding="utf-8")
    coolify_compose = (kmfa_root / "deploy/coolify/docker-compose.yml").read_text(
        encoding="utf-8"
    )
    env_example = (kmfa_root / "deploy/coolify/.env.example").read_text(
        encoding="utf-8"
    )
    runbook = (kmfa_root / "deploy/coolify/README.md").read_text(encoding="utf-8")
    for compose in (local_compose, coolify_compose):
        assert "KMFA_WALKING_SKELETON_ENABLED:-0" in compose
        assert "KMFA_ABUSE_POLICY_MODE:-enforced" in compose
        assert "kmfa-app-state:/var/lib/kmfa/state" in compose
        assert "kmfa-app-state:" in compose
    assert "KMFA_WALKING_SKELETON_ENABLED=0" in env_example
    assert "KMFA_ABUSE_POLICY_MODE=enforced" in env_example
    assert "重启" in runbook and "SHA-256" in runbook
    assert "Flag" in runbook and "禁止使用 `docker compose down -v`" in runbook
