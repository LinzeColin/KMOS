#!/usr/bin/env python3
"""S05/P5.2 private S3-compatible object storage acceptance Oracle.

The script owns uniquely prefixed Docker resources and uses synthetic bytes
only. It proves private/prefix-scoped access, immutable application versions,
deep checksum reconciliation, two App nodes, object-service replacement,
browser-independent recovery and write-adapter rollback. It does not exercise
P5.3 deletion lifecycle or P5.4 backup/restore.
"""

from __future__ import annotations

import argparse
import hashlib
import http.cookiejar
import json
import os
import re
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import quote

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

REPO = Path(__file__).resolve().parents[3]
BACKEND = REPO / "KMFA" / "app" / "backend"
sys.path.insert(0, str(BACKEND))

from app.object_reconciliation import reconcile_s3_store  # noqa: E402
from app.object_storage import (  # noqa: E402
    ObjectStorageConflictError,
    S3_STORAGE_BACKEND,
    S3ObjectStore,
    content_md5_base64,
)
from app.structured_repository import StructuredRepository  # noqa: E402
from app.structured_store import open_structured_store  # noqa: E402

API_PREFIX = "/public-api/walking-skeleton/v1"
SESSION_COOKIE_NAME = "__Secure-kmfa_session"
ACCESS_RE = re.compile(r"^kmfa-a1-[A-Za-z0-9_-]{43}$")
RECOVERY_RE = re.compile(r"^kmfa-r1-[A-Za-z0-9_-]{43}$")
PREFIX_RE = re.compile(r"^kmfa-p52-[a-z0-9-]{1,32}$")
POSTGRES_IMAGE = "postgres:17.10-alpine3.23"
MINIO_IMAGE = (
    "minio/minio:RELEASE.2025-09-07T16-13-09Z"
    "@sha256:14cea493d9a34af32f524e538b8346cf79f3321eff8e708c1e2960462bd8936e"
)
MC_IMAGE = (
    "minio/mc:RELEASE.2025-08-13T08-35-41Z"
    "@sha256:a7fe349ef4bd8521fb8497f55c6042871b2ae640607cf99d9bede5e9bdf11727"
)
PG_DATABASE = "kmfa_p52"
PG_USER = "kmfa_p52"
S3_BUCKET = "kmfa-private-artifacts"
S3_PREFIX = "kmfa/private/v1"
S3_REGION = "us-east-1"
POLICY_PATH = REPO / "KMFA" / "app" / "object-store-policy.json"
FIXTURES = (
    ("same-name.unknown", "application/octet-stream", b""),
    (
        "same-name.unknown",
        "application/x-kmfa-unknown",
        b"\x00KMFA-P52-SYNTHETIC\xff\n" + bytes(range(256)) * 17,
    ),
    (
        "same-name.unknown",
        "application/pdf",
        b"\x00KMFA-P52-SYNTHETIC\xff\n" + bytes(range(256)) * 17,
    ),
    (
        "large.synthetic.double.exe.unknown",
        "video/x-kmfa-synthetic",
        bytes(range(256)) * 8193,
    ),
)


def _timestamp() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _redact(value: str, sensitive_values: Sequence[str] = ()) -> str:
    redacted = value
    for sensitive in sensitive_values:
        redacted = redacted.replace(sensitive, "[REDACTED]")
    redacted = re.sub(
        r"kmfa-(?:a1|r1)-[A-Za-z0-9_-]{43}",
        "[REDACTED-CAPABILITY]",
        redacted,
    )
    redacted = re.sub(
        r"postgres(?:ql)?://[^\s\"']+",
        "postgresql://[REDACTED]",
        redacted,
    )
    return redacted


def _run(
    *arguments: str,
    check: bool = True,
    environment: Mapping[str, str] | None = None,
    sensitive_values: Sequence[str] = (),
) -> subprocess.CompletedProcess[str]:
    process_environment = os.environ.copy()
    if environment:
        process_environment.update(environment)
    result = subprocess.run(
        list(arguments),
        capture_output=True,
        text=True,
        check=False,
        env=process_environment,
    )
    if check and result.returncode != 0:
        detail = _redact(result.stdout + result.stderr, sensitive_values)
        raise AssertionError(f"owned Docker command failed: {detail[-4000:]}")
    return result


def _docker_exists(kind: str, name: str) -> bool:
    if kind == "container":
        return _run("docker", "inspect", name, check=False).returncode == 0
    if kind == "network":
        return _run(
            "docker", "network", "inspect", name, check=False
        ).returncode == 0
    if kind == "volume":
        return _run(
            "docker", "volume", "inspect", name, check=False
        ).returncode == 0
    raise ValueError("unsupported Docker resource kind")


def _host_port(container: str, internal_port: int) -> int:
    result = _run("docker", "port", container, f"{internal_port}/tcp")
    return int(result.stdout.strip().splitlines()[0].rsplit(":", 1)[1])


def _wait_http(url: str, timeout: float = 90) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.5)
    raise AssertionError("HTTP readiness timeout")


def _wait_postgresql(container: str, timeout: float = 60) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ready = _run(
            "docker",
            "exec",
            container,
            "pg_isready",
            "-U",
            PG_USER,
            "-d",
            PG_DATABASE,
            check=False,
        )
        if ready.returncode == 0:
            return
        time.sleep(0.5)
    raise AssertionError("PostgreSQL readiness timeout")


def _request(
    base_url: str,
    method: str,
    path: str,
    *,
    payload: bytes | None = None,
    headers: dict[str, str] | None = None,
    opener: urllib.request.OpenerDirector | None = None,
    timeout: float = 20,
) -> tuple[int, bytes, Any]:
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=payload,
        method=method,
        headers=headers or {},
    )
    sender = opener.open if opener is not None else urllib.request.urlopen
    try:
        with sender(request, timeout=timeout) as response:
            return response.status, response.read(), response.headers
    except urllib.error.HTTPError as error:
        return error.code, error.read(), error.headers


def _json_request(
    base_url: str,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    *,
    token: str | None = None,
    opener: urllib.request.OpenerDirector | None = None,
) -> tuple[int, dict[str, Any], Any]:
    payload = None
    headers = {"Accept": "application/json"}
    if body is not None:
        payload = json.dumps(body, ensure_ascii=True).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    status, raw, response_headers = _request(
        base_url,
        method,
        path,
        payload=payload,
        headers=headers,
        opener=opener,
    )
    return (
        status,
        json.loads(raw.decode("utf-8")) if raw else {},
        response_headers,
    )


def _cookie_token(headers: Any) -> str:
    cookie = str(headers.get("Set-Cookie", ""))
    match = re.search(
        rf"(?:^|[,;]\s*){re.escape(SESSION_COOKIE_NAME)}=([^;]+)",
        cookie,
    )
    assert match is not None
    token = match.group(1)
    assert ACCESS_RE.fullmatch(token)
    assert "Secure" in cookie and "HttpOnly" in cookie
    assert "SameSite=strict" in cookie
    return token


def _s3_client(
    endpoint_url: str,
    access_key: str,
    secret_key: str,
):
    return boto3.session.Session().client(
        "s3",
        endpoint_url=endpoint_url,
        region_name=S3_REGION,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        verify=False,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )


def _assert_access_denied(operation: Callable[[], Any]) -> None:
    try:
        operation()
    except ClientError as error:
        assert str(error.response["Error"]["Code"]) in {
            "AccessDenied",
            "Forbidden",
        }
    else:
        raise AssertionError("prefix-scoped credential exceeded its policy")


class OwnedResources:
    def __init__(self, prefix: str, image: str, state_dir: Path) -> None:
        self.prefix = prefix
        self.image = image
        self.state_dir = state_dir
        self.network = f"{prefix}-net"
        self.pg_volume = f"{prefix}-pgdata"
        self.object_volume = f"{prefix}-objectdata"
        self.postgres = f"{prefix}-pg"
        self.object_store = f"{prefix}-object"
        self.pg_password = f"p52-pg-{secrets.token_hex(16)}"
        self.minio_root_user = f"p52root{secrets.token_hex(5)}"
        self.minio_root_password = f"p52-root-{secrets.token_hex(20)}"
        self.s3_access_key = f"p52app{secrets.token_hex(6)}"
        self.s3_secret_key = f"p52-app-{secrets.token_hex(20)}"
        self.apps: set[str] = set()
        self.owned: set[tuple[str, str]] = set()

    @property
    def sensitive_values(self) -> tuple[str, ...]:
        return (
            self.pg_password,
            self.minio_root_user,
            self.minio_root_password,
            self.s3_access_key,
            self.s3_secret_key,
        )

    @property
    def internal_dsn(self) -> str:
        return (
            f"postgresql://{PG_USER}:{self.pg_password}@{self.postgres}:5432/"
            f"{PG_DATABASE}"
        )

    @property
    def host_dsn(self) -> str:
        return (
            f"postgresql://{PG_USER}:{self.pg_password}@127.0.0.1:"
            f"{_host_port(self.postgres, 5432)}/{PG_DATABASE}"
        )

    @property
    def internal_s3_endpoint(self) -> str:
        return "http://object-store:9000"

    @property
    def host_s3_endpoint(self) -> str:
        return f"http://127.0.0.1:{_host_port(self.object_store, 9000)}"

    def initialize(self) -> None:
        targets = (
            ("network", self.network),
            ("volume", self.pg_volume),
            ("volume", self.object_volume),
            ("container", self.postgres),
            ("container", self.object_store),
        )
        for kind, name in targets:
            assert not _docker_exists(kind, name), (
                f"refusing to replace pre-existing {kind} {name}"
            )
        self.state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.state_dir.chmod(0o700)
        _run("docker", "network", "create", self.network)
        self.owned.add(("network", self.network))
        for volume in (self.pg_volume, self.object_volume):
            _run("docker", "volume", "create", volume)
            self.owned.add(("volume", volume))
        self.start_postgresql()
        self.start_object_store()
        self.bootstrap_object_store()

    def start_postgresql(self) -> None:
        environment = {"POSTGRES_PASSWORD": self.pg_password}
        _run(
            "docker",
            "run",
            "-d",
            "--name",
            self.postgres,
            "--network",
            self.network,
            "-p",
            "127.0.0.1::5432",
            "-e",
            "POSTGRES_PASSWORD",
            "-e",
            f"POSTGRES_DB={PG_DATABASE}",
            "-e",
            f"POSTGRES_USER={PG_USER}",
            "-v",
            f"{self.pg_volume}:/var/lib/postgresql/data",
            POSTGRES_IMAGE,
            environment=environment,
            sensitive_values=self.sensitive_values,
        )
        self.owned.add(("container", self.postgres))
        _wait_postgresql(self.postgres)

    def start_object_store(self) -> None:
        environment = {
            "MINIO_ROOT_USER": self.minio_root_user,
            "MINIO_ROOT_PASSWORD": self.minio_root_password,
        }
        _run(
            "docker",
            "run",
            "-d",
            "--name",
            self.object_store,
            "--network",
            self.network,
            "--network-alias",
            "object-store",
            "-p",
            "127.0.0.1::9000",
            "-e",
            "MINIO_ROOT_USER",
            "-e",
            "MINIO_ROOT_PASSWORD",
            "-v",
            f"{self.object_volume}:/data",
            MINIO_IMAGE,
            "server",
            "/data",
            "--console-address",
            ":9001",
            environment=environment,
            sensitive_values=self.sensitive_values,
        )
        self.owned.add(("container", self.object_store))
        _wait_http(
            f"{self.host_s3_endpoint}/minio/health/ready",
            timeout=60,
        )

    def bootstrap_object_store(self) -> None:
        environment = {
            "MC_HOST_admin": (
                f"http://{self.minio_root_user}:{self.minio_root_password}"
                "@object-store:9000"
            ),
            "P52_APP_KEY": self.s3_access_key,
            "P52_APP_SECRET": self.s3_secret_key,
        }
        script = """
          mc mb --ignore-existing admin/kmfa-private-artifacts
          mc anonymous set none admin/kmfa-private-artifacts
          mc version enable admin/kmfa-private-artifacts
          mc admin user add admin "$P52_APP_KEY" "$P52_APP_SECRET"
          mc admin policy create admin kmfa-private-artifacts /policy/object-store-policy.json
          mc admin policy attach admin kmfa-private-artifacts --user "$P52_APP_KEY"
        """
        _run(
            "docker",
            "run",
            "--rm",
            "--network",
            self.network,
            "-e",
            "MC_HOST_admin",
            "-e",
            "P52_APP_KEY",
            "-e",
            "P52_APP_SECRET",
            "-v",
            f"{POLICY_PATH}:/policy/object-store-policy.json:ro",
            "--entrypoint",
            "/bin/sh",
            MC_IMAGE,
            "-ec",
            script,
            environment=environment,
            sensitive_values=self.sensitive_values,
        )

    def replace_object_store(self) -> None:
        _run("docker", "rm", "-f", self.object_store)
        self.owned.discard(("container", self.object_store))
        self.start_object_store()

    def start_app(
        self,
        suffix: str,
        *,
        storage_mode: str = "s3",
    ) -> tuple[str, str]:
        name = f"{self.prefix}-app-{suffix}"
        assert not _docker_exists("container", name)
        environment = {
            "KMFA_STRUCTURED_DATABASE_URL": self.internal_dsn,
            "KMFA_S3_ACCESS_KEY_ID": self.s3_access_key,
            "KMFA_S3_SECRET_ACCESS_KEY": self.s3_secret_key,
        }
        _run(
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "--network",
            self.network,
            "-p",
            "127.0.0.1::8000",
            "-e",
            "KMFA_WALKING_SKELETON_ENABLED=1",
            "-e",
            "KMFA_PUBLIC_INDEXING_ENABLED=0",
            "-e",
            "KMFA_PRIVATE_OPS_REQUIRE_ACCESS=1",
            "-e",
            "KMFA_STRUCTURED_DATABASE_MODE=postgresql-primary",
            "-e",
            "KMFA_STRUCTURED_DATABASE_URL",
            "-e",
            f"KMFA_ARTIFACT_STORAGE_MODE={storage_mode}",
            "-e",
            f"KMFA_S3_ENDPOINT_URL={self.internal_s3_endpoint}",
            "-e",
            f"KMFA_S3_BUCKET={S3_BUCKET}",
            "-e",
            f"KMFA_S3_REGION={S3_REGION}",
            "-e",
            f"KMFA_S3_PREFIX={S3_PREFIX}",
            "-e",
            "KMFA_S3_ACCESS_KEY_ID",
            "-e",
            "KMFA_S3_SECRET_ACCESS_KEY",
            "-e",
            "KMFA_S3_ADDRESSING_STYLE=path",
            "-e",
            "KMFA_S3_ALLOW_INSECURE_LOCAL=1",
            "-v",
            f"{self.state_dir}:/var/lib/kmfa/state",
            self.image,
            environment=environment,
            sensitive_values=self.sensitive_values,
        )
        self.apps.add(name)
        self.owned.add(("container", name))
        base_url = f"http://127.0.0.1:{_host_port(name, 8000)}"
        _wait_http(f"{base_url}/healthz")
        status, payload, _ = _json_request(
            base_url,
            "GET",
            f"{API_PREFIX}/status",
        )
        assert status == 200 and payload["healthy"] is True
        return name, base_url

    def remove_app(self, name: str) -> None:
        if name in self.apps:
            _run("docker", "rm", "-f", name)
            self.apps.remove(name)
            self.owned.discard(("container", name))

    def logs(self) -> str:
        chunks: list[str] = []
        for kind, name in sorted(self.owned):
            if kind != "container":
                continue
            result = _run("docker", "logs", name, check=False)
            chunks.append(result.stdout + result.stderr)
        return "\n".join(chunks)

    def cleanup(self) -> None:
        for kind, name in sorted(self.owned, reverse=True):
            if kind == "container":
                _run("docker", "rm", "-f", name, check=False)
        self.apps.clear()
        for kind, name in sorted(self.owned, reverse=True):
            if kind == "volume":
                _run("docker", "volume", "rm", name, check=False)
            elif kind == "network":
                _run("docker", "network", "rm", name, check=False)
        self.owned.clear()


def _configure_host_clients(resources: OwnedResources) -> None:
    os.environ.update(
        {
            "KMFA_STRUCTURED_DATABASE_MODE": "postgresql-primary",
            "KMFA_STRUCTURED_DATABASE_URL": resources.host_dsn,
            "KMFA_ARTIFACT_STORAGE_MODE": "s3",
            "KMFA_S3_ENDPOINT_URL": resources.host_s3_endpoint,
            "KMFA_S3_BUCKET": S3_BUCKET,
            "KMFA_S3_REGION": S3_REGION,
            "KMFA_S3_PREFIX": S3_PREFIX,
            "KMFA_S3_ACCESS_KEY_ID": resources.s3_access_key,
            "KMFA_S3_SECRET_ACCESS_KEY": resources.s3_secret_key,
            "KMFA_S3_ADDRESSING_STYLE": "path",
            "KMFA_S3_ALLOW_INSECURE_LOCAL": "1",
        }
    )


def _capture_object(client, key: str) -> dict[str, Any]:
    head = client.head_object(Bucket=S3_BUCKET, Key=key)
    response = client.get_object(Bucket=S3_BUCKET, Key=key)
    try:
        body = response["Body"].read()
    finally:
        response["Body"].close()
    return {
        "body": body,
        "metadata": dict(head["Metadata"]),
        "content_type": head.get("ContentType", "application/octet-stream"),
        "cache_control": head.get("CacheControl", "private, no-store"),
        "content_disposition": head.get("ContentDisposition", "attachment"),
        "version_id": head.get("VersionId"),
    }


def _public_safe_reconciliation(report: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "indexed_objects",
        "inventory_objects",
        "consistent_objects",
        "normal_object_consistency_rate",
        "anomaly_count",
        "anomaly_counts",
        "classified_anomalies",
        "unexplained_anomalies",
        "repair_states_deterministic",
        "pass_gate",
    )
    return {key: report[key] for key in keys}


def run_oracle(resources: OwnedResources) -> dict[str, Any]:
    app_a, url_a = resources.start_app("a")
    app_b, url_b = resources.start_app("b")
    status_a = _json_request(url_a, "GET", f"{API_PREFIX}/status")[1]
    assert status_a["structured_store"] == "postgresql-shared-service-adapter"
    assert status_a["artifact_storage"]["write_backend"] == S3_STORAGE_BACKEND
    assert status_a["artifact_storage"][
        "application_issues_public_object_urls"
    ] is False

    sessions: list[dict[str, str]] = []
    fixture_hashes: list[str] = []
    for index, (filename, media_type, fixture) in enumerate(FIXTURES):
        base_url = url_a if index % 2 == 0 else url_b
        created_status, created, headers = _json_request(
            base_url,
            "POST",
            f"{API_PREFIX}/workspaces",
            {"project_name": f"S05 P5.2 synthetic object {index}"},
        )
        assert created_status == 201
        token = _cookie_token(headers)
        recovery = str(created["recovery_code"])
        assert RECOVERY_RE.fullmatch(recovery)
        workspace_id = str(created["workspace"]["workspace_id"])
        upload_status, upload_raw, _ = _request(
            base_url,
            "PUT",
            f"{API_PREFIX}/workspaces/{workspace_id}/artifact",
            payload=fixture,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": media_type,
                "X-KMFA-Filename": quote(filename, safe=""),
            },
        )
        assert upload_status == 200, upload_raw.decode("utf-8", errors="replace")
        fixture_sha256 = hashlib.sha256(fixture).hexdigest()
        assert json.loads(upload_raw.decode("utf-8"))["artifact"]["sha256"] == (
            fixture_sha256
        )
        fixture_hashes.append(fixture_sha256)
        sessions.append(
            {
                "workspace_id": workspace_id,
                "token": token,
                "recovery": recovery,
            }
        )

    assert fixture_hashes[1] == fixture_hashes[2]
    assert len(set(fixture_hashes)) == 3
    _configure_host_clients(resources)
    connection = open_structured_store(Path("/tmp/kmfa-p52-unused.sqlite3"))
    try:
        repository = StructuredRepository(connection)
        index_rows = [
            dict(row)
            for row in repository.artifact_object_index(
                storage_backend=S3_STORAGE_BACKEND
            )
        ]
        assert len(index_rows) == len(FIXTURES)
        assert len({row["storage_key"] for row in index_rows}) == len(FIXTURES)
        for index, session in enumerate(sessions):
            metadata_row = connection.execute(
                """
                SELECT
                  av.version_number,
                  av.storage_backend,
                  av.original_name,
                  av.reported_media_type,
                  av.size_bytes,
                  av.sha256,
                  av.lifecycle_state
                FROM artifact_versions av
                JOIN projects p ON p.project_id = av.project_id
                WHERE p.workspace_id = ?
                """,
                (session["workspace_id"],),
            ).fetchone()
            assert dict(metadata_row) == {
                "version_number": 1,
                "storage_backend": S3_STORAGE_BACKEND,
                "original_name": FIXTURES[index][0],
                "reported_media_type": FIXTURES[index][1],
                "size_bytes": len(FIXTURES[index][2]),
                "sha256": fixture_hashes[index],
                "lifecycle_state": "active",
            }
        normal_report = reconcile_s3_store(
            connection,
            S3ObjectStore.from_environment(resources.state_dir),
        )
    finally:
        connection.close()
    assert normal_report["pass_gate"] is True
    assert normal_report["normal_object_consistency_rate"] == 1.0

    # The adapter refuses a second create for the same immutable version key.
    store = S3ObjectStore.from_environment(resources.state_dir)
    selected = index_rows[0]
    materialized = store.materialize_verified(
        storage_key=str(selected["storage_key"]),
        expected_size=int(selected["size_bytes"]),
        expected_sha256=str(selected["sha256"]),
    )
    fixture_md5 = hashlib.md5(
        materialized.path.read_bytes(),
        usedforsecurity=False,
    )
    try:
        try:
            store.put_file(
                materialized.path,
                storage_key=str(selected["storage_key"]),
                size_bytes=int(selected["size_bytes"]),
                sha256=str(selected["sha256"]),
                content_md5=content_md5_base64(fixture_md5),
                artifact_id=str(selected["artifact_id"]),
                artifact_version_id=str(selected["artifact_version_id"]),
            )
        except ObjectStorageConflictError:
            pass
        else:
            raise AssertionError("immutable object overwrite was not rejected")
    finally:
        materialized.path.unlink(missing_ok=True)

    anonymous_key = quote(str(selected["storage_key"]), safe="/")
    anonymous_status, _, _ = _request(
        resources.host_s3_endpoint,
        "GET",
        f"/{S3_BUCKET}/{anonymous_key}",
    )
    anonymous_list_status, _, _ = _request(
        resources.host_s3_endpoint,
        "GET",
        f"/{S3_BUCKET}?list-type=2",
    )
    assert anonymous_status == 403 and anonymous_list_status == 403

    scoped_client = _s3_client(
        resources.host_s3_endpoint,
        resources.s3_access_key,
        resources.s3_secret_key,
    )
    _assert_access_denied(
        lambda: scoped_client.put_object(
            Bucket=S3_BUCKET,
            Key="outside-prefix/denied.synthetic",
            Body=b"denied",
            IfNoneMatch="*",
        )
    )
    _assert_access_denied(
        lambda: scoped_client.get_object(
            Bucket=S3_BUCKET,
            Key="outside-prefix/denied.synthetic",
        )
    )
    _assert_access_denied(
        lambda: scoped_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix="outside-prefix/",
        )
    )
    _assert_access_denied(
        lambda: scoped_client.delete_object(
            Bucket=S3_BUCKET,
            Key=str(selected["storage_key"]),
        )
    )

    root_client = _s3_client(
        resources.host_s3_endpoint,
        resources.minio_root_user,
        resources.minio_root_password,
    )
    assert root_client.get_bucket_versioning(Bucket=S3_BUCKET)["Status"] == "Enabled"
    native_versions_before = root_client.list_object_versions(Bucket=S3_BUCKET)
    assert len(native_versions_before.get("Versions", [])) == len(FIXTURES)

    # Every object is readable from the other application node.
    for index, session in enumerate(sessions):
        base_url = url_b if index % 2 == 0 else url_a
        status, downloaded, headers = _request(
            base_url,
            "POST",
            (
                f"{API_PREFIX}/workspaces/{session['workspace_id']}"
                "/artifact/download"
            ),
            headers={"Authorization": f"Bearer {session['token']}"},
        )
        assert status == 200 and downloaded == FIXTURES[index][2]
        assert headers["X-KMFA-Artifact-SHA256"] == fixture_hashes[index]

    # An object dependency outage is explicit and does not change DB rows.
    _run("docker", "stop", "--time", "5", resources.object_store)
    outage_status, outage, _ = _json_request(
        url_a,
        "GET",
        f"{API_PREFIX}/status",
    )
    assert outage_status == 503
    assert outage["detail"] == "walking_skeleton_storage_unavailable"
    resources.replace_object_store()
    _configure_host_clients(resources)

    connection = open_structured_store(Path("/tmp/kmfa-p52-unused.sqlite3"))
    try:
        assert len(
            StructuredRepository(connection).artifact_object_index(
                storage_backend=S3_STORAGE_BACKEND
            )
        ) == len(FIXTURES)
    finally:
        connection.close()

    # Fresh browser state recovers server-side DB index and object bytes.
    jar = http.cookiejar.CookieJar()
    fresh_browser = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(jar)
    )
    recovered_status, recovered, recovered_headers = _json_request(
        url_b,
        "POST",
        f"{API_PREFIX}/recoveries",
        {"recovery_code": sessions[0]["recovery"]},
        opener=fresh_browser,
    )
    assert recovered_status == 200
    recovered_token = _cookie_token(recovered_headers)
    assert recovered["workspace"]["workspace_id"] == sessions[0]["workspace_id"]
    recovered_download, recovered_bytes, _ = _request(
        url_b,
        "POST",
        (
            f"{API_PREFIX}/workspaces/{sessions[0]['workspace_id']}"
            "/artifact/download"
        ),
        headers={"Authorization": f"Bearer {recovered_token}"},
    )
    assert recovered_download == 200 and recovered_bytes == FIXTURES[0][2]

    # Switching only the write adapter leaves S3-backed versions readable.
    resources.remove_app(app_a)
    _, rollback_url = resources.start_app("rollback", storage_mode="legacy-filesystem")
    rollback_status = _json_request(
        rollback_url,
        "GET",
        f"{API_PREFIX}/status",
    )[1]
    assert rollback_status["artifact_storage"]["write_backend"] == (
        "legacy-private-filesystem"
    )
    assert rollback_status["artifact_storage"]["s3_dual_read_configured"] is True
    rollback_download, rollback_bytes, _ = _request(
        rollback_url,
        "POST",
        (
            f"{API_PREFIX}/workspaces/{sessions[1]['workspace_id']}"
            "/artifact/download"
        ),
        headers={"Authorization": f"Bearer {sessions[1]['token']}"},
    )
    assert rollback_download == 200 and rollback_bytes == FIXTURES[1][2]

    # Manufacture one missing object, one byte/checksum mismatch and one orphan.
    root_client = _s3_client(
        resources.host_s3_endpoint,
        resources.minio_root_user,
        resources.minio_root_password,
    )
    missing_row, mismatch_row = index_rows[:2]
    missing_key = str(missing_row["storage_key"])
    mismatch_key = str(mismatch_row["storage_key"])
    missing_original = _capture_object(root_client, missing_key)
    mismatch_original = _capture_object(root_client, mismatch_key)
    delete_result = root_client.delete_object(Bucket=S3_BUCKET, Key=missing_key)
    missing_delete_marker_version = str(delete_result["VersionId"])
    tampered = root_client.put_object(
        Bucket=S3_BUCKET,
        Key=mismatch_key,
        Body=b"synthetic-tampered-version",
        Metadata=mismatch_original["metadata"],
        ContentType="application/octet-stream",
        CacheControl="private, no-store",
        ContentDisposition="attachment",
    )
    tampered_version = str(tampered["VersionId"])
    orphan_key = (
        f"{S3_PREFIX}/artifacts/orphan-synthetic/"
        f"{secrets.token_hex(12)}.blob"
    )
    orphan_body = b"synthetic-orphan"
    orphan_result = root_client.put_object(
        Bucket=S3_BUCKET,
        Key=orphan_key,
        Body=orphan_body,
        Metadata={
            "kmfa-sha256": hashlib.sha256(orphan_body).hexdigest(),
            "kmfa-artifact-id": "artifact_orphan_synthetic",
            "kmfa-artifact-version-id": "version_orphan_synthetic",
            "kmfa-versioning": "immutable-key-v1",
        },
        ContentType="application/octet-stream",
        CacheControl="private, no-store",
        ContentDisposition="attachment",
    )
    orphan_version = str(orphan_result["VersionId"])

    _configure_host_clients(resources)
    connection = open_structured_store(Path("/tmp/kmfa-p52-unused.sqlite3"))
    try:
        anomaly_report = reconcile_s3_store(
            connection,
            S3ObjectStore.from_environment(resources.state_dir),
        )
    finally:
        connection.close()
    assert anomaly_report["anomaly_counts"] == {
        "missing_object": 1,
        "object_metadata_mismatch": 1,
        "orphan_object": 1,
    }
    assert anomaly_report["classified_anomalies"] == 3
    assert anomaly_report["unexplained_anomalies"] == 0
    assert anomaly_report["repair_states_deterministic"] is True

    # Apply only the deterministic synthetic repair and prove a green rescan.
    root_client.delete_object(
        Bucket=S3_BUCKET,
        Key=missing_key,
        VersionId=missing_delete_marker_version,
    )
    root_client.delete_object(
        Bucket=S3_BUCKET,
        Key=mismatch_key,
        VersionId=tampered_version,
    )
    root_client.delete_object(
        Bucket=S3_BUCKET,
        Key=orphan_key,
        VersionId=orphan_version,
    )
    assert _capture_object(root_client, missing_key)["body"] == missing_original["body"]
    assert _capture_object(root_client, mismatch_key)["body"] == (
        mismatch_original["body"]
    )

    connection = open_structured_store(Path("/tmp/kmfa-p52-unused.sqlite3"))
    try:
        final_report = reconcile_s3_store(
            connection,
            S3ObjectStore.from_environment(resources.state_dir),
        )
    finally:
        connection.close()
    assert final_report["pass_gate"] is True
    assert final_report["normal_object_consistency_rate"] == 1.0

    capabilities = tuple(
        value
        for session in sessions
        for value in (session["token"], session["recovery"])
    ) + (recovered_token,)
    logs = resources.logs()
    assert not any(value in logs for value in capabilities)
    assert not any(value in logs for value in resources.sensitive_values)

    image_id = _run(
        "docker", "image", "inspect", resources.image, "--format", "{{.Id}}"
    ).stdout.strip()
    minio_image_id = _run(
        "docker", "image", "inspect", MINIO_IMAGE, "--format", "{{.Id}}"
    ).stdout.strip()
    postgres_image_id = _run(
        "docker", "image", "inspect", POSTGRES_IMAGE, "--format", "{{.Id}}"
    ).stdout.strip()
    return {
        "schema_version": "kmfa.s05.p52.object-storage-oracle.v1",
        "status": "PASS",
        "completed_at": _timestamp(),
        "synthetic_only": True,
        "application_image_id": image_id,
        "object_store_image": MINIO_IMAGE,
        "object_store_image_id": minio_image_id,
        "postgres_image": POSTGRES_IMAGE,
        "postgres_image_id": postgres_image_id,
        "storage_backend": S3_STORAGE_BACKEND,
        "application_versioning": "immutable-key-v1",
        "native_bucket_versioning": "Enabled",
        "fixture_count": len(FIXTURES),
        "fixture_sizes": [len(item[2]) for item in FIXTURES],
        "fixture_sha256": fixture_hashes,
        "same_filename_count": Counter(item[0] for item in FIXTURES)[
            "same-name.unknown"
        ],
        "duplicate_content_count": Counter(fixture_hashes)[fixture_hashes[1]],
        "normal_reconciliation": _public_safe_reconciliation(normal_report),
        "anomaly_reconciliation": _public_safe_reconciliation(anomaly_report),
        "final_reconciliation": _public_safe_reconciliation(final_report),
        "checks": {
            "two_application_nodes_shared_objects": "PASS",
            "multi_type_and_size_original_bytes": "PASS",
            "same_name_separate_keys": "PASS",
            "duplicate_content_separate_versions": "PASS",
            "conditional_overwrite_rejected": "PASS",
            "native_bucket_versioning_enabled": "PASS",
            "anonymous_get_and_list_denied": "PASS",
            "credential_prefix_escape_denied": "PASS",
            "credential_delete_denied": "PASS",
            "database_metadata_and_lineage_complete": "PASS",
            "database_object_inventory_consistency_100_percent": "PASS",
            "missing_mismatch_orphan_all_classified": "PASS",
            "unexplained_anomalies_zero": "PASS",
            "deterministic_repair_rescan_consistent": "PASS",
            "object_store_outage_explicit_503": "PASS",
            "object_container_replacement_same_volume": "PASS",
            "browser_state_cleared_recovery": "PASS",
            "legacy_write_rollback_s3_dual_read": "PASS",
            "capability_and_credential_log_scan": "PASS",
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--prefix", default="kmfa-p52-e2e")
    return parser


def _prepare_empty_directory(path: Path, label: str) -> None:
    if path.exists():
        if not path.is_dir() or any(path.iterdir()):
            raise SystemExit(f"{label} must be an empty dedicated directory")
    else:
        path.mkdir(mode=0o700, parents=True)
    path.chmod(0o700)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if PREFIX_RE.fullmatch(arguments.prefix) is None:
        raise SystemExit("invalid owned Docker resource prefix")
    out_dir = arguments.out_dir.resolve()
    state_dir = arguments.state_dir.resolve()
    _prepare_empty_directory(out_dir, "out-dir")
    _prepare_empty_directory(state_dir, "state-dir")
    resources = OwnedResources(arguments.prefix, arguments.image, state_dir)
    try:
        resources.initialize()
        report = run_oracle(resources)
        encoded = json.dumps(
            report,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        assert ACCESS_RE.search(encoded) is None
        assert RECOVERY_RE.search(encoded) is None
        assert not any(secret in encoded for secret in resources.sensitive_values)
        (out_dir / "object-storage-oracle.json").write_text(
            encoded + "\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "application_image_id": report["application_image_id"],
                    "normal_consistency_rate": report[
                        "normal_reconciliation"
                    ]["normal_object_consistency_rate"],
                    "classified_anomalies": report[
                        "anomaly_reconciliation"
                    ]["classified_anomalies"],
                    "unexplained_anomalies": report[
                        "anomaly_reconciliation"
                    ]["unexplained_anomalies"],
                    "checks_passed": len(report["checks"]),
                },
                sort_keys=True,
            )
        )
        return 0
    finally:
        resources.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
