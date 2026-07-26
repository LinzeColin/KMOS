"""S06/P6.1 TEST-UP-001/002 resumable arbitrary-file contract."""

from __future__ import annotations

import hashlib
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import anti_abuse
from app import walking_skeleton as skeleton
from app.consistency_reconciliation import reconcile_upload_operations
from app.main import app

BASE = "/public-api/walking-skeleton/v1"


@pytest.fixture
def resumable_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    state = tmp_path / "walking-state"
    monkeypatch.setenv("KMFA_WALKING_SKELETON_ENABLED", "1")
    monkeypatch.setenv("KMFA_RESUMABLE_UPLOAD_ENABLED", "1")
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(state))
    monkeypatch.delenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", raising=False)
    return state


def _create(client: TestClient, name: str = "P6.1 synthetic") -> dict:
    response = client.post(f"{BASE}/workspaces", json={"project_name": name})
    assert response.status_code == 201, response.text
    payload = response.json()
    token = response.cookies.get(skeleton.SESSION_COOKIE_NAME)
    assert token and skeleton.ACCESS_TOKEN_RE.fullmatch(token)
    payload["_token"] = token
    return payload


def _auth(created: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {created['_token']}"}


def _new_session(
    client: TestClient,
    created: dict,
    payload: bytes,
    *,
    name: str = "fixture.unknown",
    media_type: str = "application/octet-stream",
    key: str = "p61-resumable-idempotency-0001",
    expected_sha256: str | None = None,
):
    workspace_id = created["workspace"]["workspace_id"]
    return client.post(
        f"{BASE}/workspaces/{workspace_id}/upload-sessions",
        headers={**_auth(created), "Idempotency-Key": key},
        json={
            "original_name": name,
            "reported_media_type": media_type,
            "size_bytes": len(payload),
            "sha256": expected_sha256 or hashlib.sha256(payload).hexdigest(),
        },
    )


def _send_chunk(
    client: TestClient,
    created: dict,
    session_id: str,
    *,
    offset: int,
    chunk: bytes,
    claimed_sha256: str | None = None,
):
    workspace_id = created["workspace"]["workspace_id"]
    return client.patch(
        f"{BASE}/workspaces/{workspace_id}/upload-sessions/{session_id}",
        headers={
            **_auth(created),
            "Content-Type": "application/offset+octet-stream",
            "Upload-Offset": str(offset),
            "X-KMFA-Chunk-SHA256": (
                claimed_sha256 or hashlib.sha256(chunk).hexdigest()
            ),
        },
        content=chunk,
    )


def _complete(client: TestClient, created: dict, session_id: str):
    workspace_id = created["workspace"]["workspace_id"]
    return client.post(
        (
            f"{BASE}/workspaces/{workspace_id}/upload-sessions/"
            f"{session_id}/complete"
        ),
        headers=_auth(created),
    )


def test_resumable_flag_is_fail_closed_and_standard_upload_is_rollback(
    resumable_store: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    with TestClient(app) as client:
        enabled = client.get(f"{BASE}/status")
        assert enabled.status_code == 200
        assert enabled.json()["resumable_upload"] == {
            "enabled": True,
            "protocol": "kmfa-offset-v1",
            "max_file_bytes": 64 * 1024 * 1024,
            "max_chunk_bytes": 4 * 1024 * 1024,
            "max_sessions_per_workspace": 16,
            "checksum": "sha256",
            "attachment_only_until_classified": True,
            "standard_upload_rollback": True,
        }

        monkeypatch.setenv("KMFA_RESUMABLE_UPLOAD_ENABLED", "typo")
        status = client.get(f"{BASE}/status")
        assert status.status_code == 200
        assert status.json()["resumable_upload"]["enabled"] is False
        created = _create(client, "rollback standard upload")
        workspace_id = created["workspace"]["workspace_id"]
        disabled = client.post(
            f"{BASE}/workspaces/{workspace_id}/upload-sessions",
            headers={
                **_auth(created),
                "Idempotency-Key": "p61-disabled-idempotency-0001",
            },
            json={
                "original_name": "disabled.bin",
                "reported_media_type": "application/octet-stream",
                "size_bytes": 1,
                "sha256": hashlib.sha256(b"x").hexdigest(),
            },
        )
        assert disabled.status_code == 404
        assert disabled.json()["detail"] == "resumable_upload_disabled"
        standard = client.put(
            f"{BASE}/workspaces/{workspace_id}/artifact",
            headers={
                **_auth(created),
                "X-KMFA-Filename": "rollback.bin",
                "Content-Type": "application/octet-stream",
            },
            content=b"rollback-safe",
        )
        assert standard.status_code == 200


@pytest.mark.parametrize(
    ("filename", "media_type", "payload"),
    [
        ("document.pdf", "application/pdf", b"%PDF-synthetic"),
        ("image.png", "image/png", b"\x89PNG\r\n\x1a\nsynthetic"),
        ("audio.mp3", "audio/mpeg", b"ID3synthetic"),
        ("video.mp4", "video/mp4", b"\x00\x00\x00\x18ftypsynthetic"),
        ("archive.zip", "application/zip", b"PK\x03\x04synthetic"),
        ("binary.unknown", "application/x-unknown", b"\x00\xffbinary"),
        ("danger.double.exe", "application/x-msdownload", b"MZsynthetic"),
    ],
)
def test_every_file_type_is_stored_private_and_downloaded_attachment_only(
    resumable_store: Path,
    filename: str,
    media_type: str,
    payload: bytes,
):
    with TestClient(app) as client:
        created = _create(client, filename)
        session = _new_session(
            client,
            created,
            payload,
            name=filename,
            media_type=media_type,
            key=f"p61-file-type-{hashlib.sha256(filename.encode()).hexdigest()}",
        )
        assert session.status_code == 201, session.text
        session_id = session.json()["upload_session"]["upload_session_id"]
        chunk = _send_chunk(
            client,
            created,
            session_id,
            offset=0,
            chunk=payload,
        )
        assert chunk.status_code == 204, chunk.text
        completed = _complete(client, created, session_id)
        assert completed.status_code == 200, completed.text
        artifact = completed.json()["artifact"]
        assert artifact["sha256"] == hashlib.sha256(payload).hexdigest()
        assert artifact["download_mode"] == "attachment-only"

        workspace_id = created["workspace"]["workspace_id"]
        downloaded = client.post(
            f"{BASE}/workspaces/{workspace_id}/artifact/download",
            headers=_auth(created),
        )
        assert downloaded.status_code == 200
        assert downloaded.content == payload
        assert downloaded.headers["content-type"].startswith(
            "application/octet-stream"
        )
        assert downloaded.headers["content-disposition"].startswith("attachment;")
        assert downloaded.headers["x-content-type-options"] == "nosniff"
        assert downloaded.headers["x-kmfa-artifact-mode"] == "attachment-only"

        object_name = next((resumable_store / "objects").glob("*.blob")).name
        assert client.get(f"{BASE}/objects/{object_name}").status_code == 404
        assert client.get(f"/assets/{object_name}").status_code == 404


@pytest.mark.parametrize("completed_chunks", [0, 1, 2, 3])
def test_resume_succeeds_from_every_chunk_boundary(
    resumable_store: Path,
    monkeypatch: pytest.MonkeyPatch,
    completed_chunks: int,
):
    monkeypatch.setattr(skeleton, "MAX_RESUMABLE_ARTIFACT_BYTES", 12)
    monkeypatch.setattr(skeleton, "MAX_UPLOAD_CHUNK_BYTES", 4)
    monkeypatch.setattr(skeleton, "MIN_FREE_STATE_BYTES", 0)
    payload = b"AAAABBBBCC"
    chunks = (payload[:4], payload[4:8], payload[8:])
    with TestClient(app) as client:
        created = _create(client, f"boundary {completed_chunks}")
        session = _new_session(
            client,
            created,
            payload,
            key=f"p61-boundary-{completed_chunks}-0001",
        )
        session_id = session.json()["upload_session"]["upload_session_id"]
        offset = 0
        for chunk in chunks[:completed_chunks]:
            sent = _send_chunk(
                client,
                created,
                session_id,
                offset=offset,
                chunk=chunk,
            )
            assert sent.status_code == 204
            offset = int(sent.headers["upload-offset"])

    with TestClient(app) as resumed:
        workspace_id = created["workspace"]["workspace_id"]
        status = resumed.get(
            (
                f"{BASE}/workspaces/{workspace_id}/upload-sessions/"
                f"{session_id}"
            ),
            headers=_auth(created),
        )
        assert status.status_code == 200
        assert status.json()["upload_session"]["offset_bytes"] == offset
        for chunk in chunks[completed_chunks:]:
            sent = _send_chunk(
                resumed,
                created,
                session_id,
                offset=offset,
                chunk=chunk,
            )
            assert sent.status_code == 204
            offset = int(sent.headers["upload-offset"])
        assert offset == len(payload)
        completed = _complete(resumed, created, session_id)
        assert completed.status_code == 200
        assert (
            completed.json()["artifact"]["sha256"]
            == hashlib.sha256(payload).hexdigest()
        )
    assert not list((resumable_store / "tmp").glob("*.chunk"))


def test_interrupted_upload_resumes_and_duplicate_chunk_does_not_grow(
    resumable_store: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(skeleton, "MAX_RESUMABLE_ARTIFACT_BYTES", 16)
    monkeypatch.setattr(skeleton, "MAX_UPLOAD_CHUNK_BYTES", 4)
    monkeypatch.setattr(skeleton, "MIN_FREE_STATE_BYTES", 0)
    payload = b"AAAABBBBCCCCDD"
    with TestClient(app) as client:
        created = _create(client)
        session = _new_session(client, created, payload)
        assert session.status_code == 201, session.text
        session_id = session.json()["upload_session"]["upload_session_id"]

        first = _send_chunk(
            client,
            created,
            session_id,
            offset=0,
            chunk=payload[:4],
        )
        replay = _send_chunk(
            client,
            created,
            session_id,
            offset=0,
            chunk=payload[:4],
        )
        assert first.status_code == replay.status_code == 204
        assert first.headers["upload-offset"] == "4"
        assert replay.headers["upload-offset"] == "4"
        assert len(list((resumable_store / "tmp").glob("*.chunk"))) == 1

        conflict = _send_chunk(
            client,
            created,
            session_id,
            offset=0,
            chunk=b"ZZZZ",
        )
        assert conflict.status_code == 409
        assert conflict.json()["detail"] == "upload_chunk_conflict"
        assert conflict.headers["upload-offset"] == "4"
        out_of_order = _send_chunk(
            client,
            created,
            session_id,
            offset=8,
            chunk=payload[8:12],
        )
        assert out_of_order.status_code == 409
        assert out_of_order.json()["detail"] == "upload_offset_conflict"
        assert out_of_order.headers["upload-offset"] == "4"

    # A new client/process view discovers the durable offset and continues.
    with TestClient(app) as restarted:
        workspace_id = created["workspace"]["workspace_id"]
        status = restarted.get(
            f"{BASE}/workspaces/{workspace_id}/upload-sessions/{session_id}",
            headers=_auth(created),
        )
        assert status.status_code == 200
        assert status.json()["upload_session"]["offset_bytes"] == 4
        reconciliation = reconcile_upload_operations()
        assert reconciliation["incomplete_resumable_count"] == 1
        assert reconciliation["resumed_operation_count"] == 0

        offset = 4
        while offset < len(payload):
            chunk = payload[offset : offset + 4]
            response = _send_chunk(
                restarted,
                created,
                session_id,
                offset=offset,
                chunk=chunk,
            )
            assert response.status_code == 204, response.text
            offset = int(response.headers["upload-offset"])
        completed = _complete(restarted, created, session_id)
        assert completed.status_code == 200, completed.text
        assert (
            completed.json()["artifact"]["sha256"]
            == hashlib.sha256(payload).hexdigest()
        )
        assert not list((resumable_store / "tmp").glob("*.chunk"))


def test_chunk_and_end_to_end_checksum_tampering_fail_closed(
    resumable_store: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(skeleton, "MAX_UPLOAD_CHUNK_BYTES", 4)
    monkeypatch.setattr(skeleton, "MAX_RESUMABLE_ARTIFACT_BYTES", 8)
    monkeypatch.setattr(skeleton, "MIN_FREE_STATE_BYTES", 0)
    payload = b"12345678"
    wrong_full_hash = hashlib.sha256(b"different").hexdigest()
    with TestClient(app) as client:
        created = _create(client)
        session = _new_session(
            client,
            created,
            payload,
            expected_sha256=wrong_full_hash,
        )
        assert session.status_code == 201
        session_id = session.json()["upload_session"]["upload_session_id"]

        tampered_claim = _send_chunk(
            client,
            created,
            session_id,
            offset=0,
            chunk=payload[:4],
            claimed_sha256=hashlib.sha256(b"forged").hexdigest(),
        )
        assert tampered_claim.status_code == 409
        assert tampered_claim.json()["detail"] == "upload_chunk_checksum_mismatch"
        assert not list((resumable_store / "tmp").glob("*.chunk"))

        assert (
            _send_chunk(
                client,
                created,
                session_id,
                offset=0,
                chunk=payload[:4],
            ).status_code
            == 204
        )
        assert (
            _send_chunk(
                client,
                created,
                session_id,
                offset=4,
                chunk=payload[4:],
            ).status_code
            == 204
        )
        complete = _complete(client, created, session_id)
        assert complete.status_code == 409
        assert complete.json()["detail"] == "upload_checksum_mismatch"
        assert not list((resumable_store / "objects").glob("*"))


def test_limits_reserve_budget_before_chunks_and_zero_byte_completes(
    resumable_store: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(skeleton, "MAX_RESUMABLE_ARTIFACT_BYTES", 8)
    monkeypatch.setattr(skeleton, "MAX_TOTAL_ARTIFACT_BYTES", 8)
    monkeypatch.setattr(skeleton, "MIN_FREE_STATE_BYTES", 0)
    with TestClient(app) as client:
        too_large_owner = _create(client, "too large")
        too_large = _new_session(
            client,
            too_large_owner,
            b"123456789",
            key="p61-over-file-limit-0001",
        )
        assert too_large.status_code == 413
        assert too_large.json()["detail"] == "artifact_too_large"
        assert not list((resumable_store / "tmp").glob("*.chunk"))

        reserved_owner = _create(client, "reserved")
        reserved = _new_session(
            client,
            reserved_owner,
            b"12345678",
            key="p61-reserved-budget-0001",
        )
        assert reserved.status_code == 201
        blocked_owner = _create(client, "blocked before bytes")
        blocked = _new_session(
            client,
            blocked_owner,
            b"x",
            key="p61-blocked-budget-0001",
        )
        assert blocked.status_code == 429
        assert blocked.json()["detail"] == "artifact_capacity_reached"

        connection = sqlite3.connect(
            resumable_store / "walking_skeleton.sqlite3"
        )
        try:
            operations = connection.execute(
                "SELECT COUNT(*) FROM consistency_operations"
            ).fetchone()[0]
        finally:
            connection.close()
        assert operations == 1
        assert not list((resumable_store / "tmp").glob("*.chunk"))

    # Zero-byte completion is a valid arbitrary file in an isolated store.
    zero_state = resumable_store.parent / "zero-state"
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(zero_state))
    with TestClient(app) as zero_client:
        created = _create(zero_client, "zero")
        zero = _new_session(
            zero_client,
            created,
            b"",
            key="p61-zero-byte-upload-0001",
        )
        assert zero.status_code == 201
        session_id = zero.json()["upload_session"]["upload_session_id"]
        completed = _complete(zero_client, created, session_id)
        assert completed.status_code == 200
        assert completed.json()["artifact"]["size_bytes"] == 0


def test_session_reserves_chunk_and_assembled_file_space_before_intent(
    resumable_store: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(skeleton, "MAX_RESUMABLE_ARTIFACT_BYTES", 8)
    monkeypatch.setattr(skeleton, "MIN_FREE_STATE_BYTES", 10)
    monkeypatch.setattr(
        skeleton.shutil,
        "disk_usage",
        lambda _: SimpleNamespace(free=25),
    )
    with TestClient(app) as client:
        created = _create(client, "two-copy reservation")
        rejected = _new_session(
            client,
            created,
            b"12345678",
            key="p61-two-copy-reservation-0001",
        )
        assert rejected.status_code == 429
        assert rejected.json()["detail"] == "artifact_capacity_reached"
    database = sqlite3.connect(
        resumable_store / "walking_skeleton.sqlite3"
    )
    try:
        assert database.execute(
            "SELECT COUNT(*) FROM consistency_operations"
        ).fetchone()[0] == 0
    finally:
        database.close()


def test_concurrent_duplicate_chunk_is_single_copy(
    resumable_store: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(skeleton, "MAX_UPLOAD_CHUNK_BYTES", 4)
    monkeypatch.setattr(skeleton, "MAX_RESUMABLE_ARTIFACT_BYTES", 4)
    monkeypatch.setattr(skeleton, "MIN_FREE_STATE_BYTES", 0)
    payload = b"same"
    with TestClient(app) as client:
        created = _create(client)
        session = _new_session(client, created, payload)
        session_id = session.json()["upload_session"]["upload_session_id"]

    def send() -> tuple[int, str]:
        with TestClient(app) as concurrent_client:
            response = _send_chunk(
                concurrent_client,
                created,
                session_id,
                offset=0,
                chunk=payload,
            )
            return response.status_code, response.headers.get("upload-offset", "")

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: send(), range(2)))
    assert results == [(204, "4"), (204, "4")]
    chunks = list((resumable_store / "tmp").glob("*.chunk"))
    assert len(chunks) == 1
    assert chunks[0].read_bytes() == payload

    with TestClient(app) as client:
        completed = _complete(client, created, session_id)
        assert completed.status_code == 200
        replay = _new_session(client, created, payload)
        assert replay.status_code == 201
        assert replay.json()["upload_session"]["upload_session_id"] == session_id
        assert replay.json()["upload_session"]["state"] == "completed"
        assert _complete(client, created, session_id).status_code == 200
    assert len(list((resumable_store / "objects").glob("*.blob"))) == 1


def test_session_head_idempotent_replay_and_explicit_cancel_cleanup(
    resumable_store: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(skeleton, "MAX_UPLOAD_CHUNK_BYTES", 4)
    monkeypatch.setattr(skeleton, "MAX_RESUMABLE_ARTIFACT_BYTES", 8)
    monkeypatch.setattr(skeleton, "MAX_TOTAL_ARTIFACT_BYTES", 8)
    monkeypatch.setattr(skeleton, "MIN_FREE_STATE_BYTES", 0)
    payload = b"12345678"
    with TestClient(app) as client:
        created = _create(client, "cancel")
        first = _new_session(
            client,
            created,
            payload,
            key="p61-cancel-idempotency-0001",
        )
        session_id = first.json()["upload_session"]["upload_session_id"]
        assert _send_chunk(
            client,
            created,
            session_id,
            offset=0,
            chunk=payload[:4],
        ).status_code == 204

        replay = _new_session(
            client,
            created,
            payload,
            key="p61-cancel-idempotency-0001",
        )
        assert replay.status_code == 201
        assert replay.json()["upload_session"]["upload_session_id"] == session_id
        assert replay.json()["upload_session"]["offset_bytes"] == 4

        workspace_id = created["workspace"]["workspace_id"]
        head = client.head(
            (
                f"{BASE}/workspaces/{workspace_id}/upload-sessions/"
                f"{session_id}"
            ),
            headers=_auth(created),
        )
        assert head.status_code == 204
        assert head.headers["upload-offset"] == "4"
        assert head.headers["upload-length"] == "8"
        assert head.headers["upload-state"] == "active"

        cancelled = client.delete(
            (
                f"{BASE}/workspaces/{workspace_id}/upload-sessions/"
                f"{session_id}"
            ),
            headers=_auth(created),
        )
        assert cancelled.status_code == 204
        assert not list((resumable_store / "tmp").glob("*.chunk"))
        isolated = client.get(
            (
                f"{BASE}/workspaces/{workspace_id}/upload-sessions/"
                f"{session_id}"
            ),
            headers=_auth(created),
        )
        assert isolated.status_code == 200
        assert isolated.json()["upload_session"]["state"] == "isolated"

        replacement = _new_session(
            client,
            created,
            b"87654321",
            key="p61-cancel-replacement-0001",
        )
        # The cancellation released both workspace and global reservations.
        assert replacement.status_code == 201


def test_cancel_wins_against_inflight_chunk_without_leaving_bytes(
    resumable_store: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(skeleton, "MAX_UPLOAD_CHUNK_BYTES", 4)
    monkeypatch.setattr(skeleton, "MAX_RESUMABLE_ARTIFACT_BYTES", 8)
    monkeypatch.setattr(skeleton, "MIN_FREE_STATE_BYTES", 0)
    payload = b"12345678"
    with TestClient(app) as client:
        created = _create(client, "cancel race")
        session = _new_session(
            client,
            created,
            payload,
            key="p61-cancel-race-0001",
        )
        session_id = session.json()["upload_session"]["upload_session_id"]

    original_store = skeleton.store_verified_chunk
    reached_store = threading.Event()
    allow_store = threading.Event()

    def delayed_store(*args, **kwargs):
        reached_store.set()
        assert allow_store.wait(timeout=5)
        return original_store(*args, **kwargs)

    monkeypatch.setattr(skeleton, "store_verified_chunk", delayed_store)

    def send_inflight() -> tuple[int, str]:
        with TestClient(app) as concurrent_client:
            response = _send_chunk(
                concurrent_client,
                created,
                session_id,
                offset=0,
                chunk=payload[:4],
            )
            return response.status_code, response.json()["detail"]

    with ThreadPoolExecutor(max_workers=1) as pool:
        inflight = pool.submit(send_inflight)
        assert reached_store.wait(timeout=5)
        workspace_id = created["workspace"]["workspace_id"]
        with TestClient(app) as cancelling_client:
            cancelled = cancelling_client.delete(
                (
                    f"{BASE}/workspaces/{workspace_id}/upload-sessions/"
                    f"{session_id}"
                ),
                headers=_auth(created),
            )
        assert cancelled.status_code == 204
        allow_store.set()
        assert inflight.result(timeout=5) == (
            409,
            "upload_session_not_active",
        )

    assert not list((resumable_store / "tmp").glob("*.chunk"))
    with TestClient(app) as client:
        # Cancellation cleanup remains retryable/idempotent.
        repeated = client.delete(
            (
                f"{BASE}/workspaces/{workspace_id}/upload-sessions/"
                f"{session_id}"
            ),
            headers=_auth(created),
        )
        assert repeated.status_code == 204


def test_session_count_is_lifetime_bounded_after_explicit_cancellation(
    resumable_store: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        skeleton,
        "MAX_RESUMABLE_SESSIONS_PER_WORKSPACE",
        1,
    )
    monkeypatch.setattr(skeleton, "MIN_FREE_STATE_BYTES", 0)
    with TestClient(app) as client:
        created = _create(client, "bounded sessions")
        first = _new_session(
            client,
            created,
            b"a",
            key="p61-session-cap-first-0001",
        )
        assert first.status_code == 201
        workspace_id = created["workspace"]["workspace_id"]
        session_id = first.json()["upload_session"]["upload_session_id"]
        assert client.delete(
            (
                f"{BASE}/workspaces/{workspace_id}/upload-sessions/"
                f"{session_id}"
            ),
            headers=_auth(created),
        ).status_code == 204
        blocked = _new_session(
            client,
            created,
            b"b",
            key="p61-session-cap-second-0001",
        )
        assert blocked.status_code == 429
        assert blocked.json()["detail"] == "upload_session_capacity_reached"


def test_encoded_chunk_body_is_rejected_before_staging(
    resumable_store: Path,
):
    payload = b"identity-bytes"
    with TestClient(app) as client:
        created = _create(client, "encoded")
        session = _new_session(
            client,
            created,
            payload,
            key="p61-content-encoding-0001",
        )
        session_id = session.json()["upload_session"]["upload_session_id"]
        workspace_id = created["workspace"]["workspace_id"]
        encoded = client.patch(
            (
                f"{BASE}/workspaces/{workspace_id}/upload-sessions/"
                f"{session_id}"
            ),
            headers={
                **_auth(created),
                "Content-Type": "application/offset+octet-stream",
                "Content-Encoding": "gzip",
                "Upload-Offset": "0",
                "X-KMFA-Chunk-SHA256": hashlib.sha256(payload).hexdigest(),
            },
            content=payload,
        )
        assert encoded.status_code == 415
        assert encoded.json()["detail"] == "invalid_upload_content_encoding"
        assert not list((resumable_store / "tmp").glob("*.chunk"))


def test_resumable_routes_use_expensive_upload_budget_and_release_wiring(
    resumable_store: Path,
):
    del resumable_store
    workspace_path = (
        f"{BASE}/workspaces/ws_{'a' * 22}/upload-sessions/"
        f"operation_{'b' * 24}"
    )
    for method in ("POST", "PATCH", "DELETE"):
        assert anti_abuse._classify(method, workspace_path)[0] == "upload"
    assert anti_abuse._classify("GET", workspace_path)[0] == "read"
    assert anti_abuse._classify("HEAD", workspace_path)[0] is None

    repo = Path(__file__).resolve().parents[4]
    local_compose = (repo / "KMFA/app/docker-compose.yml").read_text(
        encoding="utf-8"
    )
    coolify_compose = (
        repo / "KMFA/deploy/coolify/docker-compose.yml"
    ).read_text(encoding="utf-8")
    env_example = (
        repo / "KMFA/deploy/coolify/.env.example"
    ).read_text(encoding="utf-8")
    frontend = (
        repo / "KMFA/app/frontend/src/WalkingSkeleton.jsx"
    ).read_text(encoding="utf-8")
    workflow = (
        repo / ".github/workflows/app-e2e.yml"
    ).read_text(encoding="utf-8")
    for compose in (local_compose, coolify_compose):
        assert (
            "KMFA_RESUMABLE_UPLOAD_ENABLED:"
            ' "${KMFA_RESUMABLE_UPLOAD_ENABLED:-0}"'
        ) in compose
    assert "KMFA_RESUMABLE_UPLOAD_ENABLED=0" in env_example
    assert "application/offset+octet-stream" in frontend
    assert "'Upload-Offset': String(offset)" in frontend
    assert "data-upload-quota=\"visible\"" in frontend
    assert "data-upload-progress=\"visible\"" in frontend
    assert "KMFA/app/e2e/resumable_upload_flow.py" in workflow
    assert "resumable-upload-e2e/" in workflow
