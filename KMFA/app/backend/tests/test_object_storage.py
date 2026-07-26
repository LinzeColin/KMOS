"""S05/P5.2 private S3-compatible object and reconciliation contracts."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import sqlite3
from pathlib import Path
from urllib.parse import quote

import pytest
import yaml
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient

from app import object_storage
from app import walking_skeleton as skeleton
from app.main import app
from app.object_reconciliation import reconcile_object_inventory
from app.object_storage import (
    S3_STORAGE_BACKEND,
    InventoryObject,
    ObjectStorageConfigurationError,
    ObjectStorageConflictError,
    ObjectStorageIntegrityError,
    ObjectStorageUnavailableError,
    S3ObjectStore,
    configured_write_store,
    content_md5_base64,
    lifecycle_store_for_backend,
)

client = TestClient(app)
BASE = "/public-api/walking-skeleton/v1"


class _MemoryBody:
    def __init__(self, value: bytes) -> None:
        self.source = io.BytesIO(value)

    def read(self, size: int = -1) -> bytes:
        return self.source.read(size)

    def close(self) -> None:
        self.source.close()


class _MemoryPaginator:
    def __init__(self, backend: "_MemoryS3") -> None:
        self.backend = backend

    def paginate(self, *, Bucket: str, Prefix: str):
        del Bucket
        return [
            {
                "Contents": [
                    {"Key": key, "Size": len(value["body"])}
                    for key, value in sorted(self.backend.objects.items())
                    if key.startswith(Prefix)
                ]
            }
        ]


class _MemoryS3:
    def __init__(self) -> None:
        self.objects: dict[str, dict[str, object]] = {}
        self.available = True
        self.version = 0

    @staticmethod
    def _error(code: str, operation: str) -> ClientError:
        return ClientError(
            {"Error": {"Code": code, "Message": "synthetic"}},
            operation,
        )

    def _require_available(self, operation: str) -> None:
        if not self.available:
            raise self._error("ServiceUnavailable", operation)

    def list_objects_v2(self, *, Bucket: str, Prefix: str, MaxKeys: int):
        del Bucket, Prefix, MaxKeys
        self._require_available("ListObjectsV2")
        return {"Contents": []}

    def put_object(self, **kwargs):
        self._require_available("PutObject")
        key = str(kwargs["Key"])
        if kwargs.get("IfNoneMatch") == "*" and key in self.objects:
            raise self._error("PreconditionFailed", "PutObject")
        body = kwargs["Body"].read()
        expected_md5 = base64.b64decode(kwargs["ContentMD5"])
        assert hashlib.md5(body, usedforsecurity=False).digest() == expected_md5
        self.version += 1
        etag = hashlib.md5(body, usedforsecurity=False).hexdigest()
        self.objects[key] = {
            "body": body,
            "metadata": dict(kwargs["Metadata"]),
            "etag": etag,
            "version_id": f"synthetic-v{self.version}",
        }
        return {
            "ETag": f'"{etag}"',
            "VersionId": f"synthetic-v{self.version}",
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }

    def head_object(self, *, Bucket: str, Key: str):
        del Bucket
        self._require_available("HeadObject")
        if Key not in self.objects:
            raise self._error("NoSuchKey", "HeadObject")
        value = self.objects[Key]
        return {
            "ContentLength": len(value["body"]),
            "Metadata": dict(value["metadata"]),
            "ETag": f'"{value["etag"]}"',
            "VersionId": value["version_id"],
        }

    def get_object(self, *, Bucket: str, Key: str):
        del Bucket
        self._require_available("GetObject")
        if Key not in self.objects:
            raise self._error("NoSuchKey", "GetObject")
        return {"Body": _MemoryBody(self.objects[Key]["body"])}

    def get_paginator(self, name: str):
        assert name == "list_objects_v2"
        self._require_available("ListObjectsV2")
        return _MemoryPaginator(self)


class _VersionedMemoryPaginator:
    def __init__(self, backend: "_VersionedMemoryS3") -> None:
        self.backend = backend

    def paginate(self, *, Bucket: str, Prefix: str):
        del Bucket
        versions: list[dict[str, str]] = []
        delete_markers: list[dict[str, str]] = []
        for key, records in sorted(self.backend.versions.items()):
            if not key.startswith(Prefix):
                continue
            for record in records:
                target = delete_markers if record["delete_marker"] else versions
                target.append(
                    {
                        "Key": key,
                        "VersionId": str(record["version_id"]),
                    }
                )
        return [{"Versions": versions, "DeleteMarkers": delete_markers}]


class _VersionedMemoryS3:
    def __init__(self) -> None:
        self.versions: dict[str, list[dict[str, object]]] = {}
        self.deleted: list[tuple[str, str]] = []

    @staticmethod
    def _error(code: str, operation: str) -> ClientError:
        return ClientError(
            {"Error": {"Code": code, "Message": "synthetic"}},
            operation,
        )

    def add_version(
        self,
        *,
        key: str,
        version_id: str,
        body: bytes = b"",
        metadata: dict[str, str] | None = None,
        delete_marker: bool = False,
    ) -> None:
        self.versions.setdefault(key, []).append(
            {
                "version_id": version_id,
                "body": body,
                "metadata": metadata or {},
                "delete_marker": delete_marker,
            }
        )

    def head_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str | None = None,
    ):
        del Bucket
        records = self.versions.get(Key, [])
        if VersionId is None:
            record = records[-1] if records else None
        else:
            record = next(
                (
                    candidate
                    for candidate in records
                    if candidate["version_id"] == VersionId
                ),
                None,
            )
        if record is None or record["delete_marker"]:
            raise self._error("NoSuchKey", "HeadObject")
        body = bytes(record["body"])
        return {
            "ContentLength": len(body),
            "Metadata": dict(record["metadata"]),
            "ETag": f'"{hashlib.md5(body, usedforsecurity=False).hexdigest()}"',
            "VersionId": record["version_id"],
        }

    def get_paginator(self, name: str):
        assert name == "list_object_versions"
        return _VersionedMemoryPaginator(self)

    def delete_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ):
        del Bucket
        records = self.versions.get(Key, [])
        before = len(records)
        self.versions[Key] = [
            record
            for record in records
            if record["version_id"] != VersionId
        ]
        if len(self.versions[Key]) == before:
            raise self._error("NoSuchVersion", "DeleteObject")
        self.deleted.append((Key, VersionId))
        return {"VersionId": VersionId}


class _NoVersionInventoryS3(_VersionedMemoryS3):
    def __init__(self) -> None:
        super().__init__()
        self.unversioned_delete_calls = 0

    def get_paginator(self, name: str):
        assert name == "list_object_versions"
        raise self._error("NotImplemented", "ListObjectVersions")

    def delete_object(self, **_: object):
        self.unversioned_delete_calls += 1
        raise AssertionError("unsafe unversioned delete must not be attempted")


@pytest.fixture
def s3_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, _MemoryS3]:
    state = tmp_path / "walking-state"
    memory = _MemoryS3()
    monkeypatch.setenv("KMFA_WALKING_SKELETON_ENABLED", "1")
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(state))
    monkeypatch.setenv("KMFA_ARTIFACT_STORAGE_MODE", "s3")
    monkeypatch.setenv("KMFA_S3_ENDPOINT_URL", "http://object-store:9000")
    monkeypatch.setenv("KMFA_S3_BUCKET", "kmfa-private-artifacts")
    monkeypatch.setenv("KMFA_S3_REGION", "us-east-1")
    monkeypatch.setenv("KMFA_S3_PREFIX", "kmfa/private/v1")
    monkeypatch.setenv("KMFA_S3_ACCESS_KEY_ID", "synthetic-app-key")
    monkeypatch.setenv("KMFA_S3_SECRET_ACCESS_KEY", "synthetic-app-secret")
    monkeypatch.setenv("KMFA_S3_ADDRESSING_STYLE", "path")
    monkeypatch.setenv("KMFA_S3_ALLOW_INSECURE_LOCAL", "1")
    monkeypatch.delenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", raising=False)
    monkeypatch.setattr(object_storage, "_build_s3_client", lambda config: memory)
    return state, memory


def _create(project_name: str) -> tuple[dict, str]:
    response = client.post(f"{BASE}/workspaces", json={"project_name": project_name})
    assert response.status_code == 201, response.text
    payload = response.json()
    token = response.cookies.get(skeleton.SESSION_COOKIE_NAME)
    assert skeleton.ACCESS_TOKEN_RE.fullmatch(token)
    return payload, token


def _upload(
    workspace_id: str,
    token: str,
    content: bytes,
    *,
    filename: str = "same-name.unknown",
    media_type: str = "application/x-kmfa-synthetic",
):
    return client.put(
        f"{BASE}/workspaces/{workspace_id}/artifact",
        content=content,
        headers={
            "Authorization": f"Bearer {token}",
            "X-KMFA-Filename": quote(filename, safe=""),
            "Content-Type": media_type,
        },
    )


def test_s3_configuration_requires_complete_credentials_and_safe_transport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("KMFA_ARTIFACT_STORAGE_MODE", "s3")
    with pytest.raises(ObjectStorageConfigurationError):
        configured_write_store(tmp_path)

    values = {
        "KMFA_S3_ENDPOINT_URL": "http://object-store:9000",
        "KMFA_S3_BUCKET": "kmfa-private-artifacts",
        "KMFA_S3_REGION": "us-east-1",
        "KMFA_S3_PREFIX": "kmfa/private/v1",
        "KMFA_S3_ACCESS_KEY_ID": "synthetic-key",
        "KMFA_S3_SECRET_ACCESS_KEY": "synthetic-secret",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(ObjectStorageConfigurationError):
        configured_write_store(tmp_path)

    monkeypatch.setenv("KMFA_S3_ALLOW_INSECURE_LOCAL", "1")
    assert configured_write_store(tmp_path).storage_backend == S3_STORAGE_BACKEND
    monkeypatch.setenv("KMFA_S3_REGION", "invalid region")
    with pytest.raises(
        ObjectStorageConfigurationError,
        match="invalid_s3_configuration",
    ):
        configured_write_store(tmp_path)
    monkeypatch.setenv("KMFA_S3_REGION", "us-east-1")
    monkeypatch.setenv(
        "KMFA_S3_ENDPOINT_URL",
        "http://credential:must-not-work@object-store:9000",
    )
    with pytest.raises(ObjectStorageConfigurationError):
        configured_write_store(tmp_path)

    monkeypatch.setenv("KMFA_ARTIFACT_STORAGE_MODE", "typo")
    with pytest.raises(ObjectStorageConfigurationError):
        configured_write_store(tmp_path)


def test_s3_adapter_conditionally_creates_and_deep_hashes_inventory(
    s3_environment: tuple[Path, _MemoryS3],
):
    state, _ = s3_environment
    store = configured_write_store(state)
    assert isinstance(store, S3ObjectStore)
    fixture = b"\x00synthetic-object\xff" * 31
    source = state / "tmp" / "source.part"
    source.parent.mkdir(mode=0o700, parents=True)
    source.write_bytes(fixture)
    sha256 = hashlib.sha256(fixture).hexdigest()
    md5 = hashlib.md5(fixture, usedforsecurity=False)
    key = store.build_storage_key(
        workspace_id="ws_" + "a" * 22,
        artifact_id="artifact_synthetic",
        artifact_version_id="artifact-version_artifact_synthetic",
        version_number=1,
        sha256=sha256,
    )
    next_version_key = store.build_storage_key(
        workspace_id="ws_" + "a" * 22,
        artifact_id="artifact_synthetic",
        artifact_version_id="artifact-version_artifact_synthetic_2",
        version_number=2,
        sha256=sha256,
    )
    assert next_version_key != key
    assert "/v00000002-" in next_version_key
    receipt = store.put_file(
        source,
        storage_key=key,
        size_bytes=len(fixture),
        sha256=sha256,
        content_md5=content_md5_base64(md5),
        artifact_id="artifact_synthetic",
        artifact_version_id="artifact-version_artifact_synthetic",
    )
    assert receipt.storage_key == key
    assert receipt.provider_version_id == "synthetic-v1"

    with pytest.raises(ObjectStorageConflictError):
        store.put_file(
            source,
            storage_key=key,
            size_bytes=len(fixture),
            sha256=sha256,
            content_md5=content_md5_base64(md5),
            artifact_id="artifact_synthetic",
            artifact_version_id="artifact-version_artifact_synthetic",
        )
    downloaded = store.materialize_verified(
        storage_key=key,
        expected_size=len(fixture),
        expected_sha256=sha256,
    )
    assert downloaded.path.read_bytes() == fixture
    downloaded.path.unlink()
    inventory = store.inventory()
    assert len(inventory) == 1
    assert inventory[0].sha256 == sha256
    assert inventory[0].metadata_sha256 == sha256


def test_s3_api_round_trip_separates_same_name_and_duplicate_content(
    s3_environment: tuple[Path, _MemoryS3],
):
    state, memory = s3_environment
    content = b"same private synthetic bytes"
    created_a, token_a = _create("S3 object A")
    created_b, token_b = _create("S3 object B")
    workspace_a = created_a["workspace"]["workspace_id"]
    workspace_b = created_b["workspace"]["workspace_id"]
    first = _upload(workspace_a, token_a, content)
    second = _upload(workspace_b, token_b, content)
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["artifact"]["sha256"] == second.json()["artifact"]["sha256"]
    assert len(memory.objects) == 2
    assert len(set(memory.objects)) == 2
    assert not list((state / "objects").glob("*.blob"))

    connection = sqlite3.connect(state / "walking_skeleton.sqlite3")
    try:
        rows = connection.execute(
            """
            SELECT storage_backend, storage_key, sha256
            FROM artifact_versions ORDER BY storage_key
            """
        ).fetchall()
    finally:
        connection.close()
    assert len(rows) == 2
    assert {row[0] for row in rows} == {S3_STORAGE_BACKEND}
    assert len({row[1] for row in rows}) == 2

    downloaded = client.post(
        f"{BASE}/workspaces/{workspace_b}/artifact/download",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert downloaded.status_code == 200
    assert downloaded.content == content
    assert downloaded.headers["x-kmfa-artifact-sha256"] == rows[0][2]
    assert not list((state / "tmp").glob("download-*.part"))

    status = client.get(f"{BASE}/status")
    assert status.status_code == 200
    status_payload = status.json()
    assert status_payload["artifact_store"] == (
        "private-s3-compatible-object-adapter"
    )
    assert status_payload["artifact_storage"][
        "application_issues_public_object_urls"
    ] is False
    assert status_payload["retention_lifecycle"][
        "application_object_delete_credentials"
    ] is False
    assert status_payload["retention_lifecycle"][
        "worker_uses_separate_credentials"
    ] is True
    assert "s3-compatible-object-store" not in status_payload["hardening_pending"]
    object_key = next(iter(memory.objects))
    assert client.get(f"{BASE}/objects/{object_key}").status_code == 404


def test_s3_integrity_failure_and_outage_are_fixed_fail_closed_errors(
    s3_environment: tuple[Path, _MemoryS3],
):
    _, memory = s3_environment
    created, token = _create("S3 integrity")
    workspace_id = created["workspace"]["workspace_id"]
    content = b"original-synthetic"
    assert _upload(workspace_id, token, content).status_code == 200
    key = next(iter(memory.objects))
    memory.objects[key]["body"] = b"tampered-synthetic"
    failed = client.post(
        f"{BASE}/workspaces/{workspace_id}/artifact/download",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert failed.status_code == 503
    assert failed.json()["detail"] == "artifact_integrity_failed"

    memory.available = False
    status = client.get(f"{BASE}/status")
    assert status.status_code == 503
    assert status.json()["detail"] == "walking_skeleton_storage_unavailable"
    assert "synthetic-app-secret" not in status.text


def test_lifecycle_s3_uses_separate_credentials_and_deletes_all_exact_versions(
    s3_environment: tuple[Path, _MemoryS3],
    monkeypatch: pytest.MonkeyPatch,
):
    state, _ = s3_environment
    versioned = _VersionedMemoryS3()
    monkeypatch.setenv(
        "KMFA_S3_LIFECYCLE_ACCESS_KEY_ID",
        "synthetic-lifecycle-key",
    )
    monkeypatch.setenv(
        "KMFA_S3_LIFECYCLE_SECRET_ACCESS_KEY",
        "synthetic-lifecycle-secret",
    )
    monkeypatch.setattr(object_storage, "_build_s3_client", lambda config: versioned)
    store = lifecycle_store_for_backend(state, S3_STORAGE_BACKEND)
    assert store.config.access_key_id == "synthetic-lifecycle-key"
    assert store.config.access_key_id != "synthetic-app-key"

    body = b"synthetic-versioned-delete"
    sha256 = hashlib.sha256(body).hexdigest()
    artifact_id = "artifact_synthetic_delete"
    artifact_version_id = "artifact_version_synthetic_delete"
    key = store.build_storage_key(
        workspace_id="ws_" + "d" * 22,
        artifact_id=artifact_id,
        artifact_version_id=artifact_version_id,
        version_number=1,
        sha256=sha256,
    )
    metadata = {
        "kmfa-sha256": sha256,
        "kmfa-artifact-id": artifact_id,
        "kmfa-artifact-version-id": artifact_version_id,
    }
    versioned.add_version(
        key=key,
        version_id="version-1",
        body=body,
        metadata=metadata,
    )
    versioned.add_version(
        key=key,
        version_id="version-2",
        body=body,
        metadata=metadata,
    )
    versioned.add_version(
        key=key,
        version_id="delete-marker-3",
        delete_marker=True,
    )
    near_key = key + ".not-the-target"
    versioned.add_version(
        key=near_key,
        version_id="near-version-1",
        body=b"must-survive",
        metadata=metadata,
    )

    deleted = store.delete_all_versions(
        storage_key=key,
        expected_size=len(body),
        expected_sha256=sha256,
        artifact_id=artifact_id,
        artifact_version_id=artifact_version_id,
        missing_is_success=True,
    )
    assert deleted == 3
    assert versioned.versions[key] == []
    assert len(versioned.versions[near_key]) == 1
    assert {deleted_key for deleted_key, _ in versioned.deleted} == {key}


def test_provider_version_count_includes_hidden_bytes_and_delete_markers(
    s3_environment: tuple[Path, _MemoryS3],
    monkeypatch: pytest.MonkeyPatch,
):
    state, _ = s3_environment
    versioned = _VersionedMemoryS3()
    monkeypatch.setenv(
        "KMFA_S3_LIFECYCLE_ACCESS_KEY_ID",
        "synthetic-lifecycle-key",
    )
    monkeypatch.setenv(
        "KMFA_S3_LIFECYCLE_SECRET_ACCESS_KEY",
        "synthetic-lifecycle-secret",
    )
    monkeypatch.setattr(object_storage, "_build_s3_client", lambda config: versioned)
    store = lifecycle_store_for_backend(state, S3_STORAGE_BACKEND)
    scoped_key = f"{store.config.prefix}/artifacts/hidden/history.blob"
    versioned.add_version(
        key=scoped_key,
        version_id="hidden-version-1",
        body=b"historical bytes",
    )
    versioned.add_version(
        key=scoped_key,
        version_id="current-delete-marker",
        delete_marker=True,
    )
    versioned.add_version(
        key="outside/private/prefix/object.blob",
        version_id="outside-version",
        body=b"outside",
    )

    assert store.provider_version_count() == 2


def test_legacy_lifecycle_delete_requires_explicit_test_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv(
        "KMFA_LIFECYCLE_ALLOW_LEGACY_FILESYSTEM_DELETE",
        raising=False,
    )
    with pytest.raises(
        ObjectStorageConfigurationError,
        match="legacy_lifecycle_delete_not_allowed",
    ):
        lifecycle_store_for_backend(
            tmp_path,
            object_storage.LEGACY_STORAGE_BACKEND,
        )

    monkeypatch.setenv(
        "KMFA_LIFECYCLE_ALLOW_LEGACY_FILESYSTEM_DELETE",
        "1",
    )
    store = lifecycle_store_for_backend(
        tmp_path,
        object_storage.LEGACY_STORAGE_BACKEND,
    )
    assert store.storage_backend == object_storage.LEGACY_STORAGE_BACKEND


def test_lifecycle_s3_fails_closed_before_deleting_mismatched_old_version(
    s3_environment: tuple[Path, _MemoryS3],
    monkeypatch: pytest.MonkeyPatch,
):
    state, _ = s3_environment
    versioned = _VersionedMemoryS3()
    monkeypatch.setenv(
        "KMFA_S3_LIFECYCLE_ACCESS_KEY_ID",
        "synthetic-lifecycle-key",
    )
    monkeypatch.setenv(
        "KMFA_S3_LIFECYCLE_SECRET_ACCESS_KEY",
        "synthetic-lifecycle-secret",
    )
    monkeypatch.setattr(object_storage, "_build_s3_client", lambda config: versioned)
    store = lifecycle_store_for_backend(state, S3_STORAGE_BACKEND)
    body = b"synthetic-expected-version"
    sha256 = hashlib.sha256(body).hexdigest()
    artifact_id = "artifact_synthetic_mismatch"
    artifact_version_id = "artifact_version_synthetic_mismatch"
    key = store.build_storage_key(
        workspace_id="ws_" + "e" * 22,
        artifact_id=artifact_id,
        artifact_version_id=artifact_version_id,
        version_number=1,
        sha256=sha256,
    )
    expected_metadata = {
        "kmfa-sha256": sha256,
        "kmfa-artifact-id": artifact_id,
        "kmfa-artifact-version-id": artifact_version_id,
    }
    versioned.add_version(
        key=key,
        version_id="version-expected",
        body=body,
        metadata=expected_metadata,
    )
    versioned.add_version(
        key=key,
        version_id="version-mismatched",
        body=b"unexpected historical bytes",
        metadata=expected_metadata,
    )
    versioned.add_version(
        key=key,
        version_id="delete-marker-current",
        delete_marker=True,
    )

    with pytest.raises(ObjectStorageIntegrityError):
        store.delete_all_versions(
            storage_key=key,
            expected_size=len(body),
            expected_sha256=sha256,
            artifact_id=artifact_id,
            artifact_version_id=artifact_version_id,
            missing_is_success=True,
        )
    assert versioned.deleted == []
    assert len(versioned.versions[key]) == 3


def test_lifecycle_s3_fails_closed_when_exact_version_inventory_is_unavailable(
    s3_environment: tuple[Path, _MemoryS3],
    monkeypatch: pytest.MonkeyPatch,
):
    state, _ = s3_environment
    versioned = _NoVersionInventoryS3()
    monkeypatch.setenv(
        "KMFA_S3_LIFECYCLE_ACCESS_KEY_ID",
        "synthetic-lifecycle-key",
    )
    monkeypatch.setenv(
        "KMFA_S3_LIFECYCLE_SECRET_ACCESS_KEY",
        "synthetic-lifecycle-secret",
    )
    monkeypatch.setattr(object_storage, "_build_s3_client", lambda config: versioned)
    store = lifecycle_store_for_backend(state, S3_STORAGE_BACKEND)
    body = b"synthetic-version-inventory-required"
    sha256 = hashlib.sha256(body).hexdigest()
    artifact_id = "artifact_synthetic_inventory"
    artifact_version_id = "artifact_version_synthetic_inventory"
    key = store.build_storage_key(
        workspace_id="ws_" + "f" * 22,
        artifact_id=artifact_id,
        artifact_version_id=artifact_version_id,
        version_number=1,
        sha256=sha256,
    )
    versioned.add_version(
        key=key,
        version_id="version-must-survive",
        body=body,
        metadata={
            "kmfa-sha256": sha256,
            "kmfa-artifact-id": artifact_id,
            "kmfa-artifact-version-id": artifact_version_id,
        },
    )

    with pytest.raises(
        ObjectStorageUnavailableError,
        match="object_version_inventory_unavailable",
    ):
        store.delete_all_versions(
            storage_key=key,
            expected_size=len(body),
            expected_sha256=sha256,
            artifact_id=artifact_id,
            artifact_version_id=artifact_version_id,
            missing_is_success=True,
        )
    assert versioned.unversioned_delete_calls == 0
    assert len(versioned.versions[key]) == 1


def test_legacy_write_rollback_keeps_s3_objects_readable(
    s3_environment: tuple[Path, _MemoryS3],
    monkeypatch: pytest.MonkeyPatch,
):
    _, _ = s3_environment
    created, token = _create("S3 dual read")
    workspace_id = created["workspace"]["workspace_id"]
    content = b"survives-write-adapter-rollback"
    assert _upload(workspace_id, token, content).status_code == 200

    monkeypatch.setenv("KMFA_ARTIFACT_STORAGE_MODE", "legacy-filesystem")
    status = client.get(f"{BASE}/status").json()
    assert status["artifact_storage"]["write_backend"] == (
        "legacy-private-filesystem"
    )
    assert status["artifact_storage"]["s3_dual_read_configured"] is True
    assert status["retention_lifecycle"][
        "application_object_delete_credentials"
    ] is True
    assert status["retention_lifecycle"][
        "worker_uses_separate_credentials"
    ] is False
    downloaded = client.post(
        f"{BASE}/workspaces/{workspace_id}/artifact/download",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert downloaded.status_code == 200
    assert downloaded.content == content


def test_reconciliation_classifies_every_anomaly_without_exposing_keys():
    rows = [
        {
            "artifact_version_id": "version_ok",
            "artifact_id": "artifact_ok",
            "storage_key": "kmfa/private/v1/artifacts/ok",
            "size_bytes": 2,
            "sha256": hashlib.sha256(b"ok").hexdigest(),
        },
        {
            "artifact_version_id": "version_missing",
            "artifact_id": "artifact_missing",
            "storage_key": "kmfa/private/v1/artifacts/private-missing-key",
            "size_bytes": 7,
            "sha256": hashlib.sha256(b"missing").hexdigest(),
        },
        {
            "artifact_version_id": "version_mismatch",
            "artifact_id": "artifact_mismatch",
            "storage_key": "kmfa/private/v1/artifacts/private-mismatch-key",
            "size_bytes": 8,
            "sha256": hashlib.sha256(b"expected").hexdigest(),
        },
    ]
    inventory = [
        InventoryObject(
            storage_key="kmfa/private/v1/artifacts/ok",
            size_bytes=2,
            sha256=hashlib.sha256(b"ok").hexdigest(),
            metadata_sha256=hashlib.sha256(b"ok").hexdigest(),
            artifact_id="artifact_ok",
            artifact_version_id="version_ok",
            etag=None,
            provider_version_id=None,
        ),
        InventoryObject(
            storage_key="kmfa/private/v1/artifacts/private-mismatch-key",
            size_bytes=8,
            sha256=hashlib.sha256(b"tampered").hexdigest(),
            metadata_sha256=hashlib.sha256(b"expected").hexdigest(),
            artifact_id="artifact_mismatch",
            artifact_version_id="version_mismatch",
            etag=None,
            provider_version_id=None,
        ),
        InventoryObject(
            storage_key="kmfa/private/v1/artifacts/private-orphan-key",
            size_bytes=6,
            sha256=hashlib.sha256(b"orphan").hexdigest(),
            metadata_sha256=hashlib.sha256(b"orphan").hexdigest(),
            artifact_id="artifact_orphan",
            artifact_version_id="version_orphan",
            etag=None,
            provider_version_id=None,
        ),
    ]
    report = reconcile_object_inventory(rows, inventory)
    assert report["consistent_objects"] == 1
    assert report["anomaly_count"] == 3
    assert report["classified_anomalies"] == 3
    assert report["unexplained_anomalies"] == 0
    assert report["repair_states_deterministic"] is True
    assert report["anomaly_counts"] == {
        "missing_object": 1,
        "object_metadata_mismatch": 1,
        "orphan_object": 1,
    }
    encoded = str(report)
    assert "private-missing-key" not in encoded
    assert "private-mismatch-key" not in encoded
    assert "private-orphan-key" not in encoded


def test_deployment_defaults_legacy_and_policy_is_private_prefix_scoped():
    app_root = Path(__file__).resolve().parents[2]
    kmfa_root = app_root.parent
    repo_root = kmfa_root.parent
    local_compose = (app_root / "docker-compose.yml").read_text(encoding="utf-8")
    coolify_compose = (
        kmfa_root / "deploy" / "coolify" / "docker-compose.yml"
    ).read_text(encoding="utf-8")
    env_example = (
        kmfa_root / "deploy" / "coolify" / ".env.example"
    ).read_text(encoding="utf-8")
    policy = json.loads(
        (app_root / "object-store-policy.json").read_text(encoding="utf-8")
    )
    lifecycle_policy = json.loads(
        (app_root / "object-store-lifecycle-policy.json").read_text(
            encoding="utf-8"
        )
    )
    local_config = yaml.safe_load(local_compose)
    coolify_config = yaml.safe_load(coolify_compose)
    dockerignore = (repo_root / ".dockerignore").read_text(encoding="utf-8")
    gitignore = (repo_root / ".gitignore").read_text(encoding="utf-8")

    for compose in (local_compose, coolify_compose):
        assert "KMFA_ARTIFACT_STORAGE_MODE:-legacy-filesystem" in compose
        assert "KMFA_LIFECYCLE_MODE:-paused" in compose
        assert "KMFA_LIFECYCLE_ALLOW_LEGACY_FILESYSTEM_DELETE" not in compose
        assert "KMFA_S3_ALLOW_INSECURE_LOCAL:-0" in compose
        assert "KMFA_S3_SECRET_ACCESS_KEY:-" in compose
        assert "configured_write_store" in compose
        assert "s.schema_version()==5" in compose
    for config in (local_config, coolify_config):
        app_environment = config["services"]["app"]["environment"]
        worker = config["services"]["lifecycle-worker"]
        worker_environment = worker["environment"]
        assert "KMFA_S3_LIFECYCLE_ACCESS_KEY_ID" not in app_environment
        assert "KMFA_S3_LIFECYCLE_SECRET_ACCESS_KEY" not in app_environment
        assert worker["profiles"] == ["lifecycle"]
        assert (
            worker_environment["KMFA_S3_LIFECYCLE_ACCESS_KEY_ID"]
            == "${KMFA_S3_LIFECYCLE_ACCESS_KEY_ID:-}"
        )
        assert (
            worker_environment["KMFA_S3_LIFECYCLE_SECRET_ACCESS_KEY"]
            == "${KMFA_S3_LIFECYCLE_SECRET_ACCESS_KEY:-}"
        )
    assert "profiles: [\"s3\"]" in local_compose
    assert "kmfa-object-data:/data" in local_compose
    assert "minio/minio:RELEASE.2025-09-07" in local_compose
    assert "sha256:14cea493" in local_compose
    assert (
        'test "$${MINIO_ROOT_USER}" != "$${KMFA_S3_ACCESS_KEY_ID}"'
        in local_compose
    )
    assert (
        'test "$${MINIO_ROOT_PASSWORD}" != "$${KMFA_S3_SECRET_ACCESS_KEY}"'
        in local_compose
    )
    assert "object-store:" not in coolify_compose
    assert "KMFA_ARTIFACT_STORAGE_MODE=legacy-filesystem" in env_example
    assert "KMFA_S3_ALLOW_INSECURE_LOCAL=0" in env_example
    assert "KMFA_LIFECYCLE_MODE=paused" in env_example
    assert {"**/.env", "**/.env.*", "**/*.env"} <= set(
        dockerignore.splitlines()
    )
    assert {
        "**/.env",
        "**/.env.*",
        "**/*.env",
        "!**/.env.example",
    } <= set(gitignore.splitlines())

    statements = policy["Statement"]
    assert {statement["Effect"] for statement in statements} == {"Allow"}
    actions = {
        action
        for statement in statements
        for action in statement["Action"]
    }
    assert actions == {
        "s3:GetObject",
        "s3:ListBucket",
        "s3:PutObject",
    }
    resources = {
        resource
        for statement in statements
        for resource in statement["Resource"]
    }
    assert "*" not in resources and "arn:aws:s3:::*" not in resources
    assert resources == {
        "arn:aws:s3:::kmfa-private-artifacts",
        "arn:aws:s3:::kmfa-private-artifacts/kmfa/private/v1/*",
    }
    list_statement = next(
        statement
        for statement in statements
        if statement["Action"] == ["s3:ListBucket"]
    )
    assert list_statement["Condition"] == {
        "StringLike": {
            "s3:prefix": [
                "kmfa/private/v1",
                "kmfa/private/v1/*",
            ]
        }
    }

    lifecycle_statements = lifecycle_policy["Statement"]
    assert {statement["Effect"] for statement in lifecycle_statements} == {
        "Allow"
    }
    lifecycle_actions = {
        action
        for statement in lifecycle_statements
        for action in statement["Action"]
    }
    assert lifecycle_actions == {
        "s3:ListBucket",
        "s3:ListBucketVersions",
        "s3:GetObject",
        "s3:GetObjectVersion",
        "s3:DeleteObject",
        "s3:DeleteObjectVersion",
    }
    lifecycle_resources = {
        resource
        for statement in lifecycle_statements
        for resource in statement["Resource"]
    }
    assert lifecycle_resources == resources
