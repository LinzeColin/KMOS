"""S06/P6.3 immutable version, lineage, preview and reprocess contracts."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import pytest
from app.artifact_lineage import (
    PROCESSOR_NAME,
    PROCESSOR_VERSION,
    run_artifact_derivation_once,
)
from app.backup_restore import create_backup, restore_backup
from app.file_security import FileSecurityClient, ScanOutcome
from app.main import app
from app.retention_lifecycle import LifecycleRepository
from app.structured_store import (
    StructuredStoreIntegrityError,
    open_structured_store,
)
from fastapi.testclient import TestClient

from app import artifact_lineage
from app import walking_skeleton as skeleton

BASE = "/public-api/walking-skeleton/v1"
SECRET = "p63-state-test-shared-secret-32-bytes-minimum"
NOW = datetime(2026, 7, 26, 5, 0, tzinfo=timezone.utc)


@pytest.fixture
def lineage_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, TestClient]:
    state = tmp_path / "walking-state"
    monkeypatch.setenv("KMFA_WALKING_SKELETON_ENABLED", "1")
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(state))
    monkeypatch.setenv("KMFA_FILE_SECURITY_ENABLED", "1")
    monkeypatch.setenv("KMFA_ARTIFACT_DERIVATION_ENABLED", "1")
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


def _outcome(
    *,
    verdict: str = "clean",
    reason: str = "security_scan_clean",
    media_type: str = "text/plain",
) -> ScanOutcome:
    return ScanOutcome(
        verdict=verdict,
        reason_code=reason,
        detected_media_type=media_type,
        scanner_engine="kmfa-bounded-content-firewall",
        scanner_version="1.0",
        policy_version="kmfa-upload-security-v1",
    )


def _create(client: TestClient, name: str) -> str:
    response = client.post(f"{BASE}/workspaces", json={"project_name": name})
    assert response.status_code == 201, response.text
    return str(response.json()["workspace"]["workspace_id"])


def _upload(
    client: TestClient,
    workspace_id: str,
    payload: bytes,
    *,
    key: str,
    name: str = "same-name.txt",
) -> dict:
    response = client.put(
        f"{BASE}/workspaces/{workspace_id}/artifact",
        content=payload,
        headers={
            "Content-Type": "text/plain",
            "Idempotency-Key": key,
            "X-KMFA-Filename": quote(name, safe=""),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_same_name_same_content_and_modified_uploads_are_immutable_revisions(
    lineage_runtime: tuple[Path, TestClient],
    monkeypatch: pytest.MonkeyPatch,
):
    state, client = lineage_runtime
    monkeypatch.setattr(
        FileSecurityClient,
        "scan",
        lambda self, *args, **kwargs: _outcome(),
    )
    workspace_id = _create(client, "P6.3 immutable revisions")
    payloads = (b"same-content\n", b"same-content\n", b"modified-content\n")
    uploaded = [
        _upload(
            client,
            workspace_id,
            payload,
            key=f"p63-version-upload-idempotency-{index:06d}",
        )
        for index, payload in enumerate(payloads, 1)
    ]
    artifacts = [item["artifact"] for item in uploaded]
    assert [item["version_number"] for item in artifacts] == [1, 2, 3]
    assert [item["version_count"] for item in artifacts] == [1, 2, 3]
    assert len({item["artifact_version_id"] for item in artifacts}) == 3
    assert len({item["artifact_id"] for item in artifacts}) == 1
    assert artifacts[1]["sha256"] == artifacts[0]["sha256"]
    assert artifacts[2]["sha256"] != artifacts[1]["sha256"]
    assert artifacts[0]["parent_artifact_version_id"] is None
    assert (
        artifacts[1]["parent_artifact_version_id"]
        == artifacts[0]["artifact_version_id"]
    )
    assert (
        artifacts[2]["parent_artifact_version_id"]
        == artifacts[1]["artifact_version_id"]
    )

    connection = open_structured_store(
        state / "walking_skeleton.sqlite3"
    )
    try:
        compatibility = connection.execute(
            "SELECT object_name, sha256 FROM artifacts"
        ).fetchone()
        versions = connection.execute(
            """
            SELECT version_number, storage_key, sha256
            FROM artifact_versions
            ORDER BY version_number
            """
        ).fetchall()
        operations = connection.execute(
            """
                SELECT artifact_version_number
                FROM consistency_operations
                WHERE operation_kind = 'upload'
                ORDER BY artifact_version_number
            """
        ).fetchall()
        lineage = connection.execute(
            """
            SELECT
              artifact_version_id, parent_artifact_version_id,
              source_operation_id, relation_kind
            FROM artifact_version_lineage
            ORDER BY artifact_version_id
            """
        ).fetchall()
        assert str(compatibility["sha256"]) == artifacts[0]["sha256"]
        assert str(compatibility["object_name"]) == str(
            versions[0]["storage_key"]
        )
        assert [int(row["artifact_version_number"]) for row in operations] == [
            1,
            2,
            3,
        ]
        assert all(row["source_operation_id"] is not None for row in lineage)
        with pytest.raises(StructuredStoreIntegrityError):
            connection.execute(
                """
                UPDATE artifact_version_lineage
                SET relation_kind = 'root'
                WHERE relation_kind = 'revision'
                """
            )
    finally:
        connection.close()

    object_payloads = {
        item.read_bytes() for item in (state / "objects").glob("*.blob")
    }
    assert object_payloads == set(payloads)
    graph = client.get(
        f"{BASE}/workspaces/{workspace_id}/artifact/lineage"
    )
    assert graph.status_code == 200, graph.text
    assert graph.json()["version_count"] == 3
    assert graph.json()["derivative_count"] == 0
    assert graph.json()["lineage_gaps"] == 0
    assert len(graph.json()["edges"]) == 2


def test_safe_text_preview_reprocess_and_flag_rollback_preserve_every_object(
    lineage_runtime: tuple[Path, TestClient],
    monkeypatch: pytest.MonkeyPatch,
):
    state, client = lineage_runtime
    monkeypatch.setattr(
        FileSecurityClient,
        "scan",
        lambda self, *args, **kwargs: _outcome(),
    )
    workspace_id = _create(client, "P6.3 safe preview")
    source = b"<script>must remain text</script>\nsynthetic preview\n"
    uploaded = _upload(
        client,
        workspace_id,
        source,
        key="p63-preview-upload-idempotency-000001",
    )
    version_id = uploaded["artifact"]["artifact_version_id"]
    first = run_artifact_derivation_once(state_root=state)
    assert first is not None and first.state == "converged"

    refreshed = client.get(f"{BASE}/workspaces/{workspace_id}")
    assert refreshed.status_code == 200
    artifact = refreshed.json()["artifact"]
    assert artifact["artifact_version_id"] == version_id
    assert artifact["preview_allowed"] is True
    assert artifact["preview"]["generation_number"] == 1
    assert artifact["preview"]["processor"] == {
        "name": PROCESSOR_NAME,
        "version": PROCESSOR_VERSION,
    }

    preview = client.get(
        f"{BASE}/workspaces/{workspace_id}/artifact/preview"
    )
    assert preview.status_code == 200, preview.text
    assert preview.content == source
    assert preview.headers["content-type"].startswith("text/plain")
    assert preview.headers["x-content-type-options"] == "nosniff"
    assert (
        preview.headers["content-security-policy"]
        == "default-src 'none'; sandbox"
    )
    assert preview.headers["content-disposition"].startswith("inline;")
    assert (
        preview.headers["x-kmfa-derivative-sha256"]
        == hashlib.sha256(source).hexdigest()
    )

    key = "p63-reprocess-idempotency-key-000001"
    requested = client.post(
        f"{BASE}/workspaces/{workspace_id}/artifact/reprocess",
        headers={"Idempotency-Key": key},
    )
    replayed = client.post(
        f"{BASE}/workspaces/{workspace_id}/artifact/reprocess",
        headers={"Idempotency-Key": key},
    )
    assert requested.status_code == replayed.status_code == 202
    assert (
        requested.json()["processing_run_id"]
        == replayed.json()["processing_run_id"]
    )
    audit = client.get(
        f"{BASE}/workspaces/{workspace_id}/audit-events"
    )
    assert audit.status_code == 200
    assert [
        event["action"]
        for event in audit.json()["events"]
        if event["action"] == "artifact_reprocess_requested"
    ] == ["artifact_reprocess_requested"]
    second = run_artifact_derivation_once(state_root=state)
    assert second is not None and second.state == "converged"

    connection = open_structured_store(
        state / "walking_skeleton.sqlite3"
    )
    try:
        registry = connection.execute(
            "SELECT * FROM processor_registry"
        ).fetchall()
        derivatives = connection.execute(
            """
            SELECT
              generation_number, storage_key, sha256, processing_run_id
            FROM artifact_derivatives
            ORDER BY generation_number
            """
        ).fetchall()
        runs = connection.execute(
            """
            SELECT generation_number, state, derivative_id
            FROM artifact_processing_runs
            ORDER BY generation_number
            """
        ).fetchall()
        assert len(registry) == 1
        assert [int(row["generation_number"]) for row in runs] == [1, 2]
        assert [str(row["state"]) for row in runs] == [
            "converged",
            "converged",
        ]
        assert [int(row["generation_number"]) for row in derivatives] == [
            1,
            2,
        ]
        assert len({str(row["storage_key"]) for row in derivatives}) == 2
        assert len({str(row["sha256"]) for row in derivatives}) == 1
        deletion_targets = LifecycleRepository(
            connection
        )._deletion_targets(workspace_id)
        assert len(deletion_targets) == 3
        assert {
            str(row["storage_key"]) for row in deletion_targets
        } == {
            str(row["storage_key"]) for row in derivatives
        } | {
            str(
                connection.execute(
                    "SELECT storage_key FROM artifact_versions"
                ).fetchone()["storage_key"]
            )
        }
    finally:
        connection.close()

    latest = client.get(f"{BASE}/workspaces/{workspace_id}").json()[
        "artifact"
    ]
    assert latest["preview"]["generation_number"] == 2
    graph = client.get(
        f"{BASE}/workspaces/{workspace_id}/artifact/lineage"
    ).json()
    assert graph["version_count"] == 1
    assert graph["derivative_count"] == 2
    assert graph["lineage_gaps"] == 0

    monkeypatch.setenv("KMFA_CONSISTENCY_STATE_MODE", "paused")
    source_connection = open_structured_store(
        state / "walking_skeleton.sqlite3"
    )
    backup = create_backup(
        connection=source_connection,
        state_root=state,
        destination=state.parent / "p63-lineage-backup",
        kind="full",
        artifact_identity="synthetic-source/image-p63",
        backup_id="backup_p63_lineage_000001",
        now=NOW,
    )
    source_connection.close()
    restore_root = state.parent / "p63-lineage-restore"
    restore_root.mkdir()
    restored_connection = open_structured_store(
        restore_root / "walking_skeleton.sqlite3"
    )
    restored = restore_backup(
        connection=restored_connection,
        state_root=restore_root,
        chain_directories=(backup.directory,),
        incident_at=NOW + timedelta(seconds=1),
    )
    assert restored.invariant_failures == 0
    assert restored.restored_objects == 3
    assert (
        restored_connection.execute(
            "SELECT COUNT(*) AS n FROM artifact_version_lineage"
        ).fetchone()["n"]
        == 1
    )
    assert (
        restored_connection.execute(
            "SELECT COUNT(*) AS n FROM artifact_processing_runs"
        ).fetchone()["n"]
        == 2
    )
    assert (
        restored_connection.execute(
            "SELECT COUNT(*) AS n FROM artifact_derivatives"
        ).fetchone()["n"]
        == 2
    )
    restored_connection.close()
    assert len(list((restore_root / "objects").glob("*.blob"))) == 3

    before_rollback = {
        item.name: hashlib.sha256(item.read_bytes()).hexdigest()
        for item in (state / "objects").glob("*.blob")
    }
    assert len(before_rollback) == 3
    monkeypatch.setenv("KMFA_ARTIFACT_DERIVATION_ENABLED", "0")
    rolled_back = client.get(f"{BASE}/workspaces/{workspace_id}")
    assert rolled_back.status_code == 200
    assert rolled_back.json()["artifact"]["preview_allowed"] is False
    assert (
        client.get(
            f"{BASE}/workspaces/{workspace_id}/artifact/preview"
        ).status_code
        == 404
    )
    after_rollback = {
        item.name: hashlib.sha256(item.read_bytes()).hexdigest()
        for item in (state / "objects").glob("*.blob")
    }
    assert after_rollback == before_rollback


def test_derivative_respects_shared_artifact_capacity(
    lineage_runtime: tuple[Path, TestClient],
    monkeypatch: pytest.MonkeyPatch,
):
    state, client = lineage_runtime
    monkeypatch.setattr(
        FileSecurityClient,
        "scan",
        lambda self, *args, **kwargs: _outcome(),
    )
    workspace_id = _create(client, "P6.3 derivative capacity")
    payload = b"capacity-bounded-preview\n"
    uploaded = _upload(
        client,
        workspace_id,
        payload,
        key="p63-capacity-upload-idempotency-000001",
    )
    assert uploaded["artifact"]["security"]["state"] == "clean"

    monkeypatch.setattr(
        artifact_lineage,
        "MAX_TOTAL_ARTIFACT_BYTES",
        len(payload),
    )
    result = run_artifact_derivation_once(
        state_root=state,
        now=NOW + timedelta(seconds=1),
    )
    assert result is not None
    assert result.state == "not_applicable"
    assert result.reason_code == "processor_capacity_reached"
    connection = open_structured_store(
        state / "walking_skeleton.sqlite3"
    )
    try:
        count = connection.execute(
            "SELECT COUNT(*) AS n FROM artifact_derivatives"
        ).fetchone()
        assert int(count["n"]) == 0
    finally:
        connection.close()
    preview = client.get(
        f"{BASE}/workspaces/{workspace_id}/artifact/preview"
    )
    assert preview.status_code == 409


def test_attachment_only_file_never_enters_preview_processor(
    lineage_runtime: tuple[Path, TestClient],
    monkeypatch: pytest.MonkeyPatch,
):
    state, client = lineage_runtime
    monkeypatch.setattr(
        FileSecurityClient,
        "scan",
        lambda self, *args, **kwargs: _outcome(
            verdict="attachment_only",
            reason="security_active_content",
            media_type="text/html",
        ),
    )
    workspace_id = _create(client, "P6.3 attachment only")
    uploaded = _upload(
        client,
        workspace_id,
        b"<html><script>active</script></html>",
        key="p63-attachment-upload-idempotency-000001",
        name="active.html",
    )
    artifact = uploaded["artifact"]
    assert artifact["security"]["state"] == "attachment_only"
    assert artifact["security"]["processing_allowed"] is False
    assert artifact["preview_allowed"] is False
    assert run_artifact_derivation_once(state_root=state) is None
    assert (
        client.get(
            f"{BASE}/workspaces/{workspace_id}/artifact/preview"
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"{BASE}/workspaces/{workspace_id}/artifact/reprocess",
            headers={
                "Idempotency-Key": "p63-blocked-reprocess-key-000001"
            },
        ).status_code
        == 409
    )
    connection = open_structured_store(
        state / "walking_skeleton.sqlite3"
    )
    try:
        assert (
            int(
                connection.execute(
                    "SELECT COUNT(*) AS n FROM artifact_processing_runs"
                ).fetchone()["n"]
            )
            == 0
        )
        assert (
            int(
                connection.execute(
                    "SELECT COUNT(*) AS n FROM artifact_derivatives"
                ).fetchone()["n"]
            )
            == 0
        )
    finally:
        connection.close()


def test_web_adapter_does_not_contain_the_original_parser():
    source = Path(skeleton.__file__).read_text(encoding="utf-8")
    assert "_safe_text_extract" not in source
    assert "run_artifact_derivation_once" not in source
