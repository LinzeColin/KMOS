"""S05/P5.3 recoverable state, outbox and reconciliation contracts."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from app import consistency_state
from app import walking_skeleton as skeleton
from app.consistency_state import (
    ConsistencyConflictError,
    ConsistencyRepository,
    ConsistencyTransitionError,
)
from app.main import app
from app.legacy_sqlite_import import read_legacy_snapshot
from app.structured_repository import StructuredRepository
from app.structured_store import StructuredStoreError

client = TestClient(app)
BASE = "/public-api/walking-skeleton/v1"
T0 = "2026-07-24T00:00:00Z"
T1 = "2026-07-24T00:00:01Z"
T2 = "2026-07-24T00:00:02Z"
T3 = "2026-07-24T00:00:03Z"
T4 = "2026-07-24T00:00:04Z"


@pytest.fixture
def enabled_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    state = tmp_path / "walking-state"
    monkeypatch.setenv("KMFA_WALKING_SKELETON_ENABLED", "1")
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(state))
    monkeypatch.delenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", raising=False)
    monkeypatch.delenv("KMFA_ARTIFACT_STORAGE_MODE", raising=False)
    return state


def _workspace() -> tuple[str, str]:
    response = client.post(
        f"{BASE}/workspaces",
        json={"project_name": "P5.3 synthetic"},
    )
    assert response.status_code == 201, response.text
    return (
        response.json()["workspace"]["workspace_id"],
        response.cookies.get(skeleton.SESSION_COOKIE_NAME),
    )


def _upload(
    workspace_id: str,
    token: str,
    body: bytes,
    *,
    key: str,
    name: str = "synthetic.partial",
):
    return client.put(
        f"{BASE}/workspaces/{workspace_id}/artifact",
        content=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-kmfa-synthetic",
            "X-KMFA-Filename": quote(name, safe=""),
            "Idempotency-Key": key,
        },
    )


def _generic_operation(
    workspace_id: str,
    *,
    operation_kind: str,
    suffix: str,
) -> str:
    connection = skeleton._open_store()
    try:
        with connection.transaction():
            identity = ConsistencyRepository(
                connection
            ).create_generic_operation(
                operation_id=f"operation_{operation_kind}_{suffix}",
                workspace_id=workspace_id,
                operation_kind=operation_kind,
                idempotency_key=f"idempotency-{operation_kind}-{suffix}-0001",
                request_fingerprint=hashlib.sha256(
                    f"{operation_kind}:{suffix}".encode()
                ).hexdigest(),
                timestamp=T0,
            )
        return identity.operation_id
    finally:
        connection.close()


def _advance(
    operation_id: str,
    *,
    from_state: str,
    to_state: str,
    code: str,
    timestamp: str,
) -> None:
    connection = skeleton._open_store()
    try:
        with connection.transaction():
            ConsistencyRepository(connection).transition(
                operation_id,
                expected_state=from_state,
                to_state=to_state,
                transition_code=code,
                timestamp=timestamp,
            )
    finally:
        connection.close()


def _commit_outbox(operation_id: str, effect_kind: str) -> None:
    connection = skeleton._open_store()
    try:
        with connection.transaction():
            repository = ConsistencyRepository(connection)
            repository.ensure_outbox(
                operation_id=operation_id,
                effect_kind=effect_kind,
                timestamp=T2,
            )
            repository.transition(
                operation_id,
                expected_state="commit_pending",
                to_state="outbox_committed",
                transition_code="primary_and_outbox_committed",
                timestamp=T2,
            )
    finally:
        connection.close()


@pytest.mark.parametrize("operation_kind", ["process", "index", "export"])
@pytest.mark.parametrize(
    "crash_after",
    [
        "intent_recorded",
        "effect_pending",
        "effect_applied",
        "commit_pending",
        "outbox_committed",
    ],
)
def test_every_generic_transition_resumes_after_process_replacement(
    enabled_store: Path,
    operation_kind: str,
    crash_after: str,
):
    del enabled_store
    workspace_id, _ = _workspace()
    operation_id = _generic_operation(
        workspace_id,
        operation_kind=operation_kind,
        suffix=crash_after,
    )
    transitions = [
        ("intent_recorded", "effect_pending", "effect_started"),
        ("effect_pending", "effect_applied", "effect_verified"),
        ("effect_applied", "commit_pending", "commit_started"),
    ]
    for from_state, to_state, code in transitions:
        if from_state == crash_after:
            break
        _advance(
            operation_id,
            from_state=from_state,
            to_state=to_state,
            code=code,
            timestamp=T1,
        )
        if to_state == crash_after:
            break
    if crash_after not in {
        "commit_pending",
        "outbox_committed",
    }:
        current = skeleton._open_store()
        try:
            state = str(
                ConsistencyRepository(current).operation(operation_id)["state"]
            )
        finally:
            current.close()
        remaining = {
            "intent_recorded": [
                ("intent_recorded", "effect_pending", "effect_started"),
                ("effect_pending", "effect_applied", "effect_verified"),
                ("effect_applied", "commit_pending", "commit_started"),
            ],
            "effect_pending": [
                ("effect_pending", "effect_applied", "effect_verified"),
                ("effect_applied", "commit_pending", "commit_started"),
            ],
            "effect_applied": [
                ("effect_applied", "commit_pending", "commit_started"),
            ],
        }[state]
        for from_state, to_state, code in remaining:
            _advance(
                operation_id,
                from_state=from_state,
                to_state=to_state,
                code=code,
                timestamp=T1,
            )
    current = skeleton._open_store()
    try:
        state = str(
            ConsistencyRepository(current).operation(operation_id)["state"]
        )
    finally:
        current.close()
    if state == "commit_pending":
        _commit_outbox(operation_id, operation_kind)
    _advance(
        operation_id,
        from_state="outbox_committed",
        to_state="converged",
        code="operation_converged",
        timestamp=T3,
    )

    reopened = skeleton._open_store()
    try:
        repository = ConsistencyRepository(reopened)
        assert repository.operation(operation_id)["state"] == "converged"
        states = [str(row["to_state"]) for row in repository.trace(operation_id)]
        assert states == [
            "intent_recorded",
            "effect_pending",
            "effect_applied",
            "commit_pending",
            "outbox_committed",
            "converged",
        ]
    finally:
        reopened.close()


def test_legacy_snapshot_preserves_trace_sequence_not_random_event_id_order(
    enabled_store: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    workspace_id, _ = _workspace()
    reverse_ids = iter(("trace_z", "trace_y", "trace_x"))
    monkeypatch.setattr(
        consistency_state,
        "_new_id",
        lambda prefix: next(reverse_ids),
    )
    operation_id = _generic_operation(
        workspace_id,
        operation_kind="process",
        suffix="trace-import-order",
    )
    _advance(
        operation_id,
        from_state="intent_recorded",
        to_state="effect_pending",
        code="effect_started",
        timestamp=T0,
    )
    _advance(
        operation_id,
        from_state="effect_pending",
        to_state="effect_applied",
        code="effect_verified",
        timestamp=T0,
    )

    snapshot = read_legacy_snapshot(
        enabled_store / "walking_skeleton.sqlite3"
    )
    assert [
        row["to_state"]
        for row in snapshot["consistency_trace"]
        if row["operation_id"] == operation_id
    ] == ["intent_recorded", "effect_pending", "effect_applied"]


def test_idempotency_conflict_and_invalid_transition_fail_closed(
    enabled_store: Path,
):
    del enabled_store
    workspace_id, _ = _workspace()
    operation_id = _generic_operation(
        workspace_id,
        operation_kind="process",
        suffix="conflict",
    )
    connection = skeleton._open_store()
    try:
        with pytest.raises(ConsistencyConflictError):
            with connection.transaction():
                ConsistencyRepository(connection).create_generic_operation(
                    operation_id="operation_conflicting_request",
                    workspace_id=workspace_id,
                    operation_kind="process",
                    idempotency_key="idempotency-process-conflict-0001",
                    request_fingerprint="f" * 64,
                    timestamp=T1,
                )
        with pytest.raises(ConsistencyTransitionError):
            with connection.transaction():
                ConsistencyRepository(connection).transition(
                    operation_id,
                    expected_state="intent_recorded",
                    to_state="commit_pending",
                    transition_code="illegal_skip",
                    timestamp=T1,
                )
        assert ConsistencyRepository(connection).operation(operation_id)[
            "state"
        ] == "intent_recorded"
    finally:
        connection.close()


def test_outbox_timeout_duplicate_delivery_and_crash_before_ack_apply_once(
    enabled_store: Path,
):
    del enabled_store
    workspace_id, _ = _workspace()
    operation_id = _generic_operation(
        workspace_id,
        operation_kind="index",
        suffix="outbox",
    )
    for from_state, to_state, code in (
        ("intent_recorded", "effect_pending", "effect_started"),
        ("effect_pending", "effect_applied", "effect_verified"),
        ("effect_applied", "commit_pending", "commit_started"),
    ):
        _advance(
            operation_id,
            from_state=from_state,
            to_state=to_state,
            code=code,
            timestamp=T1,
        )
    _commit_outbox(operation_id, "index")
    _advance(
        operation_id,
        from_state="outbox_committed",
        to_state="converged",
        code="operation_converged",
        timestamp=T3,
    )

    connection = skeleton._open_store()
    try:
        with connection.transaction():
            first = ConsistencyRepository(connection).claim_outbox(
                now=T2,
                lease_until=T3,
                effect_kinds={"index"},
            )
        assert first is not None and first.attempt_count == 1
        # External consumer applies once by dedupe key. We persist its receipt,
        # then simulate a process crash before producer-side acknowledgement.
        external_effects = {first.dedupe_key: "external-index-applied"}
        receipt_hash = hashlib.sha256(
            external_effects[first.dedupe_key].encode()
        ).hexdigest()
        with connection.transaction():
            ConsistencyRepository(connection).record_effect_receipt(
                first,
                receipt_hash=receipt_hash,
                timestamp=T2,
            )
    finally:
        connection.close()

    replaced = skeleton._open_store()
    try:
        with replaced.transaction():
            second = ConsistencyRepository(replaced).claim_outbox(
                now=T3,
                lease_until=T4,
                effect_kinds={"index"},
            )
        assert second is not None and second.dedupe_key == first.dedupe_key
        assert second.attempt_count == 2
        stored_receipt = ConsistencyRepository(replaced).effect_receipt(
            second.dedupe_key
        )
        assert stored_receipt["receipt_hash"] == receipt_hash
        assert len(external_effects) == 1
        with replaced.transaction():
            ConsistencyRepository(replaced).record_effect_receipt(
                second,
                receipt_hash=receipt_hash,
                timestamp=T3,
            )
            ConsistencyRepository(replaced).acknowledge_outbox(
                second,
                timestamp=T3,
            )
        report = ConsistencyRepository(replaced).reconciliation_report()
        assert report["unexplained_terminal_states"] == 0
        assert report["duplicate_effect_receipts"] == 0
        assert report["outbox_state_counts"] == {"delivered": 1}
    finally:
        replaced.close()


def test_stale_outbox_lease_cannot_retry_or_isolate_a_new_claim(
    enabled_store: Path,
):
    del enabled_store
    workspace_id, _ = _workspace()
    operation_id = _generic_operation(
        workspace_id,
        operation_kind="process",
        suffix="lease-fence",
    )
    for from_state, to_state, code in (
        ("intent_recorded", "effect_pending", "effect_started"),
        ("effect_pending", "effect_applied", "effect_verified"),
        ("effect_applied", "commit_pending", "commit_started"),
    ):
        _advance(
            operation_id,
            from_state=from_state,
            to_state=to_state,
            code=code,
            timestamp=T0,
        )
    _commit_outbox(operation_id, "process")

    connection = skeleton._open_store()
    try:
        with connection.transaction():
            repository = ConsistencyRepository(connection)
            first = repository.claim_outbox(now=T2, lease_until=T3)
        assert first is not None
        with connection.transaction():
            repository = ConsistencyRepository(connection)
            second = repository.claim_outbox(now=T3, lease_until=T4)
        assert second is not None
        assert second.attempt_count == first.attempt_count + 1

        with pytest.raises(ConsistencyTransitionError):
            with connection.transaction():
                ConsistencyRepository(connection).retry_outbox(
                    first,
                    available_at=T4,
                    error_code="stale_worker_retry",
                    timestamp=T3,
                )
        with pytest.raises(ConsistencyTransitionError):
            with connection.transaction():
                ConsistencyRepository(connection).isolate_outbox(
                    first,
                    error_code="stale_worker_isolation",
                    timestamp=T3,
                )
        current = connection.execute(
            """
            SELECT state, attempt_count
            FROM consistency_outbox
            WHERE outbox_event_id = ?
            """,
            (second.outbox_event_id,),
        ).fetchone()
        assert dict(current) == {
            "state": "leased",
            "attempt_count": second.attempt_count,
        }
    finally:
        connection.close()


def test_partial_mismatch_is_isolated_and_object_key_stays_private(
    enabled_store: Path,
):
    del enabled_store
    workspace_id, _ = _workspace()
    operation_id = _generic_operation(
        workspace_id,
        operation_kind="export",
        suffix="isolation",
    )
    _advance(
        operation_id,
        from_state="intent_recorded",
        to_state="effect_pending",
        code="effect_started",
        timestamp=T1,
    )
    private_key = "private/synthetic/export/object-key"
    connection = skeleton._open_store()
    try:
        with connection.transaction():
            repository = ConsistencyRepository(connection)
            repository.quarantine_object(
                operation_id=operation_id,
                storage_backend="synthetic-private",
                storage_key=private_key,
                reason_code="export_identity_mismatch",
                timestamp=T2,
            )
            repository.isolate(
                operation_id,
                expected_state="effect_pending",
                error_code="export_identity_mismatch",
                timestamp=T2,
            )
        report = ConsistencyRepository(connection).reconciliation_report()
        assert report["operation_state_counts"] == {"isolated": 1}
        assert report["quarantined_object_count"] == 1
        assert report["unexplained_terminal_states"] == 0
        assert private_key not in str(report)
    finally:
        connection.close()


def test_upload_replay_is_one_object_one_projection_and_hash_only_key(
    enabled_store: Path,
):
    workspace_id, token = _workspace()
    key = "upload-replay-synthetic-0001"
    body = b"same upload bytes after an ambiguous client timeout"
    first = _upload(workspace_id, token, body, key=key)
    replay = _upload(workspace_id, token, body, key=key)
    conflict = _upload(workspace_id, token, body + b"!", key=key)
    assert first.status_code == replay.status_code == 200
    assert first.json()["artifact"] == replay.json()["artifact"]
    assert conflict.status_code == 409
    assert conflict.json()["detail"] == "idempotency_key_conflict"
    assert len(list((enabled_store / "objects").glob("*.blob"))) == 1
    assert not list((enabled_store / "tmp").glob("*.part"))

    database = sqlite3.connect(enabled_store / "walking_skeleton.sqlite3")
    try:
        counts = {
            table: database.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
            for table in (
                "artifacts",
                "artifact_versions",
                "consistency_operations",
                "consistency_outbox",
                "consistency_trace",
            )
        }
        audit_count = database.execute(
            """
            SELECT COUNT(*)
            FROM audit_events
            WHERE action = 'artifact_uploaded'
            """
        ).fetchone()[0]
    finally:
        database.close()
    assert counts == {
        "artifacts": 1,
        "artifact_versions": 1,
        "consistency_operations": 1,
        "consistency_outbox": 1,
        "consistency_trace": 6,
    }
    assert audit_count == 1
    persisted = b"".join(
        path.read_bytes()
        for path in enabled_store.rglob("*")
        if path.is_file()
    )
    assert key.encode() not in persisted


def test_upload_recovers_object_success_with_unknown_timeout(
    enabled_store: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    workspace_id, token = _workspace()
    original = skeleton.configured_write_store
    store = original(enabled_store)
    real_put = store.put_file
    calls = 0

    def ambiguous_put(*args, **kwargs):
        nonlocal calls
        calls += 1
        receipt = real_put(*args, **kwargs)
        if calls == 1:
            raise skeleton.ObjectStorageUnavailableError(
                "object_store_unavailable"
            )
        return receipt

    store.put_file = ambiguous_put
    monkeypatch.setattr(skeleton, "configured_write_store", lambda _: store)
    response = _upload(
        workspace_id,
        token,
        b"ambiguous object outcome",
        key="upload-ambiguous-timeout-0001",
    )
    assert response.status_code == 200, response.text
    assert calls == 1
    assert len(list((enabled_store / "objects").glob("*.blob"))) == 1


def test_upload_recovers_database_failure_without_duplicate_object(
    enabled_store: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    workspace_id, token = _workspace()
    body = b"object survives database failure"
    key = "upload-database-retry-0001"
    original = StructuredRepository.ensure_uploaded_artifact
    calls = 0

    def fail_once(self, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise StructuredStoreError("synthetic database interruption")
        return original(self, **kwargs)

    monkeypatch.setattr(
        StructuredRepository,
        "ensure_uploaded_artifact",
        fail_once,
    )
    interrupted = _upload(workspace_id, token, body, key=key)
    assert interrupted.status_code == 503
    assert len(list((enabled_store / "objects").glob("*.blob"))) == 1
    resumed = _upload(workspace_id, token, body, key=key)
    assert resumed.status_code == 200, resumed.text
    assert len(list((enabled_store / "objects").glob("*.blob"))) == 1
    assert not list((enabled_store / "tmp").glob("*.part"))


def test_upload_recovery_uses_persisted_backend_after_write_mode_switch(
    enabled_store: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    workspace_id, token = _workspace()
    original_configured_store = skeleton.configured_write_store
    persisted_store = original_configured_store(enabled_store)

    class PersistedBackendAlias:
        storage_backend = skeleton.S3_STORAGE_BACKEND

        def __getattr__(self, name):
            return getattr(persisted_store, name)

    aliased_store = PersistedBackendAlias()
    configured_calls = 0

    def switched_configured_store(_):
        nonlocal configured_calls
        configured_calls += 1
        return aliased_store if configured_calls == 1 else persisted_store

    resolver_calls: list[str] = []

    def persisted_backend_store(_, storage_backend):
        resolver_calls.append(storage_backend)
        assert storage_backend == skeleton.S3_STORAGE_BACKEND
        return aliased_store

    real_resume = skeleton._resume_upload_operation
    interrupted = False

    def interrupt_once(operation_id, object_store, **kwargs):
        nonlocal interrupted
        if not interrupted:
            interrupted = True
            raise skeleton.SkeletonError(
                503, "walking_skeleton_storage_unavailable"
            )
        return real_resume(operation_id, object_store, **kwargs)

    monkeypatch.setattr(
        skeleton,
        "configured_write_store",
        switched_configured_store,
    )
    monkeypatch.setattr(
        skeleton,
        "object_store_for_backend",
        persisted_backend_store,
    )
    monkeypatch.setattr(
        skeleton,
        "_resume_upload_operation",
        interrupt_once,
    )

    first = _upload(
        workspace_id,
        token,
        b"persisted backend survives write mode rollback",
        key="upload-backend-mode-switch-0001",
    )
    replay = _upload(
        workspace_id,
        token,
        b"persisted backend survives write mode rollback",
        key="upload-backend-mode-switch-0001",
    )
    assert first.status_code == 503
    assert replay.status_code == 200, replay.text
    assert resolver_calls == [skeleton.S3_STORAGE_BACKEND]
    assert len(list((enabled_store / "objects").glob("*.blob"))) == 1
    assert not list((enabled_store / "tmp").glob("*.part"))


def test_pause_mode_blocks_only_new_uploads_and_preserves_reads(
    enabled_store: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    del enabled_store
    workspace_id, token = _workspace()
    monkeypatch.setenv("KMFA_CONSISTENCY_STATE_MODE", "paused")
    status = client.get(f"{BASE}/status")
    blocked = _upload(
        workspace_id,
        token,
        b"must-not-write",
        key="upload-paused-synthetic-0001",
    )
    readable = client.get(
        f"{BASE}/workspaces/{workspace_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert status.status_code == 200
    assert status.json()["consistency_state"]["mode"] == "paused"
    assert status.json()["consistency_state"]["new_uploads_paused"] is True
    assert blocked.status_code == 503
    assert blocked.json()["detail"] == "consistency_processing_paused"
    assert readable.status_code == 200
    connection = skeleton._open_store()
    try:
        assert (
            connection.execute(
                "SELECT COUNT(*) AS count_value FROM consistency_operations"
            ).fetchone()["count_value"]
            == 0
        )
    finally:
        connection.close()

    monkeypatch.setenv("KMFA_CONSISTENCY_STATE_MODE", "typo")
    invalid = client.get(f"{BASE}/status")
    assert invalid.status_code == 503
    assert invalid.json()["detail"] == "consistency_mode_invalid"


def test_consistency_trace_is_append_only(enabled_store: Path):
    del enabled_store
    workspace_id, _ = _workspace()
    operation_id = _generic_operation(
        workspace_id,
        operation_kind="process",
        suffix="append-only",
    )
    connection = skeleton._open_store()
    try:
        with pytest.raises(StructuredStoreError):
            with connection.transaction():
                connection.execute(
                    """
                    UPDATE consistency_trace
                    SET transition_code = 'tampered'
                    WHERE operation_id = ?
                    """,
                    (operation_id,),
                )
        with pytest.raises(StructuredStoreError):
            with connection.transaction():
                connection.execute(
                    "DELETE FROM consistency_trace WHERE operation_id = ?",
                    (operation_id,),
                )
        assert len(ConsistencyRepository(connection).trace(operation_id)) == 1
    finally:
        connection.close()


def test_current_schema_deployment_preserves_v3_consistency_contract():
    app_root = Path(__file__).resolve().parents[2]
    kmfa_root = app_root.parent
    repo_root = kmfa_root.parent
    frontend = (app_root / "frontend" / "src" / "WalkingSkeleton.jsx").read_text(
        encoding="utf-8"
    )
    local_compose = (app_root / "docker-compose.yml").read_text(
        encoding="utf-8"
    )
    coolify_compose = (
        kmfa_root / "deploy" / "coolify" / "docker-compose.yml"
    ).read_text(encoding="utf-8")
    workflow = (repo_root / ".github" / "workflows" / "app-e2e.yml").read_text(
        encoding="utf-8"
    )
    assert "'Idempotency-Key': retryKey" in frontend
    assert "uploadIdempotencyKeyFor" in frontend
    assert "s.schema_version()==4" in local_compose
    assert "s.schema_version()==4" in coolify_compose
    assert "KMFA_CONSISTENCY_STATE_MODE:-recoverable-v1" in local_compose
    assert "KMFA_CONSISTENCY_STATE_MODE:-recoverable-v1" in coolify_compose
    assert "KMFA/app/e2e/consistency_state_flow.py" in workflow
    assert "consistency-state-e2e/" in workflow
    assert "kmfa-p53-ci-pgdata" in workflow
    assert "kmfa-p53-ci-objectdata" in workflow
    assert "KMFA/app/e2e/retention_backup_restore_flow.py" in workflow
    assert "retention-backup-restore-e2e/" in workflow
