"""S04/P4.1 TEST-WS-001 anonymous identity and verifier contract."""

from __future__ import annotations

import base64
import sqlite3
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from app import walking_skeleton as identity
from app.main import app

client = TestClient(app)
BASE = "/public-api/walking-skeleton/v1"
WORKSPACE_COUNT = 10_000


@pytest.fixture
def identity_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    state = tmp_path / "anonymous-identity"
    monkeypatch.setenv("KMFA_WALKING_SKELETON_ENABLED", "1")
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(state))
    monkeypatch.delenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", raising=False)
    return state


def _decoded_random_bytes(value: str, prefix: str) -> bytes:
    encoded = value.removeprefix(prefix)
    return base64.urlsafe_b64decode(encoded + ("=" * (-len(encoded) % 4)))


def _auth(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def test_10000_workspace_identities_are_unique_and_never_stored_in_plaintext(
    identity_store: Path,
):
    workspace_ids: list[str] = []
    workspace_secrets: list[str] = []
    access_tokens: list[str] = []

    for index in range(WORKSPACE_COUNT):
        created = identity._create_workspace(f"synthetic-identity-{index}")
        workspace_ids.append(created["workspace"]["workspace_id"])
        workspace_secrets.append(created["recovery_code"])
        access_tokens.append(created["access_token"])

    assert len(workspace_ids) == len(set(workspace_ids)) == WORKSPACE_COUNT
    assert len(workspace_secrets) == len(set(workspace_secrets)) == WORKSPACE_COUNT
    assert len(access_tokens) == len(set(access_tokens)) == WORKSPACE_COUNT
    assert all(identity.WORKSPACE_ID_RE.fullmatch(value) for value in workspace_ids)
    assert all(
        len(_decoded_random_bytes(value, "ws_")) == identity.WORKSPACE_ID_BYTES
        for value in workspace_ids
    )
    assert all(
        len(_decoded_random_bytes(value, "kmfa-r1-"))
        == identity.WORKSPACE_SECRET_BYTES
        for value in workspace_secrets
    )
    assert all(
        len(_decoded_random_bytes(value, "kmfa-a1-"))
        == identity.ACCESS_TOKEN_BYTES
        for value in access_tokens
    )

    database = identity_store / "walking_skeleton.sqlite3"
    connection = sqlite3.connect(database)
    try:
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("workspaces", "access_tokens", "audit_events")
        }
        recovery_verifiers = [
            row[0] for row in connection.execute("SELECT recovery_hash FROM workspaces")
        ]
        session_verifiers = [
            row[0] for row in connection.execute("SELECT token_hash FROM access_tokens")
        ]
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        connection.close()

    assert counts == {
        "workspaces": WORKSPACE_COUNT,
        "access_tokens": WORKSPACE_COUNT,
        "audit_events": WORKSPACE_COUNT,
    }
    assert len(set(recovery_verifiers)) == WORKSPACE_COUNT
    assert len(set(session_verifiers)) == WORKSPACE_COUNT
    assert all(identity.SHA256_HEX_RE.fullmatch(value) for value in recovery_verifiers)
    assert all(identity.SHA256_HEX_RE.fullmatch(value) for value in session_verifiers)

    state_bytes = b"".join(
        path.read_bytes() for path in identity_store.rglob("*") if path.is_file()
    )
    assert b"kmfa-r1-" not in state_bytes
    assert b"kmfa-a1-" not in state_bytes


def test_concurrent_workspace_creation_preserves_uniqueness(identity_store: Path):
    cold_start_barrier = Barrier(32)

    def create(index: int):
        if index < 32:
            cold_start_barrier.wait()
        return identity._create_workspace(f"synthetic-concurrent-{index}")

    with ThreadPoolExecutor(max_workers=32) as pool:
        created = list(pool.map(create, range(256)))

    workspace_ids = [row["workspace"]["workspace_id"] for row in created]
    workspace_secrets = [row["recovery_code"] for row in created]
    access_tokens = [row["access_token"] for row in created]
    assert len(set(workspace_ids)) == 256
    assert len(set(workspace_secrets)) == 256
    assert len(set(access_tokens)) == 256

    connection = sqlite3.connect(identity_store / "walking_skeleton.sqlite3")
    try:
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("workspaces", "access_tokens", "audit_events")
        }
    finally:
        connection.close()
    assert counts == {"workspaces": 256, "access_tokens": 256, "audit_events": 256}


def test_session_exchange_uses_verifier_and_returns_only_a_short_session(
    identity_store: Path,
):
    created = identity._create_workspace("synthetic-session")
    workspace_id = created["workspace"]["workspace_id"]
    workspace_secret = created["recovery_code"]

    before = datetime.now(timezone.utc)
    response = client.post(
        f"{BASE}/sessions",
        json={
            "workspace_id": workspace_id,
            "workspace_secret": workspace_secret,
        },
    )
    after = datetime.now(timezone.utc)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-robots-tag"] == "noindex, nofollow, noarchive"
    session_token = response.cookies.get(identity.SESSION_COOKIE_NAME)
    assert identity.ACCESS_TOKEN_RE.fullmatch(session_token)
    exchanged = response.json()
    expires_at = datetime.fromisoformat(
        exchanged["access_expires_at"].replace("Z", "+00:00")
    )
    assert exchanged["workspace"]["workspace_id"] == workspace_id
    assert "access_token" not in exchanged
    assert session_token != created["access_token"]
    assert exchanged["workspace_secret_returned"] is False
    assert exchanged["session_ttl_seconds"] == 3600
    assert 3598 <= (expires_at - before).total_seconds() <= 3601
    assert 3598 <= (expires_at - after).total_seconds() <= 3601
    assert "workspace_secret" not in exchanged
    assert "recovery_code" not in exchanged

    assert (
        client.get(
            f"{BASE}/workspaces/{workspace_id}",
            headers=_auth(session_token),
        ).status_code
        == 200
    )
    connection = sqlite3.connect(identity_store / "walking_skeleton.sqlite3")
    try:
        stored = connection.execute(
            "SELECT recovery_hash FROM workspaces WHERE workspace_id = ?",
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
    assert stored == identity._hash_capability(workspace_secret)
    assert workspace_secret not in stored
    assert actions == ["workspace_created", "workspace_session_exchanged"]


def test_unknown_id_and_wrong_secret_share_error_and_bounded_timing(
    identity_store: Path,
):
    created = identity._create_workspace("synthetic-negative")
    workspace_id = created["workspace"]["workspace_id"]
    wrong_secret = "kmfa-r1-" + ("A" * 43)
    if wrong_secret == created["recovery_code"]:
        wrong_secret = "kmfa-r1-" + ("B" * 43)
    unknown_workspace_id = "ws_" + ("Z" * 22)
    if unknown_workspace_id == workspace_id:
        unknown_workspace_id = "ws_" + ("Y" * 22)

    wrong = client.post(
        f"{BASE}/sessions",
        json={
            "workspace_id": workspace_id,
            "workspace_secret": wrong_secret,
        },
    )
    unknown = client.post(
        f"{BASE}/sessions",
        json={
            "workspace_id": unknown_workspace_id,
            "workspace_secret": wrong_secret,
        },
    )
    malformed = client.post(
        f"{BASE}/sessions",
        json={"workspace_id": "bad", "workspace_secret": "bad"},
    )
    assert wrong.status_code == unknown.status_code == malformed.status_code == 404
    assert wrong.json() == unknown.json() == malformed.json() == {
        "detail": "workspace_not_found"
    }

    known_timings: list[int] = []
    unknown_timings: list[int] = []
    with identity._store() as connection:
        for _ in range(500):
            started = time.perf_counter_ns()
            assert not identity._workspace_secret_matches(
                connection,
                workspace_id,
                wrong_secret,
            )
            known_timings.append(time.perf_counter_ns() - started)

            started = time.perf_counter_ns()
            assert not identity._workspace_secret_matches(
                connection,
                unknown_workspace_id,
                wrong_secret,
            )
            unknown_timings.append(time.perf_counter_ns() - started)

    median_delta_ns = abs(
        statistics.median(known_timings) - statistics.median(unknown_timings)
    )
    assert median_delta_ns < 1_000_000


def test_session_exchange_keeps_legacy_s03_workspace_ids_recoverable(
    identity_store: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    legacy_workspace_id = "ws_" + ("L" * 16)
    monkeypatch.setattr(identity, "_new_workspace_id", lambda: legacy_workspace_id)
    created = identity._create_workspace("synthetic-legacy")
    assert created["workspace"]["workspace_id"] == legacy_workspace_id

    response = client.post(
        f"{BASE}/sessions",
        json={
            "workspace_id": legacy_workspace_id,
            "workspace_secret": created["recovery_code"],
        },
    )
    assert response.status_code == 200
    assert response.json()["workspace"]["workspace_id"] == legacy_workspace_id


def test_session_token_is_scoped_to_one_workspace(identity_store: Path):
    first = identity._create_workspace("synthetic-first")
    second = identity._create_workspace("synthetic-second")
    first_id = first["workspace"]["workspace_id"]
    second_id = second["workspace"]["workspace_id"]

    assert (
        client.get(
            f"{BASE}/workspaces/{first_id}",
            headers=_auth(first["access_token"]),
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"{BASE}/workspaces/{second_id}",
            headers=_auth(first["access_token"]),
        ).status_code
        == 404
    )


def test_status_declares_p41_identity_contract(identity_store: Path):
    response = client.get(f"{BASE}/status")
    assert response.status_code == 200
    assert response.json()["anonymous_identity"] == {
        "workspace_id_entropy_bits": 128,
        "workspace_secret_entropy_bits": 256,
        "access_token_entropy_bits": 256,
        "verifier": "sha256-of-256-bit-secret",
        "session_exchange": f"{BASE}/sessions",
    }
