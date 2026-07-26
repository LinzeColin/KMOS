"""S06/P6.2 durable quarantine, retry, rollback, and recovery contracts."""

from __future__ import annotations

import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import pytest
import yaml
from app import file_security_worker
from app import walking_skeleton as skeleton
from app.backup_restore import BackupRestoreError, create_backup, restore_backup
from app.file_security import (
    FileSecurityClient,
    FileSecurityRepository,
    FileSecurityTimeoutError,
    ScanOutcome,
    run_security_scan_once,
)
from app.main import app
from app.retention_lifecycle import (
    DELETE_CONFIRMATION,
    LifecycleRepository,
    RestoreDrillProof,
)
from app.structured_store import (
    SCHEMA_VERSION,
    StructuredStoreIntegrityError,
    open_structured_store,
)
from fastapi.testclient import TestClient

BASE = "/public-api/walking-skeleton/v1"
SECRET = "p62-state-test-shared-secret-32-bytes-minimum"
NOW = datetime(2026, 7, 26, 4, 0, tzinfo=timezone.utc)


@pytest.fixture
def security_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, TestClient]:
    state = tmp_path / "walking-state"
    monkeypatch.setenv("KMFA_WALKING_SKELETON_ENABLED", "1")
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(state))
    monkeypatch.setenv("KMFA_FILE_SECURITY_ENABLED", "1")
    monkeypatch.setenv(
        "KMFA_FILE_SCANNER_URL",
        "http://127.0.0.1:18099/scan",
    )
    monkeypatch.setenv("KMFA_FILE_SCANNER_SHARED_SECRET", SECRET)
    monkeypatch.setenv("KMFA_FILE_SCANNER_TIMEOUT_SECONDS", "0.1")
    monkeypatch.setenv("KMFA_FILE_SCAN_LEASE_SECONDS", "1")
    monkeypatch.setenv("KMFA_FILE_SCAN_RETRY_DELAY_SECONDS", "0")
    monkeypatch.setenv("KMFA_FILE_SCAN_MAX_ATTEMPTS", "3")
    monkeypatch.setenv("KMFA_CONSISTENCY_STATE_MODE", "recoverable-v1")
    monkeypatch.setenv("KMFA_LIFECYCLE_MODE", "paused")
    monkeypatch.delenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", raising=False)
    monkeypatch.delenv("KMFA_STRUCTURED_DATABASE_MODE", raising=False)
    monkeypatch.delenv("KMFA_STRUCTURED_DATABASE_URL", raising=False)
    monkeypatch.delenv("KMFA_ARTIFACT_STORAGE_MODE", raising=False)
    return state, TestClient(
        app,
        base_url="https://testserver",
        headers={"Origin": "https://testserver"},
    )


def _create(client: TestClient) -> dict:
    response = client.post(
        f"{BASE}/workspaces",
        json={"project_name": "P6.2 synthetic security"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _upload(
    client: TestClient,
    workspace_id: str,
    payload: bytes,
    *,
    name: str,
) -> dict:
    response = client.put(
        f"{BASE}/workspaces/{workspace_id}/artifact",
        content=payload,
        headers={
            "Content-Type": "application/octet-stream",
            "Idempotency-Key": "p62-security-upload-idempotency-000001",
            "X-KMFA-Filename": quote(name, safe=""),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _outcome(
    *,
    verdict: str,
    reason: str,
    media_type: str,
) -> ScanOutcome:
    return ScanOutcome(
        verdict=verdict,
        reason_code=reason,
        detected_media_type=media_type,
        scanner_engine="kmfa-bounded-content-firewall",
        scanner_version="1.0",
        policy_version="kmfa-upload-security-v1",
    )


def test_rejected_file_stays_private_blocked_and_durable_across_flag_rollback(
    security_runtime: tuple[Path, TestClient],
    monkeypatch: pytest.MonkeyPatch,
):
    state, client = security_runtime
    monkeypatch.setattr(
        FileSecurityClient,
        "scan",
        lambda self, *args, **kwargs: _outcome(
            verdict="rejected",
            reason="security_malware_eicar",
            media_type="text/plain",
        ),
    )
    created = _create(client)
    workspace_id = created["workspace"]["workspace_id"]
    payload = b"synthetic rejected bytes"
    uploaded = _upload(
        client,
        workspace_id,
        payload,
        name="rejected.synthetic",
    )
    artifact = uploaded["artifact"]
    assert artifact["security"]["state"] == "rejected"
    assert artifact["security"]["reason_code"] == "security_malware_eicar"
    assert artifact["download_allowed"] is False
    assert artifact["preview_allowed"] is False
    assert artifact["security"]["processing_allowed"] is False

    blocked = client.post(
        f"{BASE}/workspaces/{workspace_id}/artifact/download"
    )
    assert blocked.status_code == 409
    assert blocked.json() == {"detail": "artifact_security_rejected"}

    database = sqlite3.connect(state / "walking_skeleton.sqlite3")
    database.row_factory = sqlite3.Row
    try:
        assessment = database.execute(
            "SELECT * FROM artifact_security_assessments"
        ).fetchone()
        events = database.execute(
            "SELECT from_state, to_state FROM artifact_security_events "
            "ORDER BY seq"
        ).fetchall()
        quarantine = database.execute(
            "SELECT state, reason_code FROM object_quarantine "
            "WHERE reason_code = 'security_scan_pending'"
        ).fetchone()
        storage_key = database.execute(
            "SELECT storage_key FROM artifact_versions"
        ).fetchone()["storage_key"]
    finally:
        database.close()
    assert assessment["state"] == "rejected"
    assert assessment["attempt_count"] == 1
    assert [tuple(row) for row in events] == [
        (None, "quarantined"),
        ("quarantined", "scanning"),
        ("scanning", "rejected"),
    ]
    assert tuple(quarantine) == ("isolated", "security_scan_pending")
    assert (state / "objects" / storage_key).read_bytes() == payload

    monkeypatch.setenv("KMFA_FILE_SECURITY_ENABLED", "0")
    rolled_back = client.get(f"{BASE}/workspaces/{workspace_id}")
    assert rolled_back.status_code == 200
    assert rolled_back.json()["artifact"]["security"]["state"] == "rejected"
    assert (
        client.post(
            f"{BASE}/workspaces/{workspace_id}/artifact/download"
        ).status_code
        == 409
    )


def test_timeout_is_not_clean_is_downloadable_as_attachment_and_can_retry(
    security_runtime: tuple[Path, TestClient],
    monkeypatch: pytest.MonkeyPatch,
):
    state, client = security_runtime

    def timeout(*args, **kwargs):
        raise FileSecurityTimeoutError("file_security_scanner_timeout")

    monkeypatch.setattr(FileSecurityClient, "scan", timeout)
    created = _create(client)
    workspace_id = created["workspace"]["workspace_id"]
    payload = b"timeout fixture remains an immutable attachment"
    uploaded = _upload(
        client,
        workspace_id,
        payload,
        name="timeout.unknown",
    )
    security = uploaded["artifact"]["security"]
    assert security["state"] == "timed_out"
    assert security["scan_complete"] is True
    assert security["download_allowed"] is True
    assert security["preview_allowed"] is False

    downloaded = client.post(
        f"{BASE}/workspaces/{workspace_id}/artifact/download"
    )
    assert downloaded.status_code == 200
    assert downloaded.content == payload
    assert downloaded.headers["x-kmfa-artifact-security"] == "timed_out"

    monkeypatch.setattr(
        FileSecurityClient,
        "scan",
        lambda self, *args, **kwargs: _outcome(
            verdict="clean",
            reason="security_scan_clean",
            media_type="text/plain",
        ),
    )
    retried = run_security_scan_once(state_root=state)
    assert retried is not None
    assert retried.state == "clean"
    assert retried.attempt_count == 2
    refreshed = client.get(f"{BASE}/workspaces/{workspace_id}").json()
    assert refreshed["artifact"]["security"]["state"] == "clean"
    assert refreshed["artifact"]["security"]["attempt_count"] == 2

    database = sqlite3.connect(state / "walking_skeleton.sqlite3")
    try:
        states = [
            row[0]
            for row in database.execute(
                "SELECT to_state FROM artifact_security_events ORDER BY seq"
            ).fetchall()
        ]
        quarantine_state = database.execute(
            "SELECT state FROM object_quarantine "
            "WHERE reason_code = 'security_scan_pending'"
        ).fetchone()[0]
    finally:
        database.close()
    assert states == [
        "quarantined",
        "scanning",
        "timed_out",
        "scanning",
        "clean",
    ]
    assert quarantine_state == "released"


def test_pre_p62_artifact_remains_unscanned_attachment_only_after_enable(
    security_runtime: tuple[Path, TestClient],
    monkeypatch: pytest.MonkeyPatch,
):
    state, client = security_runtime
    monkeypatch.setenv("KMFA_FILE_SECURITY_ENABLED", "0")
    created = _create(client)
    workspace_id = created["workspace"]["workspace_id"]
    payload = b"pre-p62 synthetic artifact"
    uploaded = _upload(
        client,
        workspace_id,
        payload,
        name="legacy.unknown",
    )
    assert (
        uploaded["artifact"]["security"]["state"]
        == "unscanned_attachment_only"
    )

    monkeypatch.setenv("KMFA_FILE_SECURITY_ENABLED", "1")
    restored = client.get(f"{BASE}/workspaces/{workspace_id}")
    assert restored.status_code == 200
    security = restored.json()["artifact"]["security"]
    assert security["state"] == "unscanned_attachment_only"
    assert security["download_allowed"] is True
    assert security["preview_allowed"] is False
    assert (
        client.post(
            f"{BASE}/workspaces/{workspace_id}/artifact/download"
        ).content
        == payload
    )
    database = sqlite3.connect(state / "walking_skeleton.sqlite3")
    try:
        assert (
            database.execute(
                "SELECT COUNT(*) FROM artifact_security_assessments"
            ).fetchone()[0]
            == 0
        )
    finally:
        database.close()


def test_scan_claim_is_single_owner_under_concurrency(
    security_runtime: tuple[Path, TestClient],
    monkeypatch: pytest.MonkeyPatch,
):
    state, client = security_runtime
    monkeypatch.setattr(skeleton, "run_security_scan_once", lambda **kwargs: None)
    created = _create(client)
    _upload(
        client,
        created["workspace"]["workspace_id"],
        b"single scanner lease",
        name="lease.txt",
    )

    entered = threading.Event()
    release = threading.Event()

    def held_scan(self, *args, **kwargs):
        entered.set()
        assert release.wait(timeout=5)
        return _outcome(
            verdict="clean",
            reason="security_scan_clean",
            media_type="text/plain",
        )

    monkeypatch.setattr(FileSecurityClient, "scan", held_scan)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(run_security_scan_once, state_root=state)
        assert entered.wait(timeout=5)
        second = executor.submit(run_security_scan_once, state_root=state)
        assert second.result(timeout=5) is None
        release.set()
        assert first.result(timeout=5).state == "clean"

    database = sqlite3.connect(state / "walking_skeleton.sqlite3")
    try:
        assessment = database.execute(
            "SELECT state, attempt_count FROM artifact_security_assessments"
        ).fetchone()
    finally:
        database.close()
    assert assessment == ("clean", 1)


def test_security_state_and_append_only_events_survive_full_restore(
    security_runtime: tuple[Path, TestClient],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    state, client = security_runtime
    monkeypatch.setattr(
        FileSecurityClient,
        "scan",
        lambda self, *args, **kwargs: _outcome(
            verdict="rejected",
            reason="security_malware_eicar",
            media_type="text/plain",
        ),
    )
    created = _create(client)
    _upload(
        client,
        created["workspace"]["workspace_id"],
        b"restore rejected fixture",
        name="restore.synthetic",
    )
    monkeypatch.setenv("KMFA_CONSISTENCY_STATE_MODE", "paused")
    source = open_structured_store(state / "walking_skeleton.sqlite3")
    backup = create_backup(
        connection=source,
        state_root=state,
        destination=tmp_path / "security-backup",
        kind="full",
        artifact_identity="synthetic-source/image-p62",
        backup_id="backup_p62_security_000001",
        now=NOW,
    )
    source.close()

    target = tmp_path / "security-restore"
    target.mkdir()
    restored_connection = open_structured_store(
        target / "walking_skeleton.sqlite3"
    )
    result = restore_backup(
        connection=restored_connection,
        state_root=target,
        chain_directories=(backup.directory,),
        incident_at=NOW + timedelta(seconds=1),
    )
    assert result.invariant_failures == 0
    assessment = restored_connection.execute(
        "SELECT state, reason_code, attempt_count "
        "FROM artifact_security_assessments"
    ).fetchone()
    event_count = restored_connection.execute(
        "SELECT COUNT(*) AS n FROM artifact_security_events"
    ).fetchone()["n"]
    assert tuple(assessment) == (
        "rejected",
        "security_malware_eicar",
        1,
    )
    assert event_count == 3
    with pytest.raises(StructuredStoreIntegrityError):
        restored_connection.execute(
            "UPDATE artifact_security_events SET reason_code = ?",
            ("security_scan_clean",),
        )
    restored_connection.close()


def test_backup_refuses_an_active_security_scan(
    security_runtime: tuple[Path, TestClient],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    state, client = security_runtime
    monkeypatch.setattr(skeleton, "run_security_scan_once", lambda **kwargs: None)
    created = _create(client)
    _upload(
        client,
        created["workspace"]["workspace_id"],
        b"active scanner lease fixture",
        name="active-scan.txt",
    )
    connection = open_structured_store(state / "walking_skeleton.sqlite3")
    with connection.transaction():
        claim = FileSecurityRepository(connection).claim(
            now=NOW,
            lease_seconds=60,
            retry_delay_seconds=0,
            max_attempts=3,
        )
    assert claim is not None
    monkeypatch.setenv("KMFA_CONSISTENCY_STATE_MODE", "paused")
    with pytest.raises(
        BackupRestoreError,
        match="backup_security_scan_pending",
    ):
        create_backup(
            connection=connection,
            state_root=state,
            destination=tmp_path / "must-not-back-up-active-scan",
            kind="full",
            artifact_identity="synthetic-source/image-p62-active",
            backup_id="backup_p62_active_scan_000001",
            now=NOW,
        )
    connection.close()


def test_deletion_and_scanner_claims_are_serialized(
    security_runtime: tuple[Path, TestClient],
    monkeypatch: pytest.MonkeyPatch,
):
    state, client = security_runtime
    monkeypatch.setattr(skeleton, "run_security_scan_once", lambda **kwargs: None)
    created = _create(client)
    workspace_id = created["workspace"]["workspace_id"]
    _upload(
        client,
        workspace_id,
        b"delete and scanner lease fixture",
        name="delete-scan.txt",
    )
    connection = open_structured_store(state / "walking_skeleton.sqlite3")
    with connection.transaction():
        repository = FileSecurityRepository(connection)
        claim = repository.claim(
            now=NOW,
            lease_seconds=60,
            retry_delay_seconds=0,
            max_attempts=3,
        )
        LifecycleRepository(connection).record_restore_proof(
            RestoreDrillProof(
                proof_id="proof_p62_delete_scan",
                backup_id="backup_p62_delete_scan",
                backup_manifest_sha256="a" * 64,
                source_schema_version=SCHEMA_VERSION,
                expected_fixture_count=1,
                restored_fixture_count=1,
                invariant_failures=0,
                measured_rpo_ms=25,
                measured_rto_ms=250,
                artifact_identity_hash="b" * 64,
                verified_at="2026-07-26T04:00:00Z",
            )
        )
    assert claim is not None
    monkeypatch.setenv("KMFA_LIFECYCLE_MODE", "active")
    delete_body = {
        "confirmation": DELETE_CONFIRMATION,
        "workspace_secret": created["recovery_code"],
    }
    delete_headers = {
        "Idempotency-Key": "p62-delete-scan-idempotency-000001",
    }
    blocked = client.request(
        "DELETE",
        f"{BASE}/workspaces/{workspace_id}",
        json=delete_body,
        headers=delete_headers,
    )
    assert blocked.status_code == 409
    assert blocked.json() == {"detail": "deletion_consistency_pending"}

    with connection.transaction():
        FileSecurityRepository(connection).complete(
            claim,
            state="timed_out",
            reason_code="security_scanner_timeout",
            detected_media_type=None,
            scanner_engine=None,
            scanner_version=None,
            policy_version="kmfa-upload-security-v1",
            timestamp="2026-07-26T04:00:01Z",
        )
    accepted = client.request(
        "DELETE",
        f"{BASE}/workspaces/{workspace_id}",
        json=delete_body,
        headers=delete_headers,
    )
    assert accepted.status_code == 202, accepted.text
    with connection.transaction():
        retry_claim = FileSecurityRepository(connection).claim(
            now=NOW + timedelta(minutes=1),
            lease_seconds=60,
            retry_delay_seconds=0,
            max_attempts=3,
        )
    assert retry_claim is None
    assessment = connection.execute(
        "SELECT state, attempt_count FROM artifact_security_assessments"
    ).fetchone()
    retention = connection.execute(
        "SELECT state FROM workspace_retention WHERE workspace_id = ?",
        (workspace_id,),
    ).fetchone()
    assert tuple(assessment) == ("timed_out", 1)
    assert retention["state"] == "deletion_requested"
    connection.close()


def test_disabled_worker_idles_without_compose_restart_loop(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    monkeypatch.setenv("KMFA_FILE_SECURITY_ENABLED", "0")
    monkeypatch.setenv("KMFA_ARTIFACT_DERIVATION_ENABLED", "0")
    assert file_security_worker.main(["--once"]) == 0
    assert '"status": "disabled"' in capsys.readouterr().out

    sleep_calls: list[float] = []

    class StopIdleLoop(RuntimeError):
        pass

    def stop_after_first_idle(seconds: float) -> None:
        sleep_calls.append(seconds)
        raise StopIdleLoop

    monkeypatch.setattr(file_security_worker.time, "sleep", stop_after_first_idle)
    with pytest.raises(StopIdleLoop):
        file_security_worker.main(["--poll-seconds", "0.25"])
    assert sleep_calls == [0.25]


def test_scanner_compose_has_no_data_plane_credentials_or_mounts():
    root = Path(__file__).resolve().parents[4]
    for relative in (
        "KMFA/app/docker-compose.yml",
        "KMFA/deploy/coolify/docker-compose.yml",
    ):
        payload = yaml.safe_load((root / relative).read_text(encoding="utf-8"))
        scanner = payload["services"]["file-security-scanner"]
        assert set(scanner["environment"]) == {
            "KMFA_FILE_SCANNER_SHARED_SECRET"
        }
        assert "volumes" not in scanner
        assert scanner["user"] == "65532:65532"
        assert scanner["read_only"] is True
        assert scanner["cap_drop"] == ["ALL"]
        assert scanner["security_opt"] == ["no-new-privileges:true"]
        assert scanner["networks"] == ["scan-plane"]
        assert payload["networks"]["scan-plane"]["internal"] is True

    source = Path(skeleton.__file__).read_text(encoding="utf-8")
    assert "file_security_policy" not in source
