"""S07/P7.2 Range resume and bounded, verifiable batch ZIP contracts."""

from __future__ import annotations

import asyncio
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote
from zipfile import ZIP_STORED, ZipFile

import pytest
from app import anti_abuse
from app import walking_skeleton as skeleton
from app.artifact_lineage import run_artifact_derivation_once
from app.download_archive import (
    MAX_BATCH_DOWNLOAD_ASSETS,
    BatchArchiveEntry,
    BatchArchiveError,
    archive_path_for,
    async_iter_prepared_archive,
    iter_prepared_archive,
    prepare_batch_archive,
)
from app.file_security import FileSecurityClient, ScanOutcome
from app.main import app
from fastapi.testclient import TestClient

BASE = "/public-api/walking-skeleton/v1"
SECRET = "p72-state-test-shared-secret-32-bytes-minimum"


@pytest.fixture
def range_batch_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, TestClient]:
    state = tmp_path / "walking-state"
    monkeypatch.setenv("KMFA_WALKING_SKELETON_ENABLED", "1")
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(state))
    monkeypatch.setenv("KMFA_SINGLE_FILE_DOWNLOAD_ENABLED", "1")
    monkeypatch.setenv("KMFA_RANGE_BATCH_DOWNLOAD_ENABLED", "1")
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


def _outcome(*, media_type: str = "text/plain") -> ScanOutcome:
    return ScanOutcome(
        verdict="clean",
        reason_code="security_scan_clean",
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
    *,
    body: bytes,
    name: str,
    key: str,
    media_type: str = "text/plain",
) -> dict:
    response = client.put(
        f"{BASE}/workspaces/{workspace_id}/artifact",
        content=body,
        headers={
            "Content-Type": media_type,
            "Idempotency-Key": key,
            "X-KMFA-Filename": quote(name, safe=""),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["artifact"]


def _download(
    client: TestClient,
    workspace_id: str,
    item: dict,
    *,
    headers: dict[str, str] | None = None,
):
    return client.post(
        f"{BASE}/workspaces/{workspace_id}/artifact/downloads",
        headers=headers,
        json={"kind": item["kind"], "asset_id": item["id"]},
    )


def _batch(client: TestClient, workspace_id: str, items: list[dict]):
    return client.post(
        f"{BASE}/workspaces/{workspace_id}/artifact/downloads/batch",
        json={
            "assets": [
                {"kind": item["kind"], "asset_id": item["id"]}
                for item in items
            ]
        },
    )


def test_range_batch_flag_defaults_config_and_rollback_preserve_single_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    state = tmp_path / "walking-state"
    monkeypatch.setenv("KMFA_WALKING_SKELETON_ENABLED", "1")
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(state))
    monkeypatch.setenv("KMFA_SINGLE_FILE_DOWNLOAD_ENABLED", "1")
    monkeypatch.setenv("KMFA_LIFECYCLE_MODE", "paused")
    monkeypatch.delenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", raising=False)
    client = TestClient(
        app,
        base_url="https://testserver",
        headers={"Origin": "https://testserver"},
    )

    expected_contract = {
        "enabled": False,
        "range": {
            "unit": "bytes",
            "ranges_per_request": 1,
            "parallel_requests": True,
            "validator": "sha256-etag",
        },
        "batch": {
            "selector_transport": "authorized-json-body",
            "max_assets": 500,
            "max_uncompressed_bytes": 512 * 1024 * 1024,
            "archive_format": "zip-stored-stream-v1",
            "manifest_path": "manifest.json",
            "whole_archive_buffered": False,
        },
        "batch_requires_single_file_download": True,
        "rollback_preserves_single_file_download": True,
    }
    for value in (None, "", "enable-ish", "truthy"):
        if value is None:
            monkeypatch.delenv(
                "KMFA_RANGE_BATCH_DOWNLOAD_ENABLED",
                raising=False,
            )
        else:
            monkeypatch.setenv(
                "KMFA_RANGE_BATCH_DOWNLOAD_ENABLED",
                value,
            )
        assert (
            client.get(f"{BASE}/status").json()["range_batch_download"]
            == expected_contract
        )

    workspace_id = _create(client, "P7.2 rollback fixture")
    body = b"range and batch rollback fixture"
    artifact = _upload(
        client,
        workspace_id,
        body=body,
        name="rollback.bin",
        media_type="application/octet-stream",
        key="p72-rollback-upload-key-00000001",
    )
    item = artifact["downloadables"][0]
    full = _download(client, workspace_id, item)
    assert full.status_code == 200
    assert full.content == body
    assert full.headers["accept-ranges"] == "none"

    ranged = _download(
        client,
        workspace_id,
        item,
        headers={"Range": "bytes=0-4"},
    )
    assert ranged.status_code == 404
    assert ranged.json()["detail"] == "range_batch_download_disabled"
    batch = _batch(client, workspace_id, [item])
    assert batch.status_code == 404
    assert batch.json()["detail"] == "range_batch_download_disabled"

    classified = anti_abuse._classify(
        "POST",
        f"{BASE}/workspaces/{workspace_id}/artifact/downloads/batch",
    )
    assert classified == ("export", workspace_id)
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
    workflow = (repo / ".github/workflows/app-e2e.yml").read_text(
        encoding="utf-8"
    )
    for compose in (local_compose, coolify_compose):
        assert (
            "KMFA_RANGE_BATCH_DOWNLOAD_ENABLED:"
            ' "${KMFA_RANGE_BATCH_DOWNLOAD_ENABLED:-0}"'
        ) in compose
    assert "KMFA_RANGE_BATCH_DOWNLOAD_ENABLED=0" in env_example
    assert "KMFA/app/e2e/range_batch_download_flow.py" in workflow
    assert "range-batch-download-e2e/" in workflow


def test_range_semantics_parallel_resume_hash_and_invalid_boundaries(
    range_batch_runtime: tuple[Path, TestClient],
    monkeypatch: pytest.MonkeyPatch,
):
    _state, owner = range_batch_runtime
    fake_clock = {"value": 2_000_000_000.0}
    monkeypatch.setattr(
        anti_abuse,
        "_now",
        lambda: fake_clock["value"],
    )
    monkeypatch.setattr(
        FileSecurityClient,
        "scan",
        lambda self, *args, **kwargs: _outcome(
            media_type="application/octet-stream"
        ),
    )
    workspace_id = _create(owner, "P7.2 Range fixture")
    body = bytes(range(256)) * 4097
    artifact = _upload(
        owner,
        workspace_id,
        body=body,
        name="range # + [fixture].bin",
        media_type="application/octet-stream",
        key="p72-range-upload-key-00000001",
    )
    item = artifact["downloadables"][0]

    full = _download(owner, workspace_id, item)
    assert full.status_code == 200
    assert full.content == body
    assert full.headers["accept-ranges"] == "bytes"
    assert full.headers["etag"] == f'"{item["sha256"]}"'

    first = _download(
        owner,
        workspace_id,
        item,
        headers={"Range": "bytes=0-65535"},
    )
    assert first.status_code == 206
    assert first.content == body[:65536]
    assert first.headers["content-range"] == f"bytes 0-65535/{len(body)}"
    assert first.headers["content-length"] == "65536"

    open_ended = _download(
        owner,
        workspace_id,
        item,
        headers={"Range": "bytes=65536-"},
    )
    assert open_ended.status_code == 206
    assert open_ended.content == body[65536:]
    assert hashlib.sha256(first.content + open_ended.content).hexdigest() == (
        item["sha256"]
    )

    suffix = _download(
        owner,
        workspace_id,
        item,
        headers={"Range": "bytes=-37"},
    )
    assert suffix.status_code == 206
    assert suffix.content == body[-37:]

    if_range = _download(
        owner,
        workspace_id,
        item,
        headers={
            "Range": "bytes=8-15",
            "If-Range": full.headers["etag"],
        },
    )
    assert if_range.status_code == 206
    assert if_range.content == body[8:16]
    changed_validator = _download(
        owner,
        workspace_id,
        item,
        headers={
            "Range": "bytes=8-15",
            "If-Range": '"different-object"',
        },
    )
    assert changed_validator.status_code == 200
    assert changed_validator.content == body

    session = owner.cookies.get("__Secure-kmfa_session")
    assert session
    fake_clock["value"] += 11

    def parallel_part(start: int, end: int) -> bytes:
        parallel = TestClient(
            app,
            base_url="https://testserver",
            headers={
                "Origin": "https://testserver",
                "Cookie": f"__Secure-kmfa_session={session}",
            },
        )
        response = _download(
            parallel,
            workspace_id,
            item,
            headers={"Range": f"bytes={start}-{end}"},
        )
        assert response.status_code == 206, response.text
        return response.content

    midpoint = len(body) // 2
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = (
            executor.submit(parallel_part, 0, midpoint - 1),
            executor.submit(
                parallel_part,
                midpoint,
                len(body) - 1,
            ),
        )
    reconstructed = b"".join(future.result() for future in futures)
    assert reconstructed == body
    assert hashlib.sha256(reconstructed).hexdigest() == item["sha256"]

    malformed = _download(
        owner,
        workspace_id,
        item,
        headers={"Range": "bytes=0-1,8-9"},
    )
    assert malformed.status_code == 400
    assert malformed.json()["detail"] == "invalid_range_header"
    unsatisfied = _download(
        owner,
        workspace_id,
        item,
        headers={"Range": f"bytes={len(body)}-"},
    )
    assert unsatisfied.status_code == 416
    assert unsatisfied.json()["detail"] == "range_not_satisfiable"
    assert unsatisfied.headers["content-range"] == f"bytes */{len(body)}"


def test_batch_zip_50_items_manifest_hash_duplicates_and_retry(
    range_batch_runtime: tuple[Path, TestClient],
    monkeypatch: pytest.MonkeyPatch,
):
    state, owner = range_batch_runtime
    monkeypatch.setattr(
        FileSecurityClient,
        "scan",
        lambda self, *args, **kwargs: _outcome(),
    )
    fake_clock = {"value": 2_000_000_000.0}
    monkeypatch.setattr(
        anti_abuse,
        "_now",
        lambda: fake_clock["value"],
    )
    workspace_id = _create(owner, "P7.2 50-file ZIP fixture")
    for index in range(32):
        body = f"synthetic batch item {index:02d}\n".encode()
        name = (
            "重名 # + [资料].txt"
            if index % 3 == 0
            else f"资料 {index:02d} # + [甲].txt"
        )
        _upload(
            owner,
            workspace_id,
            body=body,
            name=name,
            key=f"p72-batch-upload-key-{index:08d}",
        )
        fake_clock["value"] += 11

    for _ in range(18):
        result = run_artifact_derivation_once(state_root=state)
        assert result is not None and result.state == "converged"

    workspace = owner.get(f"{BASE}/workspaces/{workspace_id}")
    assert workspace.status_code == 200, workspace.text
    items = workspace.json()["artifact"]["downloadables"]
    assert len([item for item in items if item["kind"] == "original"]) == 32
    assert len([item for item in items if item["kind"] == "derivative"]) == 18
    assert len(items) == 50

    response = _batch(owner, workspace_id, items)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["content-disposition"].startswith("attachment;")
    assert response.headers["accept-ranges"] == "none"
    assert response.headers["x-kmfa-batch-file-count"] == "50"
    assert response.headers["x-kmfa-zip-format"] == "zip-stored-stream-v1"
    assert response.headers["x-kmfa-zip-manifest-path"] == "manifest.json"
    assert int(response.headers["content-length"]) == len(response.content)

    with ZipFile(BytesIO(response.content)) as archive:
        names = archive.namelist()
        assert len(names) == 51
        assert names[0] == "manifest.json"
        assert len(names) == len(set(names))
        assert all(
            not name.startswith("/")
            and "\\" not in name
            and ".." not in name.split("/")
            for name in names
        )
        assert all(
            info.compress_type == ZIP_STORED
            for info in archive.infolist()
        )
        manifest_bytes = archive.read("manifest.json")
        manifest = json.loads(manifest_bytes)
        assert manifest["format"] == "kmfa-download-manifest"
        assert manifest["version"] == 1
        assert manifest["archive_format"] == "zip-stored-stream-v1"
        assert manifest["file_count"] == 50
        assert len(manifest["files"]) == 50
        assert len(
            {record["archive_path"] for record in manifest["files"]}
        ) == 50
        for record in manifest["files"]:
            payload = archive.read(record["archive_path"])
            assert len(payload) == record["size_bytes"]
            assert hashlib.sha256(payload).hexdigest() == record["sha256"]
    assert hashlib.sha256(manifest_bytes).hexdigest() == (
        response.headers["x-kmfa-zip-manifest-sha256"]
    )

    retry = _batch(owner, workspace_id, items)
    assert retry.status_code == 200
    assert retry.content == response.content
    assert hashlib.sha256(retry.content).hexdigest() == hashlib.sha256(
        response.content
    ).hexdigest()

    duplicate = _batch(owner, workspace_id, [items[0], items[0]])
    assert duplicate.status_code == 422
    assert duplicate.json()["detail"] == "duplicate_download_asset"


def test_streaming_zip_500_boundary_zip_slip_cancel_and_bounded_retry(
    tmp_path: Path,
):
    source = tmp_path / "source.bin"
    source.write_bytes(b"x")
    entries = [
        BatchArchiveEntry(
            archive_path=archive_path_for(
                index,
                (
                    "../../escape"
                    if index == 1
                    else (
                        r"..\escape"
                        if index == 2
                        else "duplicate [# +].bin"
                    )
                ),
            ),
            size_bytes=1,
            sha256=hashlib.sha256(b"x").hexdigest(),
            manifest_record={
                "kind": "original",
                "asset_id": f"asset_{index:04d}",
                "name": "synthetic.bin",
            },
            storage_backend="fixture",
            storage_key=f"fixture-{index:04d}",
        )
        for index in range(1, MAX_BATCH_DOWNLOAD_ASSETS + 1)
    ]
    prepared = prepare_batch_archive(
        entries,
        max_total_source_bytes=MAX_BATCH_DOWNLOAD_ASSETS,
    )
    chunks = list(
        iter_prepared_archive(
            prepared,
            lambda _entry: SimpleNamespace(
                path=source,
                temporary=False,
            ),
        )
    )
    assert max(map(len, chunks)) <= 64 * 1024
    archive_bytes = b"".join(chunks)
    assert len(archive_bytes) == prepared.content_length
    with ZipFile(BytesIO(archive_bytes)) as archive:
        assert len(archive.namelist()) == MAX_BATCH_DOWNLOAD_ASSETS + 1
        assert "files/0001/download" in archive.namelist()
        assert "files/0002/download" in archive.namelist()
        assert len(archive.namelist()) == len(set(archive.namelist()))

    with pytest.raises(BatchArchiveError, match="batch_asset_count_invalid"):
        prepare_batch_archive(
            [*entries, entries[-1]],
            max_total_source_bytes=MAX_BATCH_DOWNLOAD_ASSETS + 1,
        )

    temporary = tmp_path / "materialized.tmp"
    temporary.write_bytes(b"z" * (128 * 1024))
    cancel_entry = BatchArchiveEntry(
        archive_path=archive_path_for(1, "cancel.bin"),
        size_bytes=temporary.stat().st_size,
        sha256=hashlib.sha256(temporary.read_bytes()).hexdigest(),
        manifest_record={
            "kind": "original",
            "asset_id": "asset_cancel",
            "name": "cancel.bin",
        },
        storage_backend="fixture",
        storage_key="fixture-cancel",
    )
    cancel_prepared = prepare_batch_archive(
        [cancel_entry],
        max_total_source_bytes=temporary.stat().st_size,
    )
    async def cancel_stream() -> None:
        stream = async_iter_prepared_archive(
            cancel_prepared,
            lambda _entry: SimpleNamespace(
                path=temporary,
                temporary=True,
            ),
        )
        for _ in range(7):
            await anext(stream)
        await stream.aclose()

    asyncio.run(cancel_stream())
    assert not temporary.exists()

    attempts = {"count": 0}

    def flaky_materialize(_entry):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise BatchArchiveError("batch_source_unavailable")
        return SimpleNamespace(path=source, temporary=False)

    one_prepared = prepare_batch_archive(
        [entries[2]],
        max_total_source_bytes=1,
    )
    with pytest.raises(BatchArchiveError, match="batch_source_unavailable"):
        b"".join(iter_prepared_archive(one_prepared, flaky_materialize))
    retried = b"".join(
        iter_prepared_archive(one_prepared, flaky_materialize)
    )
    with ZipFile(BytesIO(retried)) as archive:
        record = json.loads(archive.read("manifest.json"))["files"][0]
        assert archive.read(record["archive_path"]) == b"x"


def test_temporary_range_materialization_is_removed_on_client_disconnect(
    tmp_path: Path,
):
    temporary = tmp_path / "range-materialized.tmp"
    temporary.write_bytes(b"synthetic temporary range bytes")
    response = skeleton.CleanupFileResponse(
        temporary,
        cleanup_path=temporary,
        media_type="application/octet-stream",
    )

    async def disconnect_during_body() -> None:
        async def receive():
            return {"type": "http.disconnect"}

        async def send(message):
            if message["type"] == "http.response.body":
                raise OSError("synthetic client disconnect")

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/synthetic",
            "headers": [],
            "asgi": {"spec_version": "2.4"},
        }
        with pytest.raises(OSError, match="synthetic client disconnect"):
            await response(scope, receive, send)

    asyncio.run(disconnect_during_body())
    assert not temporary.exists()
