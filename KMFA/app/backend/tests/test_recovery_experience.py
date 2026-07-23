"""S04/P4.2 AC-WS-002 recovery file and secret-rotation contract."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import walking_skeleton as recovery
from app.main import app

client = TestClient(app)
BASE = "/public-api/walking-skeleton/v1"
MEDIA_TYPE = "application/vnd.kmfa.recovery+json"


@pytest.fixture
def recovery_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    state = tmp_path / "recovery-experience"
    monkeypatch.setenv("KMFA_WALKING_SKELETON_ENABLED", "1")
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(state))
    monkeypatch.delenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", raising=False)
    return state


def _create(project_name: str = "P4.2 synthetic recovery") -> dict[str, object]:
    response = client.post(f"{BASE}/workspaces", json={"project_name": project_name})
    assert response.status_code == 201, response.text
    return response.json()


def _auth(payload: dict[str, object]) -> dict[str, str]:
    return {"Authorization": f"Bearer {payload['access_token']}"}


def _export(payload: dict[str, object]):
    workspace = payload["workspace"]
    assert isinstance(workspace, dict)
    return client.post(
        f"{BASE}/workspaces/{workspace['workspace_id']}/recovery-file",
        headers=_auth(payload),
        json={"workspace_secret": payload["recovery_code"]},
    )


def _import(payload: bytes):
    return client.post(
        f"{BASE}/recovery-files/import",
        content=payload,
        headers={"Content-Type": MEDIA_TYPE},
    )


def _upload(
    payload: dict[str, object],
    content: bytes,
    filename: str = "p42.synthetic.unknown",
):
    workspace = payload["workspace"]
    assert isinstance(workspace, dict)
    return client.put(
        f"{BASE}/workspaces/{workspace['workspace_id']}/artifact",
        headers={
            **_auth(payload),
            "Content-Type": "application/x-kmfa-synthetic",
            "X-KMFA-Filename": filename,
        },
        content=content,
    )


def test_strict_recovery_file_round_trip_preserves_full_workspace_inventory(
    recovery_store: Path,
):
    created = _create()
    workspace = created["workspace"]
    assert isinstance(workspace, dict)
    workspace_id = str(workspace["workspace_id"])
    fixture = b"KMFA-P42-SYNTHETIC\x00\xff" + bytes(range(256))
    fixture_hash = hashlib.sha256(fixture).hexdigest()

    saved = client.patch(
        f"{BASE}/workspaces/{workspace_id}",
        headers=_auth(created),
        json={"project_name": "P4.2 cross-device state", "progress": 72},
    )
    assert saved.status_code == 200
    uploaded = _upload(created, fixture)
    assert uploaded.status_code == 200

    exported = _export(created)
    assert exported.status_code == 200
    assert exported.headers["content-type"] == MEDIA_TYPE
    assert exported.headers["cache-control"] == "private, no-store"
    assert exported.headers["pragma"] == "no-cache"
    assert exported.headers["x-content-type-options"] == "nosniff"
    assert exported.headers["x-robots-tag"] == "noindex, nofollow, noarchive"
    assert exported.headers["content-disposition"] == (
        'attachment; filename="kmfa-workspace.kmfa-recovery"'
    )
    recovery_file = exported.json()
    assert set(recovery_file) == {
        "format",
        "version",
        "workspace_id",
        "workspace_secret",
    }
    assert recovery_file == {
        "format": "kmfa-recovery",
        "version": 1,
        "workspace_id": workspace_id,
        "workspace_secret": created["recovery_code"],
    }
    assert "project" not in exported.text
    assert "artifact" not in exported.text

    imported = _import(exported.content)
    assert imported.status_code == 200, imported.text
    restored = imported.json()
    assert restored["recovery_file_imported"] is True
    assert restored["workspace_secret_returned"] is False
    assert restored["access_token"] != created["access_token"]
    assert restored["workspace"]["workspace_id"] == workspace_id
    assert restored["workspace"]["project_name"] == "P4.2 cross-device state"
    assert restored["workspace"]["progress"] == 72
    assert restored["workspace"]["artifact"]["sha256"] == fixture_hash

    downloaded = client.post(
        f"{BASE}/workspaces/{workspace_id}/artifact/download",
        headers=_auth(restored),
    )
    assert downloaded.status_code == 200
    assert downloaded.content == fixture
    assert downloaded.headers["x-kmfa-artifact-sha256"] == fixture_hash

    state_bytes = b"".join(
        path.read_bytes() for path in recovery_store.rglob("*") if path.is_file()
    )
    assert str(created["recovery_code"]).encode("ascii") not in state_bytes
    assert exported.content not in state_bytes


@pytest.mark.parametrize(
    "invalid_file",
    [
        b"{",
        b"[]",
        json.dumps(
            {
                "format": "not-kmfa-recovery",
                "version": 1,
                "workspace_id": "ws_" + ("A" * 22),
                "workspace_secret": "kmfa-r1-" + ("B" * 43),
            }
        ).encode(),
        json.dumps(
            {
                "format": "kmfa-recovery",
                "version": True,
                "workspace_id": "ws_" + ("A" * 22),
                "workspace_secret": "kmfa-r1-" + ("B" * 43),
            }
        ).encode(),
        json.dumps(
            {
                "format": "kmfa-recovery",
                "version": 1,
                "workspace_id": "ws_" + ("A" * 22),
                "workspace_secret": "kmfa-r1-" + ("B" * 43),
                "project_name": "must-not-be-accepted",
            }
        ).encode(),
        (
            '{"format":"kmfa-recovery","format":"kmfa-recovery","version":1,'
            '"workspace_id":"ws_AAAAAAAAAAAAAAAAAAAAAA",'
            '"workspace_secret":"kmfa-r1-BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"}'
        ).encode(),
    ],
)
def test_malformed_truncated_or_extended_recovery_files_never_authorize(
    recovery_store: Path,
    invalid_file: bytes,
):
    del recovery_store
    response = _import(invalid_file)
    assert response.status_code == 404
    assert response.json() == {"detail": "recovery_not_found"}
    assert "access_token" not in response.text


def test_unknown_id_wrong_secret_media_type_and_oversize_never_authorize(
    recovery_store: Path,
):
    del recovery_store
    created = _create()
    exported = _export(created)
    valid = exported.json()

    wrong_secret = dict(valid)
    wrong_secret["workspace_secret"] = "kmfa-r1-" + ("W" * 43)
    if wrong_secret["workspace_secret"] == created["recovery_code"]:
        wrong_secret["workspace_secret"] = "kmfa-r1-" + ("X" * 43)
    unknown_id = dict(valid)
    unknown_id["workspace_id"] = "ws_" + ("Z" * 22)
    if unknown_id["workspace_id"] == valid["workspace_id"]:
        unknown_id["workspace_id"] = "ws_" + ("Y" * 22)

    attempts = [
        _import(json.dumps(wrong_secret).encode()),
        _import(json.dumps(unknown_id).encode()),
    ]
    assert all(response.status_code == 404 for response in attempts)
    assert all("access_token" not in response.text for response in attempts)

    wrong_media = client.post(
        f"{BASE}/recovery-files/import",
        content=exported.content,
        headers={"Content-Type": "application/json"},
    )
    oversized = client.post(
        f"{BASE}/recovery-files/import",
        content=b"x" * (recovery.MAX_RECOVERY_FILE_BYTES + 1),
        headers={"Content-Type": MEDIA_TYPE},
    )
    assert wrong_media.status_code == 415
    assert wrong_media.json() == {"detail": "invalid_recovery_file"}
    assert oversized.status_code == 413
    assert oversized.json() == {"detail": "recovery_file_too_large"}


def test_rotation_atomically_revokes_old_code_and_file_without_deleting_data(
    recovery_store: Path,
):
    created = _create("P4.2 rotation")
    workspace = created["workspace"]
    assert isinstance(workspace, dict)
    workspace_id = str(workspace["workspace_id"])
    old_secret = str(created["recovery_code"])
    old_file = _export(created).content
    fixture = b"rotation-preserves-this-object"
    assert _upload(created, fixture).status_code == 200

    rotated = client.post(
        f"{BASE}/workspaces/{workspace_id}/recovery-secret/rotate",
        headers=_auth(created),
    )
    assert rotated.status_code == 200, rotated.text
    rotation = rotated.json()
    new_secret = rotation["workspace_secret"]
    assert recovery.RECOVERY_CODE_RE.fullmatch(new_secret)
    assert new_secret != old_secret
    assert rotation["workspace_secret_shown_once"] is True
    assert rotation["previous_workspace_secret_revoked"] is True
    assert rotation["existing_sessions_revoked"] is False

    old_code = client.post(
        f"{BASE}/recoveries",
        json={"recovery_code": old_secret},
    )
    old_exchange = client.post(
        f"{BASE}/sessions",
        json={"workspace_id": workspace_id, "workspace_secret": old_secret},
    )
    old_import = _import(old_file)
    assert [old_code.status_code, old_exchange.status_code, old_import.status_code] == [
        404,
        404,
        404,
    ]
    assert all(
        "access_token" not in response.text
        for response in (old_code, old_exchange, old_import)
    )

    still_open = client.get(
        f"{BASE}/workspaces/{workspace_id}",
        headers=_auth(created),
    )
    assert still_open.status_code == 200
    assert still_open.json()["artifact"]["sha256"] == hashlib.sha256(fixture).hexdigest()

    new_exchange = client.post(
        f"{BASE}/sessions",
        json={"workspace_id": workspace_id, "workspace_secret": new_secret},
    )
    assert new_exchange.status_code == 200
    new_export = client.post(
        f"{BASE}/workspaces/{workspace_id}/recovery-file",
        headers=_auth(created),
        json={"workspace_secret": new_secret},
    )
    assert new_export.status_code == 200
    new_import = _import(new_export.content)
    assert new_import.status_code == 200
    assert new_import.json()["workspace"]["artifact"]["sha256"] == hashlib.sha256(
        fixture
    ).hexdigest()

    database = recovery_store / "walking_skeleton.sqlite3"
    connection = sqlite3.connect(database)
    try:
        stored_hash = connection.execute(
            "SELECT recovery_hash FROM workspaces WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()[0]
        artifact_count = connection.execute(
            "SELECT COUNT(*) FROM artifacts WHERE workspace_id = ?",
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
    assert stored_hash == hashlib.sha256(new_secret.encode("ascii")).hexdigest()
    assert artifact_count == 1
    assert "workspace_secret_rotated" in actions
    assert "recovery_file_imported" in actions
    state_bytes = b"".join(
        path.read_bytes() for path in recovery_store.rglob("*") if path.is_file()
    )
    assert old_secret.encode("ascii") not in state_bytes
    assert new_secret.encode("ascii") not in state_bytes


def test_export_requires_session_and_current_secret(recovery_store: Path):
    del recovery_store
    created = _create()
    workspace = created["workspace"]
    assert isinstance(workspace, dict)
    endpoint = f"{BASE}/workspaces/{workspace['workspace_id']}/recovery-file"
    wrong_secret = "kmfa-r1-" + ("Q" * 43)
    if wrong_secret == created["recovery_code"]:
        wrong_secret = "kmfa-r1-" + ("R" * 43)

    missing_session = client.post(
        endpoint,
        json={"workspace_secret": created["recovery_code"]},
    )
    wrong_session = client.post(
        endpoint,
        headers={"Authorization": "Bearer kmfa-a1-" + ("S" * 43)},
        json={"workspace_secret": created["recovery_code"]},
    )
    wrong_capability = client.post(
        endpoint,
        headers=_auth(created),
        json={"workspace_secret": wrong_secret},
    )
    assert [
        missing_session.status_code,
        wrong_session.status_code,
        wrong_capability.status_code,
    ] == [404, 404, 404]


def test_legacy_s03_workspace_identity_exports_and_imports(
    recovery_store: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    del recovery_store
    legacy_workspace_id = "ws_" + ("L" * 16)
    monkeypatch.setattr(recovery, "_new_workspace_id", lambda: legacy_workspace_id)
    created = _create("legacy recovery asset")
    assert created["workspace"]["workspace_id"] == legacy_workspace_id

    exported = _export(created)
    assert exported.status_code == 200
    assert exported.json()["workspace_id"] == legacy_workspace_id
    imported = _import(exported.content)
    assert imported.status_code == 200
    assert imported.json()["workspace"]["workspace_id"] == legacy_workspace_id


def test_status_declares_p42_recovery_contract(recovery_store: Path):
    del recovery_store
    response = client.get(f"{BASE}/status")
    assert response.status_code == 200
    assert response.json()["recovery_experience"] == {
        "file_format": "kmfa-recovery",
        "file_version": 1,
        "file_media_type": MEDIA_TYPE,
        "max_file_bytes": 4096,
        "import": f"{BASE}/recovery-files/import",
        "secret_rotation": True,
        "email_recovery": False,
    }
