#!/usr/bin/env python3
"""S05/P5.4 retention, backup, restore and non-resurrection Oracle.

The Oracle uses only synthetic records and uniquely owned Docker resources. It
restores a full + logical-incremental chain into an empty PostgreSQL + versioned
MinIO environment, exercises the application, then proves explicit deletion,
legal hold, public-effect purge, retry, all-version removal and tombstone
restore. Only a bounded public-safe report is written to ``--out-dir``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import quote

import boto3
from botocore.config import Config

REPO = Path(__file__).resolve().parents[3]
APP_POLICY = REPO / "KMFA" / "app" / "object-store-policy.json"
LIFECYCLE_POLICY = (
    REPO / "KMFA" / "app" / "object-store-lifecycle-policy.json"
)
WORKER = (
    "/opt/kmfa/KMOS/KMFA/app/e2e/retention_backup_worker.py"
)
POSTGRES_IMAGE = (
    "postgres:17.10-alpine3.23@"
    "sha256:8189a1f6e40904781fc9e2612687877791d21679866db58b1de996b31fc312e4"
)
MINIO_IMAGE = (
    "minio/minio:RELEASE.2025-09-07T16-13-09Z@"
    "sha256:14cea493d9a34af32f524e538b8346cf79f3321eff8e708c1e2960462bd8936e"
)
MC_IMAGE = (
    "minio/mc:RELEASE.2025-08-13T08-35-41Z@"
    "sha256:a7fe349ef4bd8521fb8497f55c6042871b2ae640607cf99d9bede5e9bdf11727"
)
API_PREFIX = "/public-api/walking-skeleton/v1"
SESSION_COOKIE_NAME = "__Secure-kmfa_session"
PREFIX_RE = re.compile(r"^kmfa-p54-[a-z0-9][a-z0-9-]{1,24}$")
ACCESS_RE = re.compile(r"^kmfa-a1-[A-Za-z0-9_-]{43}$")
RECOVERY_RE = re.compile(r"^kmfa-r1-[A-Za-z0-9_-]{43}$")
FIXTURE = b"KMFA-S05-P54-SYNTHETIC\x00\xff\n" + bytes(range(256)) * 13
FIXTURE_SHA256 = hashlib.sha256(FIXTURE).hexdigest()
S3_BUCKET = "kmfa-private-artifacts"
S3_PREFIX = "kmfa/private/v1"
EXPECTED_DATABASE_SCHEMA_VERSION = 6


def _timestamp() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _redact(value: str, sensitive_values: Sequence[str] = ()) -> str:
    redacted = value
    for sensitive in sensitive_values:
        if sensitive:
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
    timeout: int = 240,
    sensitive_values: Sequence[str] = (),
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(arguments),
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        detail = _redact(
            result.stdout + "\n" + result.stderr,
            sensitive_values,
        )
        raise AssertionError(
            f"owned Docker command failed ({result.returncode}): "
            f"{arguments[0]}\n{detail[-5000:]}"
        )
    return result


def _parse_json(output: str) -> dict[str, Any]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        raise AssertionError("expected JSON output")
    parsed = json.loads(lines[-1])
    if not isinstance(parsed, dict):
        raise AssertionError("JSON output must be an object")
    return parsed


def _docker_exists(kind: str, name: str) -> bool:
    command = {
        "container": ("docker", "inspect", name),
        "network": ("docker", "network", "inspect", name),
        "volume": ("docker", "volume", "inspect", name),
    }[kind]
    return _run(*command, check=False, timeout=20).returncode == 0


def _host_port(container: str, internal_port: int) -> int:
    result = _run("docker", "port", container, f"{internal_port}/tcp")
    return int(result.stdout.strip().splitlines()[0].rsplit(":", 1)[1])


def _wait_postgresql(container: str, *, user: str, database: str) -> None:
    for _ in range(120):
        result = _run(
            "docker",
            "exec",
            container,
            "pg_isready",
            "-U",
            user,
            "-d",
            database,
            check=False,
            timeout=10,
        )
        if result.returncode == 0:
            return
        time.sleep(0.5)
    raise AssertionError("PostgreSQL readiness timeout")


def _wait_http(url: str) -> None:
    for _ in range(180):
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.5)
    raise AssertionError("HTTP readiness timeout")


def _request(
    base_url: str,
    method: str,
    path: str,
    *,
    payload: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, bytes, Any]:
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=payload,
        method=method,
        headers=headers or {},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
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
    extra_headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any], Any]:
    headers = {"Accept": "application/json", **(extra_headers or {})}
    payload = None
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
    if match is None or ACCESS_RE.fullmatch(match.group(1)) is None:
        raise AssertionError("secure session cookie missing")
    if not all(value in cookie for value in ("Secure", "HttpOnly", "SameSite=strict")):
        raise AssertionError("secure session cookie attributes missing")
    return match.group(1)


class DrillEnvironment:
    def __init__(
        self,
        *,
        prefix: str,
        label: str,
        image: str,
        state_dir: Path,
    ) -> None:
        self.prefix = prefix
        self.label = label
        self.image = image
        self.state_dir = state_dir
        self.network = f"{prefix}-{label}-net"
        self.postgres = f"{prefix}-{label}-pg"
        self.object_store = f"{prefix}-{label}-object"
        self.app = f"{prefix}-{label}-app"
        self.pg_volume = f"{prefix}-{label}-pgdata"
        self.object_volume = f"{prefix}-{label}-objectdata"
        self.database = "kmfa"
        self.database_user = "kmfa"
        self.database_password = f"p54-{label}-{secrets.token_hex(12)}"
        self.root_user = f"p54{label}root"
        self.root_secret = f"p54-{label}-root-{secrets.token_hex(12)}"
        self.app_user = f"p54{label}app"
        self.app_secret = f"p54-{label}-app-{secrets.token_hex(12)}"
        self.lifecycle_user = f"p54{label}lifecycle"
        self.lifecycle_secret = (
            f"p54-{label}-lifecycle-{secrets.token_hex(12)}"
        )
        self.base_url: str | None = None
        self.owned = False

    @property
    def sensitive_values(self) -> tuple[str, ...]:
        return (
            self.database_password,
            self.root_user,
            self.root_secret,
            self.app_user,
            self.app_secret,
            self.lifecycle_user,
            self.lifecycle_secret,
            self.database_url,
        )

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.database_user}:{self.database_password}@"
            f"{self.postgres}:5432/{self.database}"
        )

    @property
    def state_root(self) -> str:
        return f"/oracle/{self.label}-state"

    def initialize(self) -> None:
        for kind, name in (
            ("network", self.network),
            ("volume", self.pg_volume),
            ("volume", self.object_volume),
            ("container", self.postgres),
            ("container", self.object_store),
            ("container", self.app),
        ):
            if _docker_exists(kind, name):
                raise AssertionError(
                    f"refusing to replace pre-existing {kind} {name}"
                )
        (self.state_dir / f"{self.label}-state").mkdir(
            mode=0o700,
            parents=True,
            exist_ok=False,
        )
        _run("docker", "network", "create", self.network)
        _run("docker", "volume", "create", self.pg_volume)
        _run("docker", "volume", "create", self.object_volume)
        self.owned = True
        _run(
            "docker",
            "run",
            "-d",
            "--name",
            self.postgres,
            "--network",
            self.network,
            "-e",
            f"POSTGRES_DB={self.database}",
            "-e",
            f"POSTGRES_USER={self.database_user}",
            "-e",
            f"POSTGRES_PASSWORD={self.database_password}",
            "-v",
            f"{self.pg_volume}:/var/lib/postgresql/data",
            POSTGRES_IMAGE,
            sensitive_values=self.sensitive_values,
        )
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
            f"MINIO_ROOT_USER={self.root_user}",
            "-e",
            f"MINIO_ROOT_PASSWORD={self.root_secret}",
            "-v",
            f"{self.object_volume}:/data",
            MINIO_IMAGE,
            "server",
            "/data",
            "--console-address",
            ":9001",
            sensitive_values=self.sensitive_values,
        )
        _wait_postgresql(
            self.postgres,
            user=self.database_user,
            database=self.database,
        )
        _wait_http(
            f"http://127.0.0.1:{_host_port(self.object_store, 9000)}"
            "/minio/health/ready"
        )
        bootstrap = """
set -eu
mc alias set local http://object-store:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
mc mb --ignore-existing "local/$KMFA_S3_BUCKET"
mc anonymous set none "local/$KMFA_S3_BUCKET"
mc version enable "local/$KMFA_S3_BUCKET"
mc admin user add local "$KMFA_S3_ACCESS_KEY_ID" "$KMFA_S3_SECRET_ACCESS_KEY"
mc admin policy create local kmfa-p54-app /policy/app.json
mc admin policy attach local kmfa-p54-app --user "$KMFA_S3_ACCESS_KEY_ID"
mc admin user add local \
  "$KMFA_S3_LIFECYCLE_ACCESS_KEY_ID" \
  "$KMFA_S3_LIFECYCLE_SECRET_ACCESS_KEY"
mc admin policy create local kmfa-p54-lifecycle /policy/lifecycle.json
mc admin policy attach local kmfa-p54-lifecycle \
  --user "$KMFA_S3_LIFECYCLE_ACCESS_KEY_ID"
"""
        _run(
            "docker",
            "run",
            "--rm",
            "--network",
            self.network,
            "-e",
            f"MINIO_ROOT_USER={self.root_user}",
            "-e",
            f"MINIO_ROOT_PASSWORD={self.root_secret}",
            "-e",
            f"KMFA_S3_BUCKET={S3_BUCKET}",
            "-e",
            f"KMFA_S3_ACCESS_KEY_ID={self.app_user}",
            "-e",
            f"KMFA_S3_SECRET_ACCESS_KEY={self.app_secret}",
            "-e",
            f"KMFA_S3_LIFECYCLE_ACCESS_KEY_ID={self.lifecycle_user}",
            "-e",
            (
                "KMFA_S3_LIFECYCLE_SECRET_ACCESS_KEY="
                f"{self.lifecycle_secret}"
            ),
            "-v",
            f"{APP_POLICY}:/policy/app.json:ro",
            "-v",
            f"{LIFECYCLE_POLICY}:/policy/lifecycle.json:ro",
            "--entrypoint",
            "/bin/sh",
            MC_IMAGE,
            "-ec",
            bootstrap,
            sensitive_values=self.sensitive_values,
        )

    def _environment_arguments(
        self,
        *,
        lifecycle_mode: str,
        consistency_mode: str,
        include_lifecycle_credentials: bool,
    ) -> list[str]:
        values = {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": "/opt/kmfa/KMOS/KMFA/app/backend",
            "KMFA_WALKING_SKELETON_ENABLED": "1",
            "KMFA_WALKING_SKELETON_STATE_DIR": self.state_root,
            "KMFA_STRUCTURED_DATABASE_MODE": "postgresql-primary",
            "KMFA_STRUCTURED_DATABASE_URL": self.database_url,
            "KMFA_ARTIFACT_STORAGE_MODE": "s3",
            "KMFA_S3_ENDPOINT_URL": "http://object-store:9000",
            "KMFA_S3_BUCKET": S3_BUCKET,
            "KMFA_S3_REGION": "us-east-1",
            "KMFA_S3_PREFIX": S3_PREFIX,
            "KMFA_S3_ACCESS_KEY_ID": self.app_user,
            "KMFA_S3_SECRET_ACCESS_KEY": self.app_secret,
            "KMFA_S3_ADDRESSING_STYLE": "path",
            "KMFA_S3_ALLOW_INSECURE_LOCAL": "1",
            "KMFA_CONSISTENCY_STATE_MODE": consistency_mode,
            "KMFA_LIFECYCLE_MODE": lifecycle_mode,
            "KMFA_ABUSE_POLICY_MODE": "enforced",
        }
        if include_lifecycle_credentials:
            values.update(
                {
                    "KMFA_S3_LIFECYCLE_ACCESS_KEY_ID": self.lifecycle_user,
                    "KMFA_S3_LIFECYCLE_SECRET_ACCESS_KEY": (
                        self.lifecycle_secret
                    ),
                }
            )
        arguments: list[str] = []
        for key, value in values.items():
            arguments.extend(("-e", f"{key}={value}"))
        return arguments

    def image_command(
        self,
        arguments: Sequence[str],
        *,
        lifecycle_mode: str,
        consistency_mode: str,
        include_lifecycle_credentials: bool = False,
    ) -> dict[str, Any]:
        command = [
            "docker",
            "run",
            "--rm",
            "--network",
            self.network,
            *self._environment_arguments(
                lifecycle_mode=lifecycle_mode,
                consistency_mode=consistency_mode,
                include_lifecycle_credentials=include_lifecycle_credentials,
            ),
            "-v",
            f"{self.state_dir}:/oracle",
            self.image,
            *arguments,
        ]
        result = _run(
            *command,
            sensitive_values=self.sensitive_values,
        )
        return _parse_json(result.stdout)

    def helper(
        self,
        arguments: Sequence[str],
        *,
        lifecycle_mode: str = "paused",
        include_lifecycle_credentials: bool = False,
    ) -> dict[str, Any]:
        return self.image_command(
            ["python3", WORKER, *arguments],
            lifecycle_mode=lifecycle_mode,
            consistency_mode="recoverable-v1",
            include_lifecycle_credentials=include_lifecycle_credentials,
        )

    def start_app(self, *, lifecycle_mode: str) -> str:
        if _docker_exists("container", self.app):
            raise AssertionError("application container already exists")
        _run(
            "docker",
            "run",
            "-d",
            "--name",
            self.app,
            "--network",
            self.network,
            "-p",
            "127.0.0.1::8000",
            *self._environment_arguments(
                lifecycle_mode=lifecycle_mode,
                consistency_mode="recoverable-v1",
                include_lifecycle_credentials=False,
            ),
            "-v",
            f"{self.state_dir}:/oracle",
            self.image,
            sensitive_values=self.sensitive_values,
        )
        self.base_url = (
            f"http://127.0.0.1:{_host_port(self.app, 8000)}"
        )
        _wait_http(f"{self.base_url}/healthz")
        return self.base_url

    def stop_app(self) -> None:
        _run("docker", "rm", "-f", self.app, check=False, timeout=30)
        self.base_url = None

    def root_s3(self):
        port = _host_port(self.object_store, 9000)
        return boto3.client(
            "s3",
            endpoint_url=f"http://127.0.0.1:{port}",
            region_name="us-east-1",
            aws_access_key_id=self.root_user,
            aws_secret_access_key=self.root_secret,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            ),
        )

    def exact_versions(self, key: str) -> list[tuple[str, bool]]:
        response = self.root_s3().list_object_versions(
            Bucket=S3_BUCKET,
            Prefix=key,
        )
        versions = [
            (str(item["VersionId"]), False)
            for item in response.get("Versions", [])
            if str(item["Key"]) == key
        ]
        markers = [
            (str(item["VersionId"]), True)
            for item in response.get("DeleteMarkers", [])
            if str(item["Key"]) == key
        ]
        return versions + markers

    def inject_historical_versions(self) -> tuple[str, int]:
        client = self.root_s3()
        response = client.list_object_versions(
            Bucket=S3_BUCKET,
            Prefix=f"{S3_PREFIX}/artifacts/",
        )
        keys = {
            str(item["Key"])
            for item in response.get("Versions", [])
            if str(item["Key"]).startswith(f"{S3_PREFIX}/artifacts/")
        }
        if len(keys) != 1:
            raise AssertionError("expected one exact synthetic object key")
        key = next(iter(keys))
        head = client.head_object(Bucket=S3_BUCKET, Key=key)
        metadata = dict(head["Metadata"])
        for _ in range(2):
            client.put_object(
                Bucket=S3_BUCKET,
                Key=key,
                Body=FIXTURE,
                ContentLength=len(FIXTURE),
                ContentType="application/octet-stream",
                Metadata=metadata,
            )
        client.delete_object(Bucket=S3_BUCKET, Key=key)
        count = len(self.exact_versions(key))
        if count < 4:
            raise AssertionError("provider version fixture was not established")
        return key, count

    def object_count(self) -> int:
        response = self.root_s3().list_object_versions(
            Bucket=S3_BUCKET,
            Prefix=f"{S3_PREFIX}/artifacts/",
        )
        return sum(
            1
            for field in ("Versions", "DeleteMarkers")
            for item in response.get(field, [])
            if str(item["Key"]).startswith(f"{S3_PREFIX}/artifacts/")
        )

    def cleanup(self) -> None:
        if not self.owned:
            return
        self.stop_app()
        for container in (self.postgres, self.object_store):
            _run("docker", "rm", "-f", container, check=False, timeout=30)
        for volume in (self.pg_volume, self.object_volume):
            _run("docker", "volume", "rm", volume, check=False, timeout=30)
        _run("docker", "network", "rm", self.network, check=False, timeout=30)
        self.owned = False


class Oracle:
    def __init__(
        self,
        *,
        image: str,
        state_dir: Path,
        out_dir: Path,
        prefix: str,
        source_commit: str,
    ) -> None:
        self.image = image
        self.state_dir = state_dir.resolve()
        self.out_dir = out_dir.resolve()
        self.prefix = prefix
        self.source_commit = source_commit
        self.environments: list[DrillEnvironment] = []

    def environment(self, label: str) -> DrillEnvironment:
        environment = DrillEnvironment(
            prefix=self.prefix,
            label=label,
            image=self.image,
            state_dir=self.state_dir,
        )
        self.environments.append(environment)
        environment.initialize()
        return environment

    def cleanup(self) -> None:
        for environment in reversed(self.environments):
            environment.cleanup()

    def execute(self) -> dict[str, Any]:
        self.state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.state_dir.chmod(0o700)
        if any(self.state_dir.iterdir()):
            raise AssertionError("state directory must be empty")
        self.out_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        backups = self.state_dir / "backups"
        backups.mkdir(mode=0o700)
        image_id = _run(
            "docker",
            "image",
            "inspect",
            self.image,
            "--format",
            "{{.Id}}",
        ).stdout.strip()
        artifact_identity = f"{self.source_commit}/{image_id}"

        source = self.environment("source")
        source_url = source.start_app(lifecycle_mode="paused")
        created_status, created, created_headers = _json_request(
            source_url,
            "POST",
            f"{API_PREFIX}/workspaces",
            {"project_name": "P5.4 synthetic recovery fixture"},
        )
        if created_status != 201:
            raise AssertionError("source workspace creation failed")
        token = _cookie_token(created_headers)
        recovery_code = str(created["recovery_code"])
        workspace_id = str(created["workspace"]["workspace_id"])
        if RECOVERY_RE.fullmatch(recovery_code) is None:
            raise AssertionError("source recovery capability invalid")
        upload_status, upload_raw, _ = _request(
            source_url,
            "PUT",
            f"{API_PREFIX}/workspaces/{workspace_id}/artifact",
            payload=FIXTURE,
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": "p54-oracle-upload-idempotency-0001",
                "X-KMFA-Filename": quote(
                    "p54.synthetic.double.exe.unknown",
                    safe="",
                ),
                "Content-Type": "application/x-kmfa-synthetic",
            },
        )
        if upload_status != 200:
            raise AssertionError(
                f"source upload failed: {upload_raw[:200]!r}"
            )
        seeded = source.helper(["seed", "--workspace-id", workspace_id])
        if (
            seeded["score"] != 91
            or seeded["financial_record_count"] != 1
            or seeded["task_count"] != 1
        ):
            raise AssertionError("structured fixture seed failed")
        source.stop_app()

        full = source.image_command(
            [
                "python3",
                "-m",
                "app.backup_restore",
                "backup",
                "--destination",
                "/oracle/backups/full",
                "--kind",
                "full",
                "--artifact-identity",
                artifact_identity,
                "--backup-id",
                "backup_p54_full_000001",
            ],
            lifecycle_mode="paused",
            consistency_mode="paused",
        )
        if full["status"] != "pass" or full["object_upserts"] != 1:
            raise AssertionError("full backup failed acceptance")

        source_url = source.start_app(lifecycle_mode="paused")
        updated_status, updated, _ = _json_request(
            source_url,
            "PATCH",
            f"{API_PREFIX}/workspaces/{workspace_id}",
            {"progress": 73},
            token=token,
        )
        if updated_status != 200 or updated["progress"] != 73:
            raise AssertionError("incremental source mutation failed")
        source.stop_app()
        incremental = source.image_command(
            [
                "python3",
                "-m",
                "app.backup_restore",
                "backup",
                "--destination",
                "/oracle/backups/incremental",
                "--kind",
                "incremental",
                "--parent",
                "/oracle/backups/full",
                "--artifact-identity",
                artifact_identity,
                "--backup-id",
                "backup_p54_incremental_000001",
            ],
            lifecycle_mode="paused",
            consistency_mode="paused",
        )
        if (
            incremental["status"] != "pass"
            or incremental["table_upserts"] < 1
            or incremental["object_upserts"] != 0
            or incremental["object_deletes"] != 0
        ):
            raise AssertionError("incremental backup failed acceptance")
        source.cleanup()

        target = self.environment("target")
        restore = target.image_command(
            [
                "python3",
                "-m",
                "app.backup_restore",
                "restore",
                "--chain",
                "/oracle/backups/full",
                "--chain",
                "/oracle/backups/incremental",
                "--incident-at",
                _timestamp(),
            ],
            lifecycle_mode="paused",
            consistency_mode="paused",
            include_lifecycle_credentials=True,
        )
        if (
            restore["status"] != "pass"
            or restore["invariant_failures"] != 0
            or restore["restored_objects"] != 1
        ):
            raise AssertionError("isolated restore failed invariants")
        proof = target.image_command(
            [
                "python3",
                "-m",
                "app.backup_restore",
                "record-proof",
                "--backup-id",
                str(restore["backup_id"]),
                "--manifest-sha256",
                str(restore["manifest_sha256"]),
                "--expected-fixtures",
                "1",
                "--restored-fixtures",
                "1",
                "--invariant-failures",
                str(restore["invariant_failures"]),
                "--measured-rpo-ms",
                str(restore["measured_rpo_ms"]),
                "--measured-rto-ms",
                str(restore["measured_rto_ms"]),
                "--artifact-identity-hash",
                str(restore["artifact_identity_hash"]),
                "--proof-id",
                "proof_p54_oracle_000001",
            ],
            lifecycle_mode="paused",
            consistency_mode="paused",
        )
        if proof["status"] != "pass":
            raise AssertionError("restore proof recording failed")

        target_url = target.start_app(lifecycle_mode="active")
        recovered_status, recovered, recovered_headers = _json_request(
            target_url,
            "POST",
            f"{API_PREFIX}/recoveries",
            {"recovery_code": recovery_code},
        )
        recovered_token = _cookie_token(recovered_headers)
        if (
            recovered_status != 200
            or recovered["workspace"]["progress"] != 73
        ):
            raise AssertionError("application recovery failed")
        download_status, downloaded, _ = _request(
            target_url,
            "POST",
            f"{API_PREFIX}/workspaces/{workspace_id}/artifact/download",
            headers={"Authorization": f"Bearer {recovered_token}"},
        )
        if (
            download_status != 200
            or downloaded != FIXTURE
            or hashlib.sha256(downloaded).hexdigest() != FIXTURE_SHA256
        ):
            raise AssertionError("restored application download failed")
        restored_summary = target.helper(
            ["summary", "--workspace-id", workspace_id]
        )
        if (
            restored_summary["schema_version"]
            != EXPECTED_DATABASE_SCHEMA_VERSION
            or restored_summary["retention_state"] != "active"
            or restored_summary["project_count"] != 1
            or restored_summary["score"] != 91
            or restored_summary["financial_record_count"] != 1
            or restored_summary["task_count"] != 1
            or restored_summary["artifact_count"] != 1
            or restored_summary["due_deletion_count"] != 0
            or restored_summary["passed_restore_proof_count"] != 1
        ):
            raise AssertionError("restored structured fixture mismatch")
        status_code, status_payload, _ = _json_request(
            target_url,
            "GET",
            f"{API_PREFIX}/status",
        )
        retention_contract = status_payload.get("retention_lifecycle", {})
        if (
            status_code != 200
            or retention_contract.get("default_auto_expiry") is not False
            or retention_contract.get("restore_drill_proof_current_schema")
            is not True
            or retention_contract.get(
                "application_object_delete_credentials"
            )
            is not False
            or retention_contract.get("worker_uses_separate_credentials")
            is not True
            or retention_contract.get("worker_lease_seconds") != 600
        ):
            raise AssertionError("retention status contract mismatch")

        wrong_token_status, _, _ = _json_request(
            target_url,
            "DELETE",
            f"{API_PREFIX}/workspaces/{workspace_id}",
            {
                "confirmation": "delete-workspace",
                "workspace_secret": recovery_code,
            },
            token="kmfa-a1-" + "A" * 43,
            extra_headers={
                "Idempotency-Key": "p54-wrong-token-idempotency-0001"
            },
        )
        wrong_secret_status, _, _ = _json_request(
            target_url,
            "DELETE",
            f"{API_PREFIX}/workspaces/{workspace_id}",
            {
                "confirmation": "delete-workspace",
                "workspace_secret": "kmfa-r1-" + "A" * 43,
            },
            token=recovered_token,
            extra_headers={
                "Idempotency-Key": "p54-wrong-secret-idempotency-0001"
            },
        )
        if wrong_token_status != 404 or wrong_secret_status != 404:
            raise AssertionError("unauthorized deletion did not fail closed")

        hold_id = "hold_p54_oracle_000001"
        target.helper(
            [
                "hold",
                "--action",
                "impose",
                "--workspace-id",
                workspace_id,
                "--hold-id",
                hold_id,
            ]
        )
        held_status, held_payload, _ = _json_request(
            target_url,
            "DELETE",
            f"{API_PREFIX}/workspaces/{workspace_id}",
            {
                "confirmation": "delete-workspace",
                "workspace_secret": recovery_code,
            },
            token=recovered_token,
            extra_headers={
                "Idempotency-Key": "p54-held-delete-idempotency-0001"
            },
        )
        if (
            held_status != 409
            or held_payload.get("detail") != "workspace_legal_hold"
        ):
            raise AssertionError("legal hold did not block deletion")
        held_download_status, held_download, _ = _request(
            target_url,
            "POST",
            f"{API_PREFIX}/workspaces/{workspace_id}/artifact/download",
            headers={"Authorization": f"Bearer {recovered_token}"},
        )
        if held_download_status != 200 or held_download != FIXTURE:
            raise AssertionError("legal hold damaged retained data")
        target.helper(
            [
                "hold",
                "--action",
                "release",
                "--workspace-id",
                workspace_id,
                "--hold-id",
                hold_id,
            ]
        )

        publication_id = "publication_p54_oracle_000001"
        target.helper(
            [
                "publication",
                "--workspace-id",
                workspace_id,
                "--publication-id",
                publication_id,
            ]
        )
        effects_file = "/oracle/target-state/publication-effects.json"
        initialized_effects = target.helper(
            [
                "effects",
                "--action",
                "initialize",
                "--effects-file",
                effects_file,
                "--publication-id",
                publication_id,
            ]
        )
        if any(
            initialized_effects[f"{field}_count"] != 1
            for field in ("active", "cached", "indexed")
        ):
            raise AssertionError("public effects fixture initialization failed")
        storage_key, provider_versions_before = (
            target.inject_historical_versions()
        )
        accepted_status, accepted, _ = _json_request(
            target_url,
            "DELETE",
            f"{API_PREFIX}/workspaces/{workspace_id}",
            {
                "confirmation": "delete-workspace",
                "workspace_secret": recovery_code,
            },
            token=recovered_token,
            extra_headers={
                "Idempotency-Key": "p54-authorized-delete-idempotency-0001"
            },
        )
        if accepted_status != 202:
            raise AssertionError("authorized deletion was not accepted")
        deletion_request_id = str(accepted["deletion_request_id"])
        first_attempt = target.helper(
            [
                "process",
                "--deletion-request-id",
                deletion_request_id,
                "--effects-file",
                effects_file,
                "--fail-object-delete",
            ],
            lifecycle_mode="active",
            include_lifecycle_credentials=True,
        )
        if (
            first_attempt["request_state"] != "retry"
            or first_attempt["public_purge_within_sla"] is not True
            or len(target.exact_versions(storage_key))
            != provider_versions_before
        ):
            raise AssertionError("retry safety invariant failed")
        effects_after_first = target.helper(
            [
                "effects",
                "--action",
                "summary",
                "--effects-file",
                effects_file,
            ]
        )
        if any(
            effects_after_first[f"{field}_count"] != 0
            for field in ("active", "cached", "indexed")
        ):
            raise AssertionError("public effects were not fully purged")

        completed = target.helper(
            [
                "process",
                "--deletion-request-id",
                deletion_request_id,
                "--effects-file",
                effects_file,
            ],
            lifecycle_mode="active",
            include_lifecycle_credentials=True,
        )
        if (
            completed["request_state"] != "completed"
            or completed["public_purge_within_sla"] is not True
            or target.exact_versions(storage_key)
        ):
            raise AssertionError("authorized deletion did not converge")
        deleted_summary = target.helper(
            ["summary", "--workspace-id", workspace_id]
        )
        if (
            deleted_summary["retention_state"] != "deleted"
            or deleted_summary["project_count"] != 0
            or deleted_summary["financial_record_count"] != 0
            or deleted_summary["task_count"] != 0
            or deleted_summary["artifact_count"] != 0
            or deleted_summary["completed_deletion_event_count"] != 1
            or target.object_count() != 0
        ):
            raise AssertionError("deletion final state mismatch")
        missing_status, _, _ = _json_request(
            target_url,
            "POST",
            f"{API_PREFIX}/recoveries",
            {"recovery_code": recovery_code},
        )
        if missing_status != 404:
            raise AssertionError("deleted recovery capability remained active")
        target.stop_app()

        tombstone = target.image_command(
            [
                "python3",
                "-m",
                "app.backup_restore",
                "backup",
                "--destination",
                "/oracle/backups/tombstone",
                "--kind",
                "incremental",
                "--parent",
                "/oracle/backups/full",
                "--parent",
                "/oracle/backups/incremental",
                "--artifact-identity",
                artifact_identity,
                "--backup-id",
                "backup_p54_incremental_000002",
            ],
            lifecycle_mode="paused",
            consistency_mode="paused",
        )
        if (
            tombstone["status"] != "pass"
            or tombstone["object_deletes"] != 1
        ):
            raise AssertionError("deletion tombstone backup missing")
        target.cleanup()

        final = self.environment("final")
        final_restore = final.image_command(
            [
                "python3",
                "-m",
                "app.backup_restore",
                "restore",
                "--chain",
                "/oracle/backups/full",
                "--chain",
                "/oracle/backups/incremental",
                "--chain",
                "/oracle/backups/tombstone",
                "--incident-at",
                _timestamp(),
            ],
            lifecycle_mode="paused",
            consistency_mode="paused",
            include_lifecycle_credentials=True,
        )
        if (
            final_restore["status"] != "pass"
            or final_restore["invariant_failures"] != 0
            or final_restore["restored_objects"] != 0
        ):
            raise AssertionError("tombstone restore failed")
        final_summary = final.helper(
            ["summary", "--workspace-id", workspace_id]
        )
        if (
            final_summary["retention_state"] != "deleted"
            or final_summary["project_count"] != 0
            or final_summary["artifact_count"] != 0
            or final_summary["passed_restore_proof_count"] != 0
            or final.object_count() != 0
        ):
            raise AssertionError("deleted data resurrected from backup chain")
        final_url = final.start_app(lifecycle_mode="paused")
        final_recovery_status, _, _ = _json_request(
            final_url,
            "POST",
            f"{API_PREFIX}/recoveries",
            {"recovery_code": recovery_code},
        )
        if final_recovery_status != 404:
            raise AssertionError("tombstone restore reactivated recovery")

        return {
            "schema_version": "kmfa.s05.p54.retention-backup-restore-oracle.v1",
            "status": "PASS",
            "completed_at": _timestamp(),
            "synthetic_only": True,
            "source_commit": self.source_commit,
            "application_image_id": image_id,
            "database_schema_version": EXPECTED_DATABASE_SCHEMA_VERSION,
            "backup_chain": {
                "full_manifest_sha256": full["manifest_sha256"],
                "full_object_upserts": full["object_upserts"],
                "incremental_manifest_sha256": incremental[
                    "manifest_sha256"
                ],
                "incremental_table_upserts": incremental["table_upserts"],
                "incremental_object_upserts": incremental["object_upserts"],
                "tombstone_manifest_sha256": tombstone["manifest_sha256"],
                "tombstone_object_deletes": tombstone["object_deletes"],
                "checksum_closed": True,
            },
            "isolated_restore": {
                "expected_fixture_count": 1,
                "restored_fixture_count": 1,
                "restored_manifest_sha256": restore["manifest_sha256"],
                "invariant_failures": restore["invariant_failures"],
                "restored_object_count": restore["restored_objects"],
                "measured_rpo_ms": restore["measured_rpo_ms"],
                "measured_rto_ms": restore["measured_rto_ms"],
                "application_recovery": "PASS",
                "download_sha256_match": True,
                "progress_restored": 73,
                "score_restored": 91,
                "financial_record_count": 1,
                "task_count": 1,
            },
            "retention_and_deletion": {
                "default_auto_expiry": False,
                "due_without_request": 0,
                "wrong_token_rejected": True,
                "wrong_secret_rejected": True,
                "legal_hold_blocked_without_data_loss": True,
                "public_cache_index_purged_within_sla": True,
                "retry_preserved_object_and_business_rows": True,
                "authorized_deletion_completed": True,
                "provider_versions_before_delete": provider_versions_before,
                "provider_versions_after_delete": 0,
                "accidental_delete_count": 0,
            },
            "non_resurrection": {
                "final_restored_object_count": final_restore[
                    "restored_objects"
                ],
                "deleted_retention_state_preserved": True,
                "business_row_count": 0,
                "active_restore_proofs_after_restore": 0,
                "old_recovery_capability_rejected": True,
            },
            "rollback": {
                "pause_switch": "KMFA_LIFECYCLE_MODE=paused",
                "data_or_volume_delete_required": False,
                "forward_fix_schema": True,
            },
        }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--prefix", default="kmfa-p54-local")
    parser.add_argument("--source-commit")
    arguments = parser.parse_args(argv)
    if PREFIX_RE.fullmatch(arguments.prefix) is None:
        raise SystemExit("invalid Docker resource prefix")
    source_commit = arguments.source_commit
    if source_commit is None:
        source_commit = _run(
            "git",
            "rev-parse",
            "HEAD",
        ).stdout.strip()
    if re.fullmatch(r"[0-9a-f]{40}", source_commit) is None:
        raise SystemExit("source commit must be a full Git SHA")
    oracle = Oracle(
        image=arguments.image,
        state_dir=arguments.state_dir,
        out_dir=arguments.out_dir,
        prefix=arguments.prefix,
        source_commit=source_commit,
    )
    try:
        report = oracle.execute()
        encoded = json.dumps(
            report,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        forbidden = {
            value
            for environment in oracle.environments
            for value in environment.sensitive_values
        }
        forbidden.update(
            {
                S3_PREFIX + "/artifacts/",
                "kmfa-a1-",
                "kmfa-r1-",
            }
        )
        if any(value and value in encoded for value in forbidden):
            raise AssertionError(
                "public Oracle report contains a credential or raw capability"
            )
        report_path = oracle.out_dir / "retention-backup-restore-report.json"
        report_path.write_text(encoded + "\n", encoding="utf-8")
        print(encoded)
    finally:
        oracle.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
