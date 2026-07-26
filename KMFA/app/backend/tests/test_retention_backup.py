"""S05/P5.4 retention, explicit deletion, backup and restore contracts."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from app import backup_restore as backup_restore_cli
from app import retention_lifecycle
from app import walking_skeleton as skeleton
from app.backup_restore import (
    BackupRestoreError,
    create_backup,
    restore_backup,
)
from app.main import app
from app.object_storage import ObjectStorageUnavailableError
from app.retention_lifecycle import (
    DELETE_CONFIRMATION,
    LifecycleLegalHoldError,
    LifecycleRepository,
    RestoreDrillProof,
    due_deletion_request_ids,
    process_deletion_request,
)
from app.structured_repository import StructuredRepository
from app.structured_store import SCHEMA_VERSION, open_structured_store

BASE = "/public-api/walking-skeleton/v1"
FIXTURE = b"KMFA-P54-SYNTHETIC\x00\xff\n" + bytes(range(256)) * 9
FIXTURE_SHA256 = hashlib.sha256(FIXTURE).hexdigest()
NOW = datetime(2026, 7, 24, 0, 0, tzinfo=timezone.utc)


class MemoryPublicationEffects:
    def __init__(self) -> None:
        self.active: set[str] = set()
        self.cached: set[str] = set()
        self.indexed: set[str] = set()
        self.calls = 0

    def add(self, publication_id: str) -> None:
        self.active.add(publication_id)
        self.cached.add(publication_id)
        self.indexed.add(publication_id)

    def revoke_and_purge(
        self,
        *,
        publication_id: str,
        subject_ref: str,
    ) -> None:
        assert len(subject_ref) == 20
        self.calls += 1
        self.active.discard(publication_id)
        self.cached.discard(publication_id)
        self.indexed.discard(publication_id)


@pytest.fixture
def state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "runtime" / "walking-skeleton"
    root.parent.mkdir()
    monkeypatch.setenv("KMFA_WALKING_SKELETON_ENABLED", "1")
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(root))
    monkeypatch.setenv("KMFA_LIFECYCLE_MODE", "paused")
    monkeypatch.setenv("KMFA_CONSISTENCY_STATE_MODE", "recoverable-v1")
    monkeypatch.delenv("KMFA_STRUCTURED_DATABASE_MODE", raising=False)
    monkeypatch.delenv("KMFA_STRUCTURED_DATABASE_URL", raising=False)
    monkeypatch.setenv("KMFA_ARTIFACT_STORAGE_MODE", "legacy-filesystem")
    monkeypatch.setenv(
        "KMFA_LIFECYCLE_ALLOW_LEGACY_FILESYSTEM_DELETE",
        "1",
    )
    return root


def _proof(
    *,
    proof_id: str = "proof_p54_synthetic",
    backup_id: str = "backup_p54_synthetic",
) -> RestoreDrillProof:
    return RestoreDrillProof(
        proof_id=proof_id,
        backup_id=backup_id,
        backup_manifest_sha256="a" * 64,
        source_schema_version=SCHEMA_VERSION,
        expected_fixture_count=2,
        restored_fixture_count=2,
        invariant_failures=0,
        measured_rpo_ms=75,
        measured_rto_ms=850,
        artifact_identity_hash="b" * 64,
        verified_at=retention_lifecycle.utc_timestamp(),
    )


def _record_proof() -> None:
    with skeleton._store() as connection:
        with connection.transaction():
            LifecycleRepository(connection).record_restore_proof(_proof())


def _create_and_upload(name: str) -> dict[str, object]:
    created = skeleton._create_workspace(name)
    workspace = created["workspace"]
    workspace_id = str(workspace["workspace_id"])
    client = TestClient(app, base_url="https://testserver")
    uploaded = client.put(
        f"{BASE}/workspaces/{workspace_id}/artifact",
        content=FIXTURE,
        headers={
            "Authorization": f"Bearer {created['access_token']}",
            "Idempotency-Key": "p54-upload-idempotency-key-000001",
            "X-KMFA-Filename": quote("p54.synthetic.unknown", safe=""),
            "Content-Type": "application/x-kmfa-synthetic",
        },
    )
    assert uploaded.status_code == 200, uploaded.text
    return created


def _open_for(root: Path):
    return open_structured_store(root / "walking_skeleton.sqlite3")


def test_schema_five_preserves_default_no_expiry_retention(state: Path):
    created = skeleton._create_workspace("P5.4 no-expiry synthetic")
    connection = _open_for(state)
    try:
        assert connection.schema_version() == SCHEMA_VERSION == 5
        retention = connection.execute(
            "SELECT * FROM workspace_retention WHERE workspace_id = ?",
            (created["workspace"]["workspace_id"],),
        ).fetchone()
        assert retention["state"] == "active"
        assert retention["deleted_at"] is None
        assert "expires_at" not in retention.keys()
        assert due_deletion_request_ids(connection, limit=100) == []
    finally:
        connection.close()

    # Moving a virtual clock by a century does not create a lifecycle action.
    connection = _open_for(state)
    try:
        assert due_deletion_request_ids(connection, limit=100) == []
        assert StructuredRepository(connection).workspace_projection(
            str(created["workspace"]["workspace_id"])
        ) is not None
    finally:
        connection.close()


def test_restore_proof_expires_after_quarterly_drill_window(state: Path):
    expired_at = retention_lifecycle.utc_timestamp(
        datetime.now(timezone.utc) - timedelta(days=94)
    )
    connection = _open_for(state)
    try:
        with pytest.raises(
            retention_lifecycle.LifecycleError,
            match="restore_drill_proof_expired",
        ):
            with connection.transaction():
                LifecycleRepository(connection).record_restore_proof(
                    replace(_proof(), verified_at=expired_at)
                )
        assert LifecycleRepository(connection).active_restore_proof() is None
    finally:
        connection.close()


def test_failed_restored_proof_id_cannot_be_reactivated_by_conflicting_replay(
    state: Path,
):
    proof = _proof(proof_id="proof_p54_failed_replay")
    connection = _open_for(state)
    try:
        with connection.transaction():
            repository = LifecycleRepository(connection)
            repository.record_restore_proof(proof)
            connection.execute(
                """
                UPDATE restore_drill_proofs
                SET status = 'failed'
                WHERE proof_id = ?
                """,
                (proof.proof_id,),
            )
        with pytest.raises(
            retention_lifecycle.LifecycleConflictError,
            match="restore_drill_proof_conflict",
        ):
            with connection.transaction():
                LifecycleRepository(connection).record_restore_proof(proof)
    finally:
        connection.close()


def test_record_proof_cli_requires_quiesced_modes_and_persists_gate(
    state: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    arguments = [
        "record-proof",
        "--backup-id",
        "backup_p54_cli_000001",
        "--manifest-sha256",
        "c" * 64,
        "--expected-fixtures",
        "1",
        "--restored-fixtures",
        "1",
        "--invariant-failures",
        "0",
        "--measured-rpo-ms",
        "15",
        "--measured-rto-ms",
        "250",
        "--artifact-identity-hash",
        "d" * 64,
        "--proof-id",
        "proof_p54_cli_000001",
    ]
    assert backup_restore_cli.main(arguments) == 1
    assert '"status": "fail"' in capsys.readouterr().out

    monkeypatch.setenv("KMFA_CONSISTENCY_STATE_MODE", "paused")
    assert backup_restore_cli.main(arguments) == 0
    assert '"status": "pass"' in capsys.readouterr().out
    connection = _open_for(state)
    try:
        proof = LifecycleRepository(connection).active_restore_proof()
        assert proof["proof_id"] == "proof_p54_cli_000001"
    finally:
        connection.close()


def test_delete_api_requires_current_restore_proof_confirmation_and_secret(
    state: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    created = _create_and_upload("P5.4 guarded deletion synthetic")
    workspace_id = str(created["workspace"]["workspace_id"])
    token = str(created["access_token"])
    client = TestClient(app, base_url="https://testserver")
    monkeypatch.setenv("KMFA_LIFECYCLE_MODE", "active")
    body = {
        "confirmation": DELETE_CONFIRMATION,
        "workspace_secret": created["recovery_code"],
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": "p54-delete-idempotency-key-000001",
    }
    no_proof = client.request(
        "DELETE",
        f"{BASE}/workspaces/{workspace_id}",
        json=body,
        headers=headers,
    )
    assert no_proof.status_code == 503
    assert no_proof.json()["detail"] == "deletion_restore_proof_required"

    _record_proof()
    wrong_confirmation = client.request(
        "DELETE",
        f"{BASE}/workspaces/{workspace_id}",
        json={**body, "confirmation": "delete-something-else"},
        headers=headers,
    )
    assert wrong_confirmation.status_code == 422
    wrong_secret = client.request(
        "DELETE",
        f"{BASE}/workspaces/{workspace_id}",
        json={**body, "workspace_secret": "kmfa-r1-" + "0" * 43},
        headers=headers,
    )
    assert wrong_secret.status_code == 404
    missing_key = client.request(
        "DELETE",
        f"{BASE}/workspaces/{workspace_id}",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert missing_key.status_code == 422

    accepted = client.request(
        "DELETE",
        f"{BASE}/workspaces/{workspace_id}",
        json=body,
        headers=headers,
    )
    assert accepted.status_code == 202, accepted.text
    assert accepted.json()["access_revoked"] is True
    assert accepted.json()["default_retention_expiry"] is None
    assert skeleton.SESSION_COOKIE_NAME in accepted.headers["set-cookie"]
    assert "Max-Age=0" in accepted.headers["set-cookie"]
    request_id = str(accepted.json()["deletion_request_id"])
    immediate_replay = client.request(
        "DELETE",
        f"{BASE}/workspaces/{workspace_id}",
        json=body,
        headers=headers,
    )
    assert immediate_replay.status_code == 202
    assert immediate_replay.json()["deletion_request_id"] == request_id
    assert immediate_replay.json()["status"] == "accepted"
    mismatched_replay = client.request(
        "DELETE",
        f"{BASE}/workspaces/{workspace_id}",
        json={**body, "workspace_secret": "kmfa-r1-" + "0" * 43},
        headers=headers,
    )
    assert mismatched_replay.status_code == 404
    denied = client.get(
        f"{BASE}/workspaces/{workspace_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert denied.status_code == 404
    completed = process_deletion_request(
        open_connection=lambda: _open_for(state),
        state_root=state,
        deletion_request_id=request_id,
    )
    assert completed["state"] == "completed"
    completed_replay = client.request(
        "DELETE",
        f"{BASE}/workspaces/{workspace_id}",
        json=body,
        headers=headers,
    )
    assert completed_replay.status_code == 202
    assert completed_replay.json()["deletion_request_id"] == request_id
    assert completed_replay.json()["status"] == "completed"


def test_legal_hold_blocks_without_revoking_owner_then_release_allows_delete(
    state: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    created = _create_and_upload("P5.4 legal hold synthetic")
    workspace_id = str(created["workspace"]["workspace_id"])
    token = str(created["access_token"])
    _record_proof()
    connection = _open_for(state)
    try:
        with connection.transaction():
            hold_id = LifecycleRepository(connection).impose_legal_hold(
                workspace_id=workspace_id,
                reason_code="legal",
                authority_ref="synthetic-authority-reference",
                timestamp="2026-07-24T00:00:00Z",
            )
    finally:
        connection.close()
    monkeypatch.setenv("KMFA_LIFECYCLE_MODE", "active")
    client = TestClient(app, base_url="https://testserver")
    request = client.request(
        "DELETE",
        f"{BASE}/workspaces/{workspace_id}",
        json={
            "confirmation": DELETE_CONFIRMATION,
            "workspace_secret": created["recovery_code"],
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "p54-delete-hold-idempotency-00001",
        },
    )
    assert request.status_code == 409
    assert request.json()["detail"] == "workspace_legal_hold"
    assert (
        client.get(
            f"{BASE}/workspaces/{workspace_id}",
            headers={"Authorization": f"Bearer {token}"},
        ).status_code
        == 200
    )
    connection = _open_for(state)
    try:
        with connection.transaction():
            LifecycleRepository(connection).release_legal_hold(
                hold_id=hold_id,
                timestamp="2026-07-24T00:01:00Z",
            )
    finally:
        connection.close()
    allowed = client.request(
        "DELETE",
        f"{BASE}/workspaces/{workspace_id}",
        json={
            "confirmation": DELETE_CONFIRMATION,
            "workspace_secret": created["recovery_code"],
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "p54-delete-hold-idempotency-00001",
        },
    )
    assert allowed.status_code == 202


def test_worker_revokes_public_effects_deletes_exact_object_and_scrubs_content(
    state: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    created = _create_and_upload("P5.4 public deletion synthetic")
    workspace_id = str(created["workspace"]["workspace_id"])
    _record_proof()
    effects = MemoryPublicationEffects()
    effects.add("publication_p54_synthetic")
    connection = _open_for(state)
    try:
        with connection.transaction():
            repository = LifecycleRepository(connection)
            repository.register_publication(
                publication_id="publication_p54_synthetic",
                workspace_id=workspace_id,
                subject_identity="synthetic-public-subject",
                timestamp="2026-07-24T00:00:00Z",
            )
    finally:
        connection.close()
    monkeypatch.setenv("KMFA_LIFECYCLE_MODE", "active")
    client = TestClient(app, base_url="https://testserver")
    requested = client.request(
        "DELETE",
        f"{BASE}/workspaces/{workspace_id}",
        json={
            "confirmation": DELETE_CONFIRMATION,
            "workspace_secret": created["recovery_code"],
        },
        headers={
            "Authorization": f"Bearer {created['access_token']}",
            "Idempotency-Key": "p54-delete-public-idempotency-0001",
        },
    )
    assert requested.status_code == 202
    request_id = str(requested.json()["deletion_request_id"])
    connection = _open_for(state)
    try:
        requested_at = connection.execute(
            """
            SELECT requested_at
            FROM deletion_requests
            WHERE deletion_request_id = ?
            """,
            (request_id,),
        ).fetchone()["requested_at"]
    finally:
        connection.close()
    worker_now = datetime.fromisoformat(
        str(requested_at).replace("Z", "+00:00")
    ) + timedelta(seconds=45)
    result = process_deletion_request(
        open_connection=lambda: _open_for(state),
        state_root=state,
        deletion_request_id=request_id,
        publication_effects=effects,
        now=worker_now,
    )
    assert result["state"] == "completed"
    assert effects.calls == 1
    assert effects.active == effects.cached == effects.indexed == set()
    assert not list((state / "objects").glob("*.blob"))

    connection = _open_for(state)
    try:
        retention = connection.execute(
            "SELECT * FROM workspace_retention WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()
        deletion = connection.execute(
            "SELECT * FROM deletion_requests WHERE deletion_request_id = ?",
            (request_id,),
        ).fetchone()
        assert retention["state"] == "deleted"
        assert deletion["state"] == "completed"
        assert (
            datetime.fromisoformat(
                str(deletion["public_purged_at"]).replace("Z", "+00:00")
            )
            <= datetime.fromisoformat(
                str(deletion["public_purge_due_at"]).replace("Z", "+00:00")
            )
        )
        assert connection.execute(
            "SELECT COUNT(*) AS n FROM projects WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()["n"] == 0
        assert connection.execute(
            "SELECT COUNT(*) AS n FROM artifacts WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()["n"] == 0
        operations = connection.execute(
            """
            SELECT original_name, size_bytes, content_sha256, storage_key
            FROM consistency_operations WHERE workspace_id = ?
            """,
            (workspace_id,),
        ).fetchall()
        assert all(row["original_name"] == "deleted" for row in operations)
        assert all(row["size_bytes"] == 0 for row in operations)
        assert all(row["content_sha256"] == "0" * 64 for row in operations)
        assert all(str(row["storage_key"]).startswith("deleted/") for row in operations)
        target = connection.execute(
            """
            SELECT artifact_id, storage_key, size_bytes, sha256
            FROM deletion_object_targets
            WHERE deletion_request_id = ?
            """,
            (request_id,),
        ).fetchone()
        assert str(target["artifact_id"]).startswith("deleted_")
        assert str(target["storage_key"]).startswith("deleted/")
        assert target["size_bytes"] == 0
        assert target["sha256"] == "0" * 64
        assert connection.execute(
            """
            SELECT COUNT(*) AS n FROM lifecycle_events
            WHERE deletion_request_id = ?
              AND action = 'workspace_deletion_completed'
            """,
            (request_id,),
        ).fetchone()["n"] == 1
    finally:
        connection.close()
    with pytest.raises(skeleton.SkeletonError) as recovery:
        skeleton._recover_workspace(str(created["recovery_code"]))
    assert recovery.value.code == "recovery_not_found"

    # Re-running the completed request has no additional external or object effect.
    replay = process_deletion_request(
        open_connection=lambda: _open_for(state),
        state_root=state,
        deletion_request_id=request_id,
        publication_effects=effects,
        now=worker_now + timedelta(seconds=5),
    )
    assert replay["state"] == "completed"
    assert effects.calls == 1


def test_worker_lease_prevents_overlap_and_allows_stale_recovery(
    state: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    created = _create_and_upload("P5.4 worker lease synthetic")
    _record_proof()
    monkeypatch.setenv("KMFA_LIFECYCLE_MODE", "active")
    requested = TestClient(app, base_url="https://testserver").request(
        "DELETE",
        (
            f"{BASE}/workspaces/"
            f"{created['workspace']['workspace_id']}"
        ),
        json={
            "confirmation": DELETE_CONFIRMATION,
            "workspace_secret": created["recovery_code"],
        },
        headers={
            "Authorization": f"Bearer {created['access_token']}",
            "Idempotency-Key": "p54-delete-worker-lease-00000001",
        },
    )
    assert requested.status_code == 202
    request_id = str(requested.json()["deletion_request_id"])

    connection = _open_for(state)
    try:
        request = connection.execute(
            """
            SELECT requested_at
            FROM deletion_requests
            WHERE deletion_request_id = ?
            """,
            (request_id,),
        ).fetchone()
        claim_at = retention_lifecycle.parse_timestamp(
            str(request["requested_at"])
        ) + timedelta(seconds=1)
        with connection.transaction():
            claimed = LifecycleRepository(connection).claim_request(
                request_id,
                timestamp=retention_lifecycle.utc_timestamp(claim_at),
            )
        assert claimed["state"] == "revoking"
        assert due_deletion_request_ids(
            connection,
            limit=100,
            now=claim_at
            + retention_lifecycle.DELETION_WORKER_LEASE
            - timedelta(seconds=1),
        ) == []
    finally:
        connection.close()

    with pytest.raises(
        retention_lifecycle.LifecycleWorkerBusyError,
        match="deletion_request_lease_active",
    ):
        process_deletion_request(
            open_connection=lambda: _open_for(state),
            state_root=state,
            deletion_request_id=request_id,
            now=claim_at + timedelta(seconds=2),
        )
    stale_at = (
        claim_at
        + retention_lifecycle.DELETION_WORKER_LEASE
        + timedelta(seconds=1)
    )
    connection = _open_for(state)
    try:
        assert due_deletion_request_ids(
            connection,
            limit=100,
            now=stale_at,
        ) == [request_id]
        unchanged = connection.execute(
            """
            SELECT state, attempt_count, last_error_code
            FROM deletion_requests
            WHERE deletion_request_id = ?
            """,
            (request_id,),
        ).fetchone()
        assert dict(unchanged) == {
            "state": "revoking",
            "attempt_count": 1,
            "last_error_code": None,
        }
    finally:
        connection.close()
    recovered = process_deletion_request(
        open_connection=lambda: _open_for(state),
        state_root=state,
        deletion_request_id=request_id,
        now=stale_at,
    )
    assert recovered["state"] == "completed"
    assert recovered["attempt_count"] == 2


def test_public_purge_uses_completion_time_and_blocks_late_delete(
    state: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    created = _create_and_upload("P5.4 public purge SLA synthetic")
    workspace_id = str(created["workspace"]["workspace_id"])
    _record_proof()
    effects = MemoryPublicationEffects()
    effects.add("publication_p54_late")
    connection = _open_for(state)
    try:
        with connection.transaction():
            LifecycleRepository(connection).register_publication(
                publication_id="publication_p54_late",
                workspace_id=workspace_id,
                subject_identity="synthetic-late-public-subject",
                timestamp=retention_lifecycle.utc_timestamp(),
            )
    finally:
        connection.close()
    monkeypatch.setenv("KMFA_LIFECYCLE_MODE", "active")
    requested = TestClient(app, base_url="https://testserver").request(
        "DELETE",
        f"{BASE}/workspaces/{workspace_id}",
        json={
            "confirmation": DELETE_CONFIRMATION,
            "workspace_secret": created["recovery_code"],
        },
        headers={
            "Authorization": f"Bearer {created['access_token']}",
            "Idempotency-Key": "p54-delete-public-late-00000001",
        },
    )
    assert requested.status_code == 202
    request_id = str(requested.json()["deletion_request_id"])
    connection = _open_for(state)
    try:
        request = connection.execute(
            """
            SELECT requested_at, public_purge_due_at
            FROM deletion_requests
            WHERE deletion_request_id = ?
            """,
            (request_id,),
        ).fetchone()
        requested_at = retention_lifecycle.parse_timestamp(
            str(request["requested_at"])
        )
        purge_due = retention_lifecycle.parse_timestamp(
            str(request["public_purge_due_at"])
        )
    finally:
        connection.close()
    late_at = purge_due + timedelta(seconds=1)
    clock_values = iter((requested_at + timedelta(seconds=1), late_at, late_at))

    with pytest.raises(
        retention_lifecycle.LifecycleWorkerError,
        match="public_purge_sla_exceeded",
    ):
        process_deletion_request(
            open_connection=lambda: _open_for(state),
            state_root=state,
            deletion_request_id=request_id,
            publication_effects=effects,
            clock=lambda: next(clock_values),
        )
    assert effects.active == effects.cached == effects.indexed == set()
    assert len(list((state / "objects").glob("*.blob"))) == 1
    connection = _open_for(state)
    try:
        deletion = connection.execute(
            """
            SELECT state, last_error_code, public_purged_at
            FROM deletion_requests
            WHERE deletion_request_id = ?
            """,
            (request_id,),
        ).fetchone()
        assert deletion["state"] == "retry"
        assert deletion["last_error_code"] == "public_purge_sla_exceeded"
        assert retention_lifecycle.parse_timestamp(
            str(deletion["public_purged_at"])
        ) > purge_due
        target = connection.execute(
            """
            SELECT state, attempt_count
            FROM deletion_object_targets
            WHERE deletion_request_id = ?
            """,
            (request_id,),
        ).fetchone()
        assert dict(target) == {"state": "pending", "attempt_count": 0}
        assert connection.execute(
            "SELECT COUNT(*) AS n FROM projects WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()["n"] == 1
        assert connection.execute(
            """
            SELECT COUNT(*) AS n
            FROM lifecycle_events
            WHERE deletion_request_id = ?
              AND action = 'public_cache_index_revoked'
              AND result_status = 'sla_exceeded'
            """,
            (request_id,),
        ).fetchone()["n"] == 1
        assert due_deletion_request_ids(connection, limit=100) == []
    finally:
        connection.close()


def test_hold_imposed_after_request_blocks_before_irreversible_delete(
    state: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    created = _create_and_upload("P5.4 hold race synthetic")
    workspace_id = str(created["workspace"]["workspace_id"])
    _record_proof()
    monkeypatch.setenv("KMFA_LIFECYCLE_MODE", "active")
    requested = TestClient(app, base_url="https://testserver").request(
        "DELETE",
        f"{BASE}/workspaces/{workspace_id}",
        json={
            "confirmation": DELETE_CONFIRMATION,
            "workspace_secret": created["recovery_code"],
        },
        headers={
            "Authorization": f"Bearer {created['access_token']}",
            "Idempotency-Key": "p54-delete-late-hold-idempotency-01",
        },
    )
    assert requested.status_code == 202
    request_id = str(requested.json()["deletion_request_id"])

    connection = _open_for(state)
    try:
        with connection.transaction():
            hold_id = LifecycleRepository(connection).impose_legal_hold(
                workspace_id=workspace_id,
                reason_code="regulatory",
                authority_ref="synthetic-late-hold-authority",
                timestamp="2026-07-24T00:00:05Z",
            )
        request = connection.execute(
            """
            SELECT state
            FROM deletion_requests
            WHERE deletion_request_id = ?
            """,
            (request_id,),
        ).fetchone()
        assert request["state"] == "blocked_hold"
        assert due_deletion_request_ids(connection, limit=100) == []
    finally:
        connection.close()

    with pytest.raises(LifecycleLegalHoldError):
        process_deletion_request(
            open_connection=lambda: _open_for(state),
            state_root=state,
            deletion_request_id=request_id,
            now=NOW + timedelta(seconds=10),
        )
    assert len(list((state / "objects").glob("*.blob"))) == 1

    connection = _open_for(state)
    try:
        assert connection.execute(
            "SELECT COUNT(*) AS n FROM projects WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()["n"] == 1
        with connection.transaction():
            LifecycleRepository(connection).release_legal_hold(
                hold_id=hold_id,
                timestamp="2026-07-24T00:00:15Z",
            )
        assert due_deletion_request_ids(connection, limit=100) == [request_id]
    finally:
        connection.close()
    completed = process_deletion_request(
        open_connection=lambda: _open_for(state),
        state_root=state,
        deletion_request_id=request_id,
        now=NOW + timedelta(seconds=20),
    )
    assert completed["state"] == "completed"


def test_hold_race_blocks_zero_object_workspace_at_final_transaction(
    state: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    created = skeleton._create_workspace("P5.4 zero-object hold race synthetic")
    workspace_id = str(created["workspace"]["workspace_id"])
    _record_proof()
    connection = _open_for(state)
    try:
        with connection.transaction():
            LifecycleRepository(connection).register_publication(
                publication_id="publication_zero_object_hold_race",
                workspace_id=workspace_id,
                subject_identity="synthetic-zero-object-publication",
                timestamp="2026-07-24T00:00:00Z",
            )
    finally:
        connection.close()

    monkeypatch.setenv("KMFA_LIFECYCLE_MODE", "active")
    requested = TestClient(app, base_url="https://testserver").request(
        "DELETE",
        f"{BASE}/workspaces/{workspace_id}",
        json={
            "confirmation": DELETE_CONFIRMATION,
            "workspace_secret": created["recovery_code"],
        },
        headers={
            "Authorization": f"Bearer {created['access_token']}",
            "Idempotency-Key": "p54-zero-object-hold-race-00001",
        },
    )
    assert requested.status_code == 202
    request_id = str(requested.json()["deletion_request_id"])

    class HoldDuringPublicPurge:
        def revoke_and_purge(
            self,
            *,
            publication_id: str,
            subject_ref: str,
        ) -> None:
            assert publication_id == "publication_zero_object_hold_race"
            assert len(subject_ref) == 20
            hold_connection = _open_for(state)
            try:
                with hold_connection.transaction():
                    LifecycleRepository(hold_connection).impose_legal_hold(
                        workspace_id=workspace_id,
                        reason_code="security",
                        authority_ref="synthetic-finalization-race-authority",
                        timestamp="2026-07-24T00:00:05Z",
                    )
            finally:
                hold_connection.close()

    with pytest.raises(LifecycleLegalHoldError):
        process_deletion_request(
            open_connection=lambda: _open_for(state),
            state_root=state,
            deletion_request_id=request_id,
            publication_effects=HoldDuringPublicPurge(),
            now=NOW + timedelta(seconds=10),
        )

    connection = _open_for(state)
    try:
        request = connection.execute(
            """
            SELECT state, completed_at
            FROM deletion_requests
            WHERE deletion_request_id = ?
            """,
            (request_id,),
        ).fetchone()
        assert dict(request) == {
            "state": "blocked_hold",
            "completed_at": None,
        }
        assert connection.execute(
            "SELECT COUNT(*) AS n FROM projects WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()["n"] == 1
    finally:
        connection.close()


def test_worker_retry_is_durable_and_never_scrubs_before_object_delete(
    state: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    created = _create_and_upload("P5.4 retry synthetic")
    workspace_id = str(created["workspace"]["workspace_id"])
    _record_proof()
    monkeypatch.setenv("KMFA_LIFECYCLE_MODE", "active")
    client = TestClient(app, base_url="https://testserver")
    requested = client.request(
        "DELETE",
        f"{BASE}/workspaces/{workspace_id}",
        json={
            "confirmation": DELETE_CONFIRMATION,
            "workspace_secret": created["recovery_code"],
        },
        headers={
            "Authorization": f"Bearer {created['access_token']}",
            "Idempotency-Key": "p54-delete-retry-idempotency-00001",
        },
    )
    request_id = str(requested.json()["deletion_request_id"])

    class FailingDeleteStore:
        def delete_all_versions(self, **_: object) -> int:
            raise ObjectStorageUnavailableError("object_store_unavailable")

    original_factory = retention_lifecycle.lifecycle_store_for_backend
    monkeypatch.setattr(
        retention_lifecycle,
        "lifecycle_store_for_backend",
        lambda *_: FailingDeleteStore(),
    )
    with pytest.raises(retention_lifecycle.LifecycleWorkerError):
        process_deletion_request(
            open_connection=lambda: _open_for(state),
            state_root=state,
            deletion_request_id=request_id,
            now=NOW,
        )
    connection = _open_for(state)
    try:
        request = connection.execute(
            "SELECT state, attempt_count FROM deletion_requests "
            "WHERE deletion_request_id = ?",
            (request_id,),
        ).fetchone()
        target = connection.execute(
            "SELECT state, attempt_count FROM deletion_object_targets "
            "WHERE deletion_request_id = ?",
            (request_id,),
        ).fetchone()
        assert dict(request) == {"state": "retry", "attempt_count": 1}
        assert dict(target) == {"state": "deleting", "attempt_count": 1}
        assert connection.execute(
            "SELECT COUNT(*) AS n FROM projects WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()["n"] == 1
    finally:
        connection.close()
    assert len(list((state / "objects").glob("*.blob"))) == 1

    monkeypatch.setattr(
        retention_lifecycle,
        "lifecycle_store_for_backend",
        original_factory,
    )
    completed = process_deletion_request(
        open_connection=lambda: _open_for(state),
        state_root=state,
        deletion_request_id=request_id,
        now=NOW + timedelta(seconds=10),
    )
    assert completed["state"] == "completed"


def test_first_attempt_missing_object_is_not_misclassified_as_crash_replay(
    state: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    created = _create_and_upload("P5.4 unexplained missing synthetic")
    workspace_id = str(created["workspace"]["workspace_id"])
    _record_proof()
    monkeypatch.setenv("KMFA_LIFECYCLE_MODE", "active")
    requested = TestClient(app, base_url="https://testserver").request(
        "DELETE",
        f"{BASE}/workspaces/{workspace_id}",
        json={
            "confirmation": DELETE_CONFIRMATION,
            "workspace_secret": created["recovery_code"],
        },
        headers={
            "Authorization": f"Bearer {created['access_token']}",
            "Idempotency-Key": "p54-delete-missing-idempotency-0001",
        },
    )
    request_id = str(requested.json()["deletion_request_id"])
    object_path = next((state / "objects").glob("*.blob"))
    object_path.unlink()

    with pytest.raises(retention_lifecycle.LifecycleWorkerError):
        process_deletion_request(
            open_connection=lambda: _open_for(state),
            state_root=state,
            deletion_request_id=request_id,
            now=NOW,
        )
    connection = _open_for(state)
    try:
        request = connection.execute(
            """
            SELECT state
            FROM deletion_requests
            WHERE deletion_request_id = ?
            """,
            (request_id,),
        ).fetchone()
        target = connection.execute(
            """
            SELECT state, last_error_code
            FROM deletion_object_targets
            WHERE deletion_request_id = ?
            """,
            (request_id,),
        ).fetchone()
        assert request["state"] == "retry"
        assert target["state"] == "deleting"
        assert target["last_error_code"] == "object_missing_before_delete"
        assert connection.execute(
            "SELECT COUNT(*) AS n FROM projects WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()["n"] == 1
    finally:
        connection.close()
    with pytest.raises(retention_lifecycle.LifecycleWorkerError):
        process_deletion_request(
            open_connection=lambda: _open_for(state),
            state_root=state,
            deletion_request_id=request_id,
            now=NOW + timedelta(seconds=1),
        )


def test_full_incremental_restore_and_deletion_tombstone_prevent_resurrection(
    state: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    created = _create_and_upload("P5.4 backup source synthetic")
    workspace_id = str(created["workspace"]["workspace_id"])
    recovery_code = str(created["recovery_code"])
    source = _open_for(state)
    monkeypatch.setenv("KMFA_CONSISTENCY_STATE_MODE", "paused")
    full_dir = tmp_path / "backup-full"
    full = create_backup(
        connection=source,
        state_root=state,
        destination=full_dir,
        kind="full",
        artifact_identity="synthetic-commit/image-p54",
        backup_id="backup_p54_full_000001",
        now=NOW,
    )
    source.close()

    monkeypatch.setenv("KMFA_CONSISTENCY_STATE_MODE", "recoverable-v1")
    skeleton._update_workspace(
        workspace_id,
        f"Bearer {created['access_token']}",
        skeleton.UpdateWorkspaceRequest(progress=73),
    )
    monkeypatch.setenv("KMFA_CONSISTENCY_STATE_MODE", "paused")
    source = _open_for(state)
    incremental_dir = tmp_path / "backup-incremental"
    incremental = create_backup(
        connection=source,
        state_root=state,
        destination=incremental_dir,
        kind="incremental",
        parent_chain=(full_dir,),
        artifact_identity="synthetic-commit/image-p54",
        backup_id="backup_p54_incremental_000001",
        now=NOW + timedelta(seconds=30),
    )
    source_hash = StructuredRepository(source).workspace_snapshot_hash(workspace_id)
    source.close()
    assert full.object_upserts == 1
    assert incremental.table_upserts > 0
    assert incremental.object_upserts == 0

    target = tmp_path / "restore-target"
    target.mkdir()
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(target))
    target_connection = _open_for(target)
    restored = restore_backup(
        connection=target_connection,
        state_root=target,
        chain_directories=(full_dir, incremental_dir),
        incident_at=NOW + timedelta(seconds=35),
    )
    assert restored.invariant_failures == 0
    assert restored.restored_objects == 1
    assert restored.measured_rpo_ms == 5000
    assert StructuredRepository(target_connection).workspace_snapshot_hash(
        workspace_id
    ) == source_hash
    assert target_connection.execute(
        "SELECT COUNT(*) AS n FROM access_tokens"
    ).fetchone()["n"] == 0
    with pytest.raises(skeleton.SkeletonError) as restored_session:
        skeleton._get_workspace(
            workspace_id,
            f"Bearer {created['access_token']}",
        )
    assert restored_session.value.code == "workspace_not_found"
    with target_connection.transaction():
        LifecycleRepository(target_connection).record_restore_proof(
            RestoreDrillProof(
                proof_id="proof_p54_restored_target",
                backup_id=restored.backup_id,
                backup_manifest_sha256=restored.manifest_sha256,
                source_schema_version=SCHEMA_VERSION,
                expected_fixture_count=1,
                restored_fixture_count=1,
                invariant_failures=restored.invariant_failures,
                measured_rpo_ms=restored.measured_rpo_ms,
                measured_rto_ms=restored.measured_rto_ms,
                artifact_identity_hash=restored.artifact_identity_hash,
                verified_at=retention_lifecycle.utc_timestamp(),
            )
        )
    target_connection.close()
    recovered = skeleton._recover_workspace(recovery_code)
    assert recovered["workspace"]["progress"] == 73
    downloaded = TestClient(app, base_url="https://testserver").post(
        f"{BASE}/workspaces/{workspace_id}/artifact/download",
        headers={"Authorization": f"Bearer {recovered['access_token']}"},
    )
    assert downloaded.status_code == 200
    assert downloaded.content == FIXTURE

    monkeypatch.setenv("KMFA_LIFECYCLE_MODE", "active")
    deletion = TestClient(app, base_url="https://testserver").request(
        "DELETE",
        f"{BASE}/workspaces/{workspace_id}",
        json={
            "confirmation": DELETE_CONFIRMATION,
            "workspace_secret": recovery_code,
        },
        headers={
            "Authorization": f"Bearer {recovered['access_token']}",
            "Idempotency-Key": "p54-delete-before-incremental-0001",
        },
    )
    assert deletion.status_code == 202
    process_deletion_request(
        open_connection=lambda: _open_for(target),
        state_root=target,
        deletion_request_id=str(deletion.json()["deletion_request_id"]),
        now=NOW + timedelta(seconds=75),
    )

    monkeypatch.setenv("KMFA_LIFECYCLE_MODE", "paused")
    monkeypatch.setenv("KMFA_CONSISTENCY_STATE_MODE", "paused")
    target_connection = _open_for(target)
    tombstone_dir = tmp_path / "backup-tombstone"
    tombstone = create_backup(
        connection=target_connection,
        state_root=target,
        destination=tombstone_dir,
        kind="incremental",
        parent_chain=(full_dir, incremental_dir),
        artifact_identity="synthetic-commit/image-p54",
        backup_id="backup_p54_incremental_000002",
        now=NOW + timedelta(seconds=90),
    )
    target_connection.close()
    assert tombstone.object_deletes == 1

    final_target = tmp_path / "restore-final-target"
    final_target.mkdir()
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(final_target))
    final_connection = _open_for(final_target)
    final_restore = restore_backup(
        connection=final_connection,
        state_root=final_target,
        chain_directories=(full_dir, incremental_dir, tombstone_dir),
        incident_at=NOW + timedelta(seconds=95),
    )
    assert final_restore.invariant_failures == 0
    assert final_restore.restored_objects == 0
    retention = final_connection.execute(
        "SELECT state FROM workspace_retention WHERE workspace_id = ?",
        (workspace_id,),
    ).fetchone()
    assert retention["state"] == "deleted"
    assert final_connection.execute(
        "SELECT COUNT(*) AS n FROM projects WHERE workspace_id = ?",
        (workspace_id,),
    ).fetchone()["n"] == 0
    assert not list((final_target / "objects").glob("*.blob"))
    assert final_connection.execute(
        "SELECT COUNT(*) AS n FROM restore_drill_proofs WHERE status = 'passed'"
    ).fetchone()["n"] == 0
    final_connection.close()
    with pytest.raises(skeleton.SkeletonError):
        skeleton._recover_workspace(recovery_code)


def test_backup_fails_closed_on_non_quiesced_writes_or_nested_destination(
    state: Path,
    tmp_path: Path,
):
    skeleton._create_workspace("P5.4 unsafe backup synthetic")
    connection = _open_for(state)
    with pytest.raises(BackupRestoreError, match="quiesced"):
        create_backup(
            connection=connection,
            state_root=state,
            destination=tmp_path / "unsafe-backup",
            kind="full",
            artifact_identity="synthetic",
        )
    connection.close()


def test_backup_blocks_nonterminal_consistency_operation(
    state: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _create_and_upload("P5.4 pending consistency backup synthetic")
    monkeypatch.setenv("KMFA_CONSISTENCY_STATE_MODE", "paused")
    connection = _open_for(state)
    try:
        with connection.transaction():
            connection.execute(
                """
                UPDATE consistency_operations
                SET state = 'commit_pending'
                """
            )
        destination = tmp_path / "backup-must-not-start"
        with pytest.raises(
            BackupRestoreError,
            match="backup_consistency_operations_pending",
        ):
            create_backup(
                connection=connection,
                state_root=state,
                destination=destination,
                kind="full",
                artifact_identity="synthetic-pending-consistency",
                backup_id="backup_p54_pending_000001",
                now=NOW,
            )
        assert not destination.exists()
    finally:
        connection.close()


def test_empty_object_backup_refuses_restore_over_untracked_target_bytes(
    state: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    skeleton._create_workspace("P5.4 empty-object backup synthetic")
    monkeypatch.setenv("KMFA_CONSISTENCY_STATE_MODE", "paused")
    source = _open_for(state)
    backup_dir = tmp_path / "backup-empty-objects"
    create_backup(
        connection=source,
        state_root=state,
        destination=backup_dir,
        kind="full",
        artifact_identity="synthetic-empty-object-restore",
        backup_id="backup_p54_empty_000001",
        now=NOW,
    )
    source.close()

    target = tmp_path / "restore-not-empty"
    objects = target / "objects"
    objects.mkdir(parents=True)
    (objects / "untracked.blob").write_bytes(b"must-not-be-overwritten")
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(target))
    target_connection = _open_for(target)
    with pytest.raises(BackupRestoreError, match="restore_object_target_not_empty"):
        restore_backup(
            connection=target_connection,
            state_root=target,
            chain_directories=(backup_dir,),
            incident_at=NOW + timedelta(seconds=1),
        )
    target_connection.close()
    assert (objects / "untracked.blob").read_bytes() == b"must-not-be-overwritten"


def test_restore_rejects_bundle_and_blob_symlinks(
    state: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _create_and_upload("P5.4 backup symlink synthetic")
    monkeypatch.setenv("KMFA_CONSISTENCY_STATE_MODE", "paused")
    source = _open_for(state)
    backup_dir = tmp_path / "backup-real"
    create_backup(
        connection=source,
        state_root=state,
        destination=backup_dir,
        kind="full",
        artifact_identity="synthetic-symlink-restore",
        backup_id="backup_p54_symlink_000001",
        now=NOW,
    )
    source.close()

    target = tmp_path / "restore-symlink-target"
    target.mkdir()
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(target))
    target_connection = _open_for(target)
    bundle_link = tmp_path / "backup-bundle-link"
    bundle_link.symlink_to(backup_dir, target_is_directory=True)
    with pytest.raises(BackupRestoreError, match="backup_bundle_unavailable"):
        restore_backup(
            connection=target_connection,
            state_root=target,
            chain_directories=(bundle_link,),
            incident_at=NOW + timedelta(seconds=1),
        )

    blob = next((backup_dir / "objects").glob("*.blob"))
    external_blob = tmp_path / "external-backup-object.blob"
    external_blob.write_bytes(blob.read_bytes())
    blob.unlink()
    blob.symlink_to(external_blob)
    with pytest.raises(
        BackupRestoreError,
        match="backup_object_blob_invalid",
    ):
        restore_backup(
            connection=target_connection,
            state_root=target,
            chain_directories=(backup_dir,),
            incident_at=NOW + timedelta(seconds=1),
        )
    assert not list((target / "objects").glob("*.blob"))
    target_connection.close()


def test_restore_rejects_invalid_or_pre_recovery_incident_time(
    state: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    skeleton._create_workspace("P5.4 incident time synthetic")
    monkeypatch.setenv("KMFA_CONSISTENCY_STATE_MODE", "paused")
    source = _open_for(state)
    backup_dir = tmp_path / "backup-incident-time"
    create_backup(
        connection=source,
        state_root=state,
        destination=backup_dir,
        kind="full",
        artifact_identity="synthetic-incident-time",
        backup_id="backup_p54_incident_000001",
        now=NOW,
    )
    source.close()

    target = tmp_path / "restore-incident-target"
    target.mkdir()
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(target))
    target_connection = _open_for(target)
    with pytest.raises(
        BackupRestoreError,
        match="backup_incident_timestamp_invalid",
    ):
        restore_backup(
            connection=target_connection,
            state_root=target,
            chain_directories=(backup_dir,),
            incident_at=datetime(2026, 7, 24, 0, 0),
        )
    with pytest.raises(
        BackupRestoreError,
        match="backup_incident_before_recovery_point",
    ):
        restore_backup(
            connection=target_connection,
            state_root=target,
            chain_directories=(backup_dir,),
            incident_at=NOW - timedelta(seconds=1),
        )
    assert StructuredRepository(target_connection).workspace_projection(
        "missing-workspace"
    ) is None
    target_connection.close()
