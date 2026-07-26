#!/usr/bin/env python3
"""S06/P6.1 final-image resumable arbitrary-file Oracle.

The Oracle owns one explicitly named container and an initially empty host
state directory. It persists only synthetic fixture hashes/counts: workspace
recovery material and short-lived session capabilities remain in memory.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

API_PREFIX = "/public-api/walking-skeleton/v1"
SESSION_RE = re.compile(r"^operation_[A-Za-z0-9_-]{24}$")
ACCESS_RE = re.compile(r"^kmfa-a1-[A-Za-z0-9_-]{43}$")
RECOVERY_RE = re.compile(r"^kmfa-r1-[A-Za-z0-9_-]{43}$")
CONTAINER_RE = re.compile(r"^kmfa-p61-[a-z0-9-]+$")
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_CHUNK_BYTES = 4 * 1024 * 1024

FIXTURES = (
    ("document.pdf", "application/pdf", b"%PDF-p61-synthetic"),
    ("image.png", "image/png", b"\x89PNG\r\n\x1a\np61-synthetic"),
    ("audio.mp3", "audio/mpeg", b"ID3-p61-synthetic"),
    ("video.mp4", "video/mp4", b"\x00\x00\x00\x18ftyp-p61-synthetic"),
    ("archive.zip", "application/zip", b"PK\x03\x04-p61-synthetic"),
    ("binary.unknown", "application/x-unknown", b"\x00\xff-p61-synthetic"),
    ("danger.double.exe", "application/x-msdownload", b"MZ-p61-synthetic"),
)


@dataclass(frozen=True)
class HttpResult:
    status: int
    headers: dict[str, str]
    set_cookies: tuple[str, ...]
    body: bytes

    def json(self) -> dict[str, Any]:
        return json.loads(self.body)


def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        check=check,
        capture_output=True,
        text=True,
    )


def _container_exists(name: str) -> bool:
    return _run("docker", "inspect", name, check=False).returncode == 0


def _wait_ready(base_url: str, timeout: float = 60) -> None:
    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(
                f"{base_url}/healthz",
                timeout=2,
            ) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError) as exc:
            last_error = str(exc)
        time.sleep(0.5)
    raise AssertionError(f"container health timeout: {last_error}")


class Container:
    def __init__(
        self,
        *,
        name: str,
        image: str,
        state_dir: Path,
        port: int,
    ) -> None:
        self.name = name
        self.image = image
        self.state_dir = state_dir
        self.port = port
        self.base_url = f"http://localhost:{port}"
        self.owned = False

    def start(self, *, resumable: bool) -> None:
        assert not self.owned
        assert not _container_exists(self.name), (
            f"refusing to replace pre-existing container {self.name}"
        )
        user_args: tuple[str, ...] = ()
        if hasattr(os, "getuid") and hasattr(os, "getgid"):
            user_args = ("--user", f"{os.getuid()}:{os.getgid()}")
        result = _run(
            "docker",
            "run",
            "-d",
            "--name",
            self.name,
            "-p",
            f"127.0.0.1:{self.port}:8000",
            "-e",
            "KMFA_WALKING_SKELETON_ENABLED=1",
            "-e",
            f"KMFA_RESUMABLE_UPLOAD_ENABLED={1 if resumable else 0}",
            "-e",
            "KMFA_PUBLIC_INDEXING_ENABLED=0",
            "-e",
            "KMFA_ABUSE_POLICY_MODE=enforced",
            "-v",
            f"{self.state_dir}:/var/lib/kmfa/state",
            *user_args,
            self.image,
        )
        assert result.stdout.strip(), result.stderr
        self.owned = True
        try:
            _wait_ready(self.base_url)
        except Exception:
            logs = _run("docker", "logs", self.name, check=False)
            raise AssertionError(
                f"container failed to start:\n{logs.stdout}\n{logs.stderr}"
            )

    def restart(self) -> None:
        assert self.owned
        _run("docker", "restart", self.name)
        _wait_ready(self.base_url)

    def logs(self) -> str:
        result = _run("docker", "logs", self.name, check=False)
        return result.stdout + result.stderr

    def remove(self) -> None:
        if not self.owned:
            return
        _run("docker", "rm", "-f", self.name)
        self.owned = False


class Api:
    def __init__(
        self,
        base_url: str,
        capabilities: list[str] | None = None,
    ) -> None:
        self.base_url = base_url
        self.sequence = 0
        self.capabilities = capabilities

    def _actor_headers(self) -> dict[str, str]:
        self.sequence += 1
        # Each synthetic workspace uses a deterministic, non-personal actor.
        suffix = hashlib.sha256(
            f"p61-actor-{self.sequence}".encode()
        ).hexdigest()
        return {
            "CF-Connecting-IP": f"198.51.100.{10 + self.sequence % 200}",
            "Cookie": f"__Host-kmfa_device=kmfa-d1-{suffix[:22]}",
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResult:
        request = urllib.request.Request(
            f"{self.base_url}{API_PREFIX}{path}",
            data=body,
            headers={
                "Accept": "application/json",
                "Origin": self.base_url,
                **(headers or {}),
            },
            method=method,
        )
        try:
            response = urllib.request.urlopen(request, timeout=30)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            raw_headers = {
                key.lower(): value for key, value in response.headers.items()
            }
            set_cookies = tuple(
                response.headers.get_all("Set-Cookie") or ()
            )
            return HttpResult(
                status=response.status,
                headers=raw_headers,
                set_cookies=set_cookies,
                body=response.read(),
            )

    def create_workspace(self, label: str) -> tuple[str, str, dict[str, str]]:
        actor = self._actor_headers()
        result = self.request(
            "POST",
            "/workspaces",
            body=json.dumps({"project_name": label}).encode(),
            headers={**actor, "Content-Type": "application/json"},
        )
        assert result.status == 201, result.body
        payload = result.json()
        workspace_id = str(payload["workspace"]["workspace_id"])
        recovery_code = str(payload["recovery_code"])
        assert RECOVERY_RE.fullmatch(recovery_code)
        joined = "\n".join(result.set_cookies)
        match = re.search(
            r"__Secure-kmfa_session=([^;\s]+)",
            joined,
        )
        assert match and ACCESS_RE.fullmatch(match.group(1)), result.set_cookies
        token = match.group(1)
        if self.capabilities is not None:
            self.capabilities.extend((token, recovery_code))
        return workspace_id, token, actor

    def auth(
        self,
        token: str,
        actor: dict[str, str],
    ) -> dict[str, str]:
        return {**actor, "Authorization": f"Bearer {token}"}

    def create_session(
        self,
        workspace_id: str,
        token: str,
        actor: dict[str, str],
        *,
        name: str,
        media_type: str,
        payload: bytes,
        key: str,
        sha256: str | None = None,
        size_bytes: int | None = None,
    ) -> HttpResult:
        body = {
            "original_name": name,
            "reported_media_type": media_type,
            "size_bytes": len(payload) if size_bytes is None else size_bytes,
            "sha256": sha256 or hashlib.sha256(payload).hexdigest(),
        }
        return self.request(
            "POST",
            f"/workspaces/{workspace_id}/upload-sessions",
            body=json.dumps(body).encode(),
            headers={
                **self.auth(token, actor),
                "Content-Type": "application/json",
                "Idempotency-Key": key,
            },
        )

    def chunk(
        self,
        workspace_id: str,
        token: str,
        actor: dict[str, str],
        session_id: str,
        *,
        offset: int,
        chunk: bytes,
        checksum: str | None = None,
    ) -> HttpResult:
        return self.request(
            "PATCH",
            f"/workspaces/{workspace_id}/upload-sessions/{session_id}",
            body=chunk,
            headers={
                **self.auth(token, actor),
                "Content-Type": "application/offset+octet-stream",
                "Upload-Offset": str(offset),
                "X-KMFA-Chunk-SHA256": (
                    checksum or hashlib.sha256(chunk).hexdigest()
                ),
            },
        )

    def session(
        self,
        workspace_id: str,
        token: str,
        actor: dict[str, str],
        session_id: str,
    ) -> HttpResult:
        return self.request(
            "GET",
            f"/workspaces/{workspace_id}/upload-sessions/{session_id}",
            headers=self.auth(token, actor),
        )

    def complete(
        self,
        workspace_id: str,
        token: str,
        actor: dict[str, str],
        session_id: str,
    ) -> HttpResult:
        return self.request(
            "POST",
            (
                f"/workspaces/{workspace_id}/upload-sessions/"
                f"{session_id}/complete"
            ),
            headers=self.auth(token, actor),
        )

    def download(
        self,
        workspace_id: str,
        token: str,
        actor: dict[str, str],
    ) -> HttpResult:
        return self.request(
            "POST",
            f"/workspaces/{workspace_id}/artifact/download",
            headers=self.auth(token, actor),
        )


def _session_id(result: HttpResult) -> str:
    assert result.status == 201, result.body
    upload = result.json()["upload_session"]
    session_id = str(upload["upload_session_id"])
    assert SESSION_RE.fullmatch(session_id)
    assert upload["protocol"] == "kmfa-offset-v1"
    assert upload["attachment_only"] is True
    return session_id


def _disconnect_during_chunk(
    api: Api,
    *,
    workspace_id: str,
    token: str,
    actor: dict[str, str],
    session_id: str,
    offset: int,
    intended_chunk: bytes,
) -> None:
    target = urlsplit(api.base_url)
    assert target.hostname and target.port
    connection = http.client.HTTPConnection(
        target.hostname,
        target.port,
        timeout=5,
    )
    path = (
        f"{API_PREFIX}/workspaces/{workspace_id}/upload-sessions/{session_id}"
    )
    connection.putrequest("PATCH", path)
    headers = {
        **api.auth(token, actor),
        "Origin": api.base_url,
        "Content-Type": "application/offset+octet-stream",
        "Content-Length": str(len(intended_chunk)),
        "Upload-Offset": str(offset),
        "X-KMFA-Chunk-SHA256": hashlib.sha256(
            intended_chunk
        ).hexdigest(),
    }
    for name, value in headers.items():
        connection.putheader(name, value)
    connection.endheaders()
    connection.send(intended_chunk[: len(intended_chunk) // 2])
    # Closing before the declared body is complete is the synthetic transport
    # interruption. There is deliberately no response to treat as success.
    connection.close()


def _upload_fixture(
    api: Api,
    *,
    index: int,
    name: str,
    media_type: str,
    payload: bytes,
) -> str:
    workspace_id, token, actor = api.create_workspace(f"P6.1 type {index}")
    created = api.create_session(
        workspace_id,
        token,
        actor,
        name=name,
        media_type=media_type,
        payload=payload,
        key=f"p61-e2e-file-type-{index:02d}",
    )
    session_id = _session_id(created)
    chunk = api.chunk(
        workspace_id,
        token,
        actor,
        session_id,
        offset=0,
        chunk=payload,
    )
    assert chunk.status == 204 and chunk.headers["upload-offset"] == str(
        len(payload)
    )
    completed = api.complete(
        workspace_id,
        token,
        actor,
        session_id,
    )
    assert completed.status == 200, completed.body
    downloaded = api.download(workspace_id, token, actor)
    expected_hash = hashlib.sha256(payload).hexdigest()
    assert downloaded.status == 200 and downloaded.body == payload
    assert downloaded.headers["content-type"].startswith(
        "application/octet-stream"
    )
    assert downloaded.headers["content-disposition"].startswith("attachment;")
    assert downloaded.headers["x-content-type-options"] == "nosniff"
    assert downloaded.headers["x-kmfa-artifact-mode"] == "attachment-only"
    assert downloaded.headers["x-kmfa-artifact-sha256"] == expected_hash
    for action in ("preview", "execute"):
        denied = api.request(
            "POST",
            f"/workspaces/{workspace_id}/artifact/{action}",
            headers=api.auth(token, actor),
        )
        assert denied.status == 404
    return expected_hash


def _interruption_oracle(
    api: Api,
    container: Container,
    state_dir: Path,
) -> dict[str, Any]:
    payload = (
        b"A" * MAX_CHUNK_BYTES
        + b"B" * MAX_CHUNK_BYTES
        + b"resume-after-restart"
    )
    workspace_id, token, actor = api.create_workspace("P6.1 restart")
    created = api.create_session(
        workspace_id,
        token,
        actor,
        name="restart.bin",
        media_type="application/octet-stream",
        payload=payload,
        key="p61-e2e-restart-0001",
    )
    session_id = _session_id(created)
    first_chunk = payload[:MAX_CHUNK_BYTES]
    sent = api.chunk(
        workspace_id,
        token,
        actor,
        session_id,
        offset=0,
        chunk=first_chunk,
    )
    assert sent.status == 204
    chunks_before = list(
        (state_dir / "walking-skeleton" / "tmp").glob("*.chunk")
    )
    assert len(chunks_before) == 1

    container.restart()
    status = api.session(workspace_id, token, actor, session_id)
    assert status.status == 200
    assert status.json()["upload_session"]["offset_bytes"] == MAX_CHUNK_BYTES
    replay = api.chunk(
        workspace_id,
        token,
        actor,
        session_id,
        offset=0,
        chunk=first_chunk,
    )
    assert replay.status == 204
    assert replay.headers["upload-offset"] == str(MAX_CHUNK_BYTES)
    assert len(
        list((state_dir / "walking-skeleton" / "tmp").glob("*.chunk"))
    ) == 1
    second_chunk = payload[MAX_CHUNK_BYTES : 2 * MAX_CHUNK_BYTES]
    _disconnect_during_chunk(
        api,
        workspace_id=workspace_id,
        token=token,
        actor=actor,
        session_id=session_id,
        offset=MAX_CHUNK_BYTES,
        intended_chunk=second_chunk,
    )
    request_parts = state_dir / "walking-skeleton" / "tmp"
    deadline = time.monotonic() + 5
    while (
        list(request_parts.glob("request-*.part"))
        and time.monotonic() < deadline
    ):
        time.sleep(0.05)
    assert not list(request_parts.glob("request-*.part"))
    interrupted_status = api.session(
        workspace_id,
        token,
        actor,
        session_id,
    )
    assert interrupted_status.status == 200
    assert (
        interrupted_status.json()["upload_session"]["offset_bytes"]
        == MAX_CHUNK_BYTES
    )
    second = api.chunk(
        workspace_id,
        token,
        actor,
        session_id,
        offset=MAX_CHUNK_BYTES,
        chunk=second_chunk,
    )
    assert second.status == 204
    tail = api.chunk(
        workspace_id,
        token,
        actor,
        session_id,
        offset=2 * MAX_CHUNK_BYTES,
        chunk=payload[2 * MAX_CHUNK_BYTES :],
    )
    assert tail.status == 204
    completed = api.complete(workspace_id, token, actor, session_id)
    assert completed.status == 200
    downloaded = api.download(workspace_id, token, actor)
    assert downloaded.body == payload
    assert not list(
        (state_dir / "walking-skeleton" / "tmp").glob("*.chunk")
    )
    return {
        "restart_count": 1,
        "mid_chunk_disconnect_count": 1,
        "partial_chunk_accepted": 0,
        "resumed_offset_bytes": MAX_CHUNK_BYTES,
        "duplicate_chunk_extra_copies": 0,
        "download_sha256": hashlib.sha256(payload).hexdigest(),
    }


def _negative_oracles(api: Api) -> dict[str, int]:
    over_workspace, over_token, over_actor = api.create_workspace(
        "P6.1 overlimit"
    )
    over = api.create_session(
        over_workspace,
        over_token,
        over_actor,
        name="over.bin",
        media_type="application/octet-stream",
        payload=b"",
        size_bytes=MAX_FILE_BYTES + 1,
        sha256=hashlib.sha256(b"").hexdigest(),
        key="p61-e2e-overlimit-0001",
    )
    assert over.status == 413
    assert over.json()["detail"] == "artifact_too_large"

    tamper_workspace, tamper_token, tamper_actor = api.create_workspace(
        "P6.1 tamper"
    )
    payload = b"tamper-check"
    created = api.create_session(
        tamper_workspace,
        tamper_token,
        tamper_actor,
        name="tamper.bin",
        media_type="application/octet-stream",
        payload=payload,
        key="p61-e2e-tamper-0001",
    )
    session_id = _session_id(created)
    tampered = api.chunk(
        tamper_workspace,
        tamper_token,
        tamper_actor,
        session_id,
        offset=0,
        chunk=payload,
        checksum=hashlib.sha256(b"different").hexdigest(),
    )
    assert tampered.status == 409
    assert tampered.json()["detail"] == "upload_chunk_checksum_mismatch"
    status = api.session(
        tamper_workspace,
        tamper_token,
        tamper_actor,
        session_id,
    )
    assert status.json()["upload_session"]["offset_bytes"] == 0

    full_workspace, full_token, full_actor = api.create_workspace(
        "P6.1 full hash"
    )
    full_created = api.create_session(
        full_workspace,
        full_token,
        full_actor,
        name="full.bin",
        media_type="application/octet-stream",
        payload=payload,
        sha256=hashlib.sha256(b"wrong-full").hexdigest(),
        key="p61-e2e-full-tamper-0001",
    )
    full_session = _session_id(full_created)
    assert api.chunk(
        full_workspace,
        full_token,
        full_actor,
        full_session,
        offset=0,
        chunk=payload,
    ).status == 204
    full_complete = api.complete(
        full_workspace,
        full_token,
        full_actor,
        full_session,
    )
    assert full_complete.status == 409
    assert full_complete.json()["detail"] == "upload_checksum_mismatch"
    return {
        "overlimit_bytes_written": 0,
        "tampered_chunk_accepted": 0,
        "tampered_full_file_published": 0,
    }


def _concurrency_oracle(api: Api) -> dict[str, int]:
    workspace_id, token, actor = api.create_workspace("P6.1 concurrent")
    payload = b"concurrent-identical-chunk"
    created = api.create_session(
        workspace_id,
        token,
        actor,
        name="concurrent.bin",
        media_type="application/octet-stream",
        payload=payload,
        key="p61-e2e-concurrent-0001",
    )
    session_id = _session_id(created)

    def send() -> HttpResult:
        return api.chunk(
            workspace_id,
            token,
            actor,
            session_id,
            offset=0,
            chunk=payload,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: send(), range(2)))
    assert [result.status for result in results] == [204, 204]
    status = api.session(workspace_id, token, actor, session_id)
    assert status.json()["upload_session"]["offset_bytes"] == len(payload)
    assert status.json()["upload_session"]["chunk_count"] == 1
    assert api.complete(
        workspace_id,
        token,
        actor,
        session_id,
    ).status == 200
    return {
        "concurrent_requests": 2,
        "accepted_responses": 2,
        "durable_chunk_copies": 1,
    }


def _rollback_oracle(
    api: Api,
    preserved: tuple[str, str, dict[str, str], str],
) -> dict[str, Any]:
    workspace_id, token, actor, expected_hash = preserved
    status = api.request("GET", "/status")
    assert status.status == 200
    assert status.json()["resumable_upload"]["enabled"] is False
    downloaded = api.download(workspace_id, token, actor)
    assert hashlib.sha256(downloaded.body).hexdigest() == expected_hash

    new_workspace, new_token, new_actor = api.create_workspace(
        "P6.1 standard rollback"
    )
    disabled = api.create_session(
        new_workspace,
        new_token,
        new_actor,
        name="disabled.bin",
        media_type="application/octet-stream",
        payload=b"x",
        key="p61-e2e-disabled-0001",
    )
    assert disabled.status == 404
    standard_payload = b"standard-upload-still-works"
    standard = api.request(
        "PUT",
        f"/workspaces/{new_workspace}/artifact",
        body=standard_payload,
        headers={
            **api.auth(new_token, new_actor),
            "Content-Type": "application/octet-stream",
            "X-KMFA-Filename": "standard.bin",
            "Idempotency-Key": "p61-e2e-standard-0001",
        },
    )
    assert standard.status == 200, standard.body
    return {
        "resumable_enabled": False,
        "existing_download_hash_preserved": True,
        "standard_upload_status": standard.status,
        "state_deleted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--container-name", default="kmfa-p61-e2e")
    parser.add_argument("--port", type=int, default=18106)
    args = parser.parse_args()

    assert CONTAINER_RE.fullmatch(args.container_name)
    args.state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    assert not any(args.state_dir.iterdir()), (
        "state-dir must be initially empty; refusing to overwrite evidence"
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    image_id = _run(
        "docker",
        "image",
        "inspect",
        "--format",
        "{{.Id}}",
        args.image,
    ).stdout.strip()
    assert image_id.startswith("sha256:")

    container = Container(
        name=args.container_name,
        image=args.image,
        state_dir=args.state_dir.resolve(),
        port=args.port,
    )
    log_samples: list[str] = []
    capabilities: list[str] = []
    try:
        container.start(resumable=True)
        api = Api(container.base_url, capabilities)
        contract = api.request("GET", "/status").json()["resumable_upload"]
        assert contract == {
            "enabled": True,
            "protocol": "kmfa-offset-v1",
            "max_file_bytes": MAX_FILE_BYTES,
            "max_chunk_bytes": MAX_CHUNK_BYTES,
            "max_sessions_per_workspace": 16,
            "checksum": "sha256",
            "attachment_only_until_classified": True,
            "standard_upload_rollback": True,
        }
        fixture_hashes = [
            _upload_fixture(
                api,
                index=index,
                name=name,
                media_type=media_type,
                payload=payload,
            )
            for index, (name, media_type, payload) in enumerate(FIXTURES, 1)
        ]
        interruption = _interruption_oracle(api, container, args.state_dir)
        negatives = _negative_oracles(api)
        concurrency = _concurrency_oracle(api)

        preserved_workspace, preserved_token, preserved_actor = (
            api.create_workspace("P6.1 rollback preserved")
        )
        preserved_payload = b"preserved-across-flag-rollback"
        preserved_created = api.create_session(
            preserved_workspace,
            preserved_token,
            preserved_actor,
            name="preserved.bin",
            media_type="application/octet-stream",
            payload=preserved_payload,
            key="p61-e2e-preserved-0001",
        )
        preserved_session = _session_id(preserved_created)
        assert api.chunk(
            preserved_workspace,
            preserved_token,
            preserved_actor,
            preserved_session,
            offset=0,
            chunk=preserved_payload,
        ).status == 204
        assert api.complete(
            preserved_workspace,
            preserved_token,
            preserved_actor,
            preserved_session,
        ).status == 200
        preserved_hash = hashlib.sha256(preserved_payload).hexdigest()
        chunk_root = args.state_dir / "walking-skeleton" / "tmp"
        incomplete_chunks_before = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in chunk_root.glob("*.chunk")
        }
        assert len(incomplete_chunks_before) == 1
        log_samples.append(container.logs())

        container.remove()
        container.start(resumable=False)
        api = Api(container.base_url, capabilities)
        rollback = _rollback_oracle(
            api,
            (
                preserved_workspace,
                preserved_token,
                preserved_actor,
                preserved_hash,
            ),
        )
        incomplete_chunks_after = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in chunk_root.glob("*.chunk")
        }
        assert incomplete_chunks_after == incomplete_chunks_before
        rollback["incomplete_chunks_preserved"] = len(
            incomplete_chunks_after
        )
        log_samples.append(container.logs())
        joined_logs = "\n".join(log_samples)
        assert not any(secret in joined_logs for secret in capabilities)

        object_files = list(
            (args.state_dir / "walking-skeleton" / "objects").glob("*.blob")
        )
        assert len(object_files) == len(FIXTURES) + 4
        result = {
            "schema_version": "kmfa.s06.p61.resumable-upload-e2e.v1",
            "status": "PASS",
            "image_id": image_id,
            "synthetic_only": True,
            "capabilities_persisted": False,
            "contract": contract,
            "file_type_cases": len(FIXTURES),
            "file_type_hashes": fixture_hashes,
            "attachment_only_cases": len(FIXTURES),
            "execution_successes": 0,
            "interruption": interruption,
            "negative_oracles": negatives,
            "concurrency": concurrency,
            "rollback": rollback,
            "object_count": len(object_files),
            "unexplained_failures": 0,
        }
        output = args.out_dir / "summary.json"
        output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        assert output.stat().st_size <= 64 * 1024
        print(json.dumps(result, ensure_ascii=False))
        return 0
    finally:
        container.remove()


if __name__ == "__main__":
    raise SystemExit(main())
