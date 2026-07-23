#!/usr/bin/env python3
"""S05/P5.1 PostgreSQL persistence, rollout, rollback and recovery Oracle.

All records, capabilities, credentials and file bytes are synthetic.  The
script owns its uniquely named Docker resources, removes only those resources,
and writes a bounded public-safe report without raw capabilities or a DSN.
"""

from __future__ import annotations

import argparse
import hashlib
import http.cookiejar
import json
import os
import re
import secrets
import sqlite3
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import quote

REPO = Path(__file__).resolve().parents[3]
BACKEND = REPO / "KMFA" / "app" / "backend"
sys.path.insert(0, str(BACKEND))

from app.legacy_sqlite_import import import_legacy_sqlite  # noqa: E402
from app.structured_repository import (  # noqa: E402
    AcceptanceFixture,
    StructuredDataService,
    StructuredRepository,
)
from app.structured_store import (  # noqa: E402
    StructuredStoreIntegrityError,
    open_structured_store,
)

API_PREFIX = "/public-api/walking-skeleton/v1"
SESSION_COOKIE_NAME = "__Secure-kmfa_session"
ACCESS_RE = re.compile(r"^kmfa-a1-[A-Za-z0-9_-]{43}$")
RECOVERY_RE = re.compile(r"^kmfa-r1-[A-Za-z0-9_-]{43}$")
PREFIX_RE = re.compile(r"^kmfa-p51-[a-z0-9-]{1,32}$")
POSTGRES_IMAGE = "postgres:17.10-alpine3.23"
PG_DATABASE = "kmfa_p51"
PG_USER = "kmfa_p51"
FIXTURE_BYTES = b"KMFA-S05-P51-SYNTHETIC\x00\xff\n" + bytes(range(256)) * 7
FIXTURE_SHA256 = hashlib.sha256(FIXTURE_BYTES).hexdigest()
FIXTURE_NAME = "p51.synthetic.double.exe.unknown"


def _timestamp() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _redact(value: str, sensitive_values: Sequence[str] = ()) -> str:
    redacted = value
    for sensitive_value in sensitive_values:
        redacted = redacted.replace(sensitive_value, "[REDACTED]")
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
    sensitive_values: Sequence[str] = (),
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(arguments),
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        detail = _redact(result.stdout + result.stderr, sensitive_values)
        raise AssertionError(f"owned Docker command failed: {detail[-4000:]}")
    return result


def _docker_exists(kind: str, name: str) -> bool:
    if kind == "container":
        return _run("docker", "inspect", name, check=False).returncode == 0
    if kind == "network":
        return _run("docker", "network", "inspect", name, check=False).returncode == 0
    if kind == "volume":
        return _run("docker", "volume", "inspect", name, check=False).returncode == 0
    raise ValueError("unsupported Docker resource kind")


def _host_port(container: str, internal_port: int) -> int:
    result = _run("docker", "port", container, f"{internal_port}/tcp")
    first = result.stdout.strip().splitlines()[0]
    return int(first.rsplit(":", 1)[1])


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


def _wait_app(base_url: str, timeout: float = 90) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/healthz", timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.5)
    raise AssertionError("application readiness timeout")


def _request(
    base_url: str,
    method: str,
    path: str,
    *,
    payload: bytes | None = None,
    headers: dict[str, str] | None = None,
    opener: urllib.request.OpenerDirector | None = None,
) -> tuple[int, bytes, Any]:
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=payload,
        method=method,
        headers=headers or {},
    )
    sender = opener.open if opener is not None else urllib.request.urlopen
    try:
        with sender(request, timeout=10) as response:
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
    headers = {"Accept": "application/json"}
    payload = None
    if body is not None:
        payload = json.dumps(body, ensure_ascii=True).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    status, raw, response_headers = _request(
        base_url,
        method,
        path,
        payload=payload,
        headers=headers,
        opener=opener,
    )
    decoded = json.loads(raw.decode("utf-8")) if raw else {}
    return status, decoded, response_headers


def _cookie_token(headers: Any) -> str:
    cookie = str(headers.get("Set-Cookie", ""))
    match = re.search(
        rf"(?:^|[,;]\s*){re.escape(SESSION_COOKIE_NAME)}=([^;]+)",
        cookie,
    )
    assert match is not None, "session cookie missing"
    token = match.group(1)
    assert ACCESS_RE.fullmatch(token)
    assert "Secure" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=strict" in cookie
    return token


class OwnedResources:
    def __init__(self, prefix: str, image: str, state_dir: Path) -> None:
        self.prefix = prefix
        self.image = image
        self.state_dir = state_dir
        self.network = f"{prefix}-net"
        self.volume = f"{prefix}-pgdata"
        self.postgres = f"{prefix}-pg"
        self.postgres_password = f"p51-{secrets.token_hex(16)}"
        self.apps: set[str] = set()
        self.postgres_owned = False
        self.network_owned = False
        self.volume_owned = False

    def initialize(self) -> None:
        for kind, name in (
            ("network", self.network),
            ("volume", self.volume),
            ("container", self.postgres),
        ):
            assert not _docker_exists(kind, name), (
                f"refusing to replace pre-existing {kind} {name}"
            )
        self.state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.state_dir.chmod(0o700)
        _run("docker", "network", "create", self.network)
        self.network_owned = True
        _run("docker", "volume", "create", self.volume)
        self.volume_owned = True
        self.start_postgresql()

    def start_postgresql(self) -> None:
        assert not _docker_exists("container", self.postgres)
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
            f"POSTGRES_DB={PG_DATABASE}",
            "-e",
            f"POSTGRES_USER={PG_USER}",
            "-e",
            f"POSTGRES_PASSWORD={self.postgres_password}",
            "-v",
            f"{self.volume}:/var/lib/postgresql/data",
            POSTGRES_IMAGE,
            sensitive_values=(self.postgres_password,),
        )
        self.postgres_owned = True
        _wait_postgresql(self.postgres)

    def replace_postgresql(self) -> None:
        assert self.postgres_owned
        _run("docker", "stop", "--time", "10", self.postgres)
        _run("docker", "rm", self.postgres)
        self.postgres_owned = False
        self.start_postgresql()

    @property
    def internal_dsn(self) -> str:
        return (
            f"postgresql://{PG_USER}:{self.postgres_password}@{self.postgres}:5432/"
            f"{PG_DATABASE}"
        )

    @property
    def host_dsn(self) -> str:
        port = _host_port(self.postgres, 5432)
        return (
            f"postgresql://{PG_USER}:{self.postgres_password}@127.0.0.1:{port}/"
            f"{PG_DATABASE}"
        )

    def start_app(self, suffix: str) -> tuple[str, str]:
        name = f"{self.prefix}-app-{suffix}"
        assert name not in self.apps
        assert not _docker_exists("container", name), (
            f"refusing to replace pre-existing container {name}"
        )
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
            f"KMFA_STRUCTURED_DATABASE_URL={self.internal_dsn}",
            "-v",
            f"{self.state_dir}:/var/lib/kmfa/state",
            self.image,
            sensitive_values=(self.postgres_password,),
        )
        self.apps.add(name)
        base_url = f"http://127.0.0.1:{_host_port(name, 8000)}"
        _wait_app(base_url)
        return name, base_url

    def remove_app(self, name: str) -> None:
        if name in self.apps:
            _run("docker", "rm", "-f", name)
            self.apps.remove(name)

    def logs(self) -> str:
        chunks: list[str] = []
        for name in sorted(self.apps):
            result = _run("docker", "logs", name, check=False)
            chunks.append(result.stdout + result.stderr)
        if self.postgres_owned:
            result = _run("docker", "logs", self.postgres, check=False)
            chunks.append(result.stdout + result.stderr)
        return "\n".join(chunks)

    def cleanup(self) -> None:
        for name in sorted(self.apps):
            _run("docker", "rm", "-f", name, check=False)
        self.apps.clear()
        if self.postgres_owned:
            _run("docker", "rm", "-f", self.postgres, check=False)
            self.postgres_owned = False
        if self.volume_owned:
            _run("docker", "volume", "rm", self.volume, check=False)
            self.volume_owned = False
        if self.network_owned:
            _run("docker", "network", "rm", self.network, check=False)
            self.network_owned = False


def _configure_host_database(dsn: str) -> None:
    os.environ["KMFA_STRUCTURED_DATABASE_MODE"] = "postgresql-primary"
    os.environ["KMFA_STRUCTURED_DATABASE_URL"] = dsn


def _acceptance_fixture(workspace_id: str) -> AcceptanceFixture:
    return AcceptanceFixture(
        workspace_id=workspace_id,
        score=93,
        financial_record_id="finance_p51_synthetic",
        financial_record_type="forecast",
        financial_category="synthetic rollout fixture",
        amount_minor=654_321,
        currency="CNY",
        effective_date="2026-07-23",
        source_ref="synthetic://s05-p51-e2e",
        task_id="task_p51_synthetic",
        task_title="Complete PostgreSQL rollout Oracle",
        task_status="in_progress",
        task_sort_order=1,
        task_due_at="2026-07-30T00:00:00Z",
        timestamp="2026-07-23T00:00:00Z",
    )


def _create_legacy_fixture(path: Path) -> str:
    schema = (
        BACKEND / "migrations" / "sqlite" / "0001_legacy_walking_skeleton.sql"
    ).read_text(encoding="utf-8")
    connection = sqlite3.connect(path)
    connection.executescript(schema)
    workspace_id = "ws_" + "l" * 22
    connection.execute(
        """
        INSERT INTO workspaces(
          workspace_id, recovery_hash, project_name, progress, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            workspace_id,
            "d" * 64,
            "Legacy import synthetic",
            31,
            "2026-07-20T00:00:00Z",
            "2026-07-21T00:00:00Z",
        ),
    )
    connection.execute(
        """
        INSERT INTO access_tokens(token_hash, workspace_id, created_at, expires_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            "e" * 64,
            workspace_id,
            "2026-07-20T00:00:00Z",
            "2026-07-20T01:00:00Z",
        ),
    )
    connection.execute(
        """
        INSERT INTO artifacts(
          artifact_id, workspace_id, object_name, original_name,
          reported_media_type, size_bytes, sha256, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "artifact_legacy_p51_synthetic",
            workspace_id,
            "legacy-p51-synthetic.blob",
            "legacy-p51.fixture",
            "application/octet-stream",
            23,
            "f" * 64,
            "2026-07-21T00:00:00Z",
        ),
    )
    connection.execute(
        """
        INSERT INTO audit_events(
          event_id, workspace_id, action, result_status, created_at
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            "walk_legacy_p51_synthetic",
            workspace_id,
            "workspace_created",
            "ok",
            "2026-07-20T00:00:00Z",
        ),
    )
    connection.commit()
    connection.close()
    return workspace_id


def _create_structured_sqlite_fixture(path: Path) -> str:
    legacy_schema = (
        BACKEND / "migrations" / "sqlite" / "0001_legacy_walking_skeleton.sql"
    ).read_text(encoding="utf-8")
    structured_schema = (
        BACKEND / "migrations" / "sqlite" / "0002_structured_data.sql"
    ).read_text(encoding="utf-8")
    connection = sqlite3.connect(path)
    connection.executescript(legacy_schema)
    workspace_id = "ws_" + "v" * 22
    timestamp = "2026-07-22T00:00:00Z"
    connection.execute(
        """
        INSERT INTO workspaces(
          workspace_id, recovery_hash, project_name, progress, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            workspace_id,
            "a" * 64,
            "Structured SQLite synthetic",
            54,
            timestamp,
            timestamp,
        ),
    )
    connection.execute(
        """
        INSERT INTO audit_events(
          event_id, workspace_id, action, result_status, created_at
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            "walk_structured_sqlite_p51",
            workspace_id,
            "workspace_created",
            "ok",
            timestamp,
        ),
    )
    connection.commit()
    connection.executescript(structured_schema)
    project_id = "project_" + workspace_id
    connection.execute(
        "UPDATE project_metrics SET score = 77 WHERE project_id = ?",
        (project_id,),
    )
    connection.execute(
        """
        INSERT INTO financial_records(
          financial_record_id, project_id, record_type, category, amount_minor,
          currency, effective_date, row_version, created_at, updated_at
        ) VALUES (?, ?, 'actual', 'structured SQLite synthetic', 9900, 'CNY',
                  '2026-07-22', 1, ?, ?)
        """,
        ("finance_structured_sqlite_p51", project_id, timestamp, timestamp),
    )
    connection.execute(
        """
        INSERT INTO workspace_tasks(
          task_id, project_id, title, status, sort_order, row_version,
          created_at, updated_at
        ) VALUES (?, ?, 'Structured SQLite migration fixture', 'done', 1, 1, ?, ?)
        """,
        ("task_structured_sqlite_p51", project_id, timestamp, timestamp),
    )
    connection.commit()
    connection.close()
    return workspace_id


def run_oracle(resources: OwnedResources, out_dir: Path) -> dict[str, Any]:
    app_a, url_a = resources.start_app("a")
    app_b, url_b = resources.start_app("b")

    # Both fresh processes race through the same migration chain.
    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(
            executor.map(
                lambda url: _json_request(url, "GET", f"{API_PREFIX}/status"),
                (url_a, url_b),
            )
        )
    for status, payload, _ in statuses:
        assert status == 200
        assert payload["healthy"] is True
        assert payload["schema_version"] == 3
        assert payload["structured_store"] == "postgresql-shared-service-adapter"

    created_status, created, created_headers = _json_request(
        url_a,
        "POST",
        f"{API_PREFIX}/workspaces",
        {"project_name": "S05 P5.1 synthetic rollout"},
    )
    assert created_status == 201
    assert "access_token" not in created
    token = _cookie_token(created_headers)
    recovery_code = str(created["recovery_code"])
    assert RECOVERY_RE.fullmatch(recovery_code)
    workspace_id = str(created["workspace"]["workspace_id"])

    update_status, updated, _ = _json_request(
        url_a,
        "PATCH",
        f"{API_PREFIX}/workspaces/{workspace_id}",
        {"project_name": "S05 P5.1 persisted synthetic", "progress": 67},
        token=token,
    )
    assert update_status == 200
    assert updated["progress"] == 67

    upload_status, upload_raw, _ = _request(
        url_a,
        "PUT",
        f"{API_PREFIX}/workspaces/{workspace_id}/artifact",
        payload=FIXTURE_BYTES,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-kmfa-synthetic",
            "X-KMFA-Filename": quote(FIXTURE_NAME, safe=""),
        },
    )
    assert upload_status == 200
    assert json.loads(upload_raw.decode("utf-8"))["artifact"]["sha256"] == FIXTURE_SHA256

    _configure_host_database(resources.host_dsn)
    connection = open_structured_store(Path("/tmp/kmfa-p51-unused.sqlite3"))
    try:
        service = StructuredDataService(connection)
        service.apply_acceptance_fixture(_acceptance_fixture(workspace_id))
        repository = service.repository
        snapshot_after_fixture = repository.workspace_snapshot(workspace_id)
        assert snapshot_after_fixture["project"]["score"] == 93

        def concurrent_task(index: int) -> None:
            worker = open_structured_store(Path("/tmp/kmfa-p51-unused.sqlite3"))
            try:
                with worker.transaction():
                    StructuredRepository(worker).put_task(
                        task_id=f"task_p51_concurrent_{index:02d}",
                        workspace_id=workspace_id,
                        title=f"Synthetic concurrent task {index}",
                        status="todo",
                        sort_order=index + 10,
                        due_at=None,
                        timestamp="2026-07-23T00:00:00Z",
                    )
            finally:
                worker.close()

        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(concurrent_task, range(20)))
        repository = StructuredRepository(connection)
        snapshot_before_rollout = repository.workspace_snapshot(workspace_id)
        hash_before_rollout = repository.workspace_snapshot_hash(workspace_id)
        business_hash_before_rollout = repository.workspace_business_state_hash(
            workspace_id
        )
        assert len(snapshot_before_rollout["tasks"]) == 21

        with pytest_raises(StructuredStoreIntegrityError):
            with connection.transaction():
                repository.set_score(
                    workspace_id=workspace_id,
                    score=99,
                    updated_at="2026-07-23T01:00:00Z",
                )
                connection.execute(
                    """
                    INSERT INTO financial_records(
                      financial_record_id, project_id, record_type, category,
                      amount_minor, currency, effective_date, row_version,
                      created_at, updated_at
                    ) VALUES (?, ?, 'actual', 'rollback canary', -1, 'CNY',
                              '2026-07-23', 1, ?, ?)
                    """,
                    (
                        "finance_p51_invalid",
                        "project_" + workspace_id,
                        "2026-07-23T01:00:00Z",
                        "2026-07-23T01:00:00Z",
                    ),
                )
        assert repository.workspace_snapshot_hash(workspace_id) == hash_before_rollout
    finally:
        connection.close()

    # Existing session and file bytes work from the second app node.
    get_status, from_b, _ = _json_request(
        url_b,
        "GET",
        f"{API_PREFIX}/workspaces/{workspace_id}",
        token=token,
    )
    assert get_status == 200 and from_b["progress"] == 67
    download_status, downloaded, download_headers = _request(
        url_b,
        "POST",
        f"{API_PREFIX}/workspaces/{workspace_id}/artifact/download",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert download_status == 200
    assert downloaded == FIXTURE_BYTES
    assert download_headers["X-KMFA-Artifact-SHA256"] == FIXTURE_SHA256

    # Remove one node while the other serves, then introduce its replacement.
    resources.remove_app(app_a)
    app_c, url_c = resources.start_app("c")
    get_status, from_c, _ = _json_request(
        url_c,
        "GET",
        f"{API_PREFIX}/workspaces/{workspace_id}",
        token=token,
    )
    assert get_status == 200 and from_c["project_name"].endswith("synthetic")

    # A fresh cookie jar represents browser data clearing. Recovery is driven
    # only by the externally held capability and server-side PostgreSQL state.
    empty_jar = http.cookiejar.CookieJar()
    fresh_browser = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(empty_jar)
    )
    recovered_status, recovered, recovered_headers = _json_request(
        url_c,
        "POST",
        f"{API_PREFIX}/recoveries",
        {"recovery_code": recovery_code},
        opener=fresh_browser,
    )
    assert recovered_status == 200
    recovered_token = _cookie_token(recovered_headers)
    assert recovered_token != token
    assert recovered["workspace"]["workspace_id"] == workspace_id
    assert recovered["workspace"]["progress"] == 67

    # Replace the database container while retaining only its named data
    # volume, then verify both application nodes reconnect to identical state.
    resources.replace_postgresql()
    for base_url in (url_b, url_c):
        status, payload, _ = _json_request(
            base_url,
            "GET",
            f"{API_PREFIX}/workspaces/{workspace_id}",
            token=recovered_token,
        )
        assert status == 200 and payload["progress"] == 67

    _configure_host_database(resources.host_dsn)
    reopened = open_structured_store(Path("/tmp/kmfa-p51-unused.sqlite3"))
    try:
        repository = StructuredRepository(reopened)
        hash_after_rollout = repository.workspace_snapshot_hash(workspace_id)
        business_hash_after_rollout = repository.workspace_business_state_hash(
            workspace_id
        )
        snapshot_after_rollout = repository.workspace_snapshot(workspace_id)
    finally:
        reopened.close()
    assert business_hash_after_rollout == business_hash_before_rollout
    assert snapshot_after_rollout["audit_event_count"] > snapshot_before_rollout[
        "audit_event_count"
    ]

    # The v1.5 read-only migration path is additive, idempotent and preserves
    # its source byte-for-byte.
    migration_fixtures = resources.state_dir / "migration-fixtures"
    migration_fixtures.mkdir(mode=0o700, parents=True, exist_ok=True)
    legacy_path = migration_fixtures / "synthetic-legacy-source.sqlite3"
    legacy_workspace_id = _create_legacy_fixture(legacy_path)
    legacy_sha_before = hashlib.sha256(legacy_path.read_bytes()).hexdigest()
    first_import = import_legacy_sqlite(legacy_path)
    second_import = import_legacy_sqlite(legacy_path)
    legacy_sha_after = hashlib.sha256(legacy_path.read_bytes()).hexdigest()
    assert legacy_sha_before == legacy_sha_after
    assert first_import == second_import
    imported = open_structured_store(Path("/tmp/kmfa-p51-unused.sqlite3"))
    try:
        imported_projection = StructuredRepository(imported).workspace_projection(
            legacy_workspace_id
        )
        imported_count = imported.execute(
            """
            SELECT COUNT(*) AS count_value
            FROM workspaces
            WHERE workspace_id = ?
            """,
            (legacy_workspace_id,),
        ).fetchone()["count_value"]
    finally:
        imported.close()
    assert imported_count == 1
    assert imported_projection["progress"] == 31

    structured_source = (
        migration_fixtures / "synthetic-structured-source.sqlite3"
    )
    structured_workspace_id = _create_structured_sqlite_fixture(structured_source)
    structured_source_sha_before = hashlib.sha256(
        structured_source.read_bytes()
    ).hexdigest()
    structured_first_import = import_legacy_sqlite(structured_source)
    structured_second_import = import_legacy_sqlite(structured_source)
    structured_source_sha_after = hashlib.sha256(
        structured_source.read_bytes()
    ).hexdigest()
    assert structured_first_import == structured_second_import
    assert structured_source_sha_before == structured_source_sha_after
    structured_target = open_structured_store(
        Path("/tmp/kmfa-p51-unused.sqlite3")
    )
    try:
        structured_snapshot = StructuredRepository(
            structured_target
        ).workspace_snapshot(structured_workspace_id)
    finally:
        structured_target.close()
    assert structured_snapshot["project"]["score"] == 77
    assert len(structured_snapshot["financial_records"]) == 1
    assert len(structured_snapshot["tasks"]) == 1

    capabilities = (token, recovered_token, recovery_code)
    logs = resources.logs()
    assert not any(capability in logs for capability in capabilities)
    assert resources.postgres_password not in logs

    app_image_id = _run(
        "docker", "image", "inspect", resources.image, "--format", "{{.Id}}"
    ).stdout.strip()
    postgres_image_id = _run(
        "docker", "image", "inspect", POSTGRES_IMAGE, "--format", "{{.Id}}"
    ).stdout.strip()
    return {
        "schema_version": "kmfa.s05.p51.structured-database-oracle.v1",
        "status": "PASS",
        "completed_at": _timestamp(),
        "synthetic_only": True,
        "application_image_id": app_image_id,
        "postgres_image": POSTGRES_IMAGE,
        "postgres_image_id": postgres_image_id,
        "structured_schema_version": 3,
        "structured_business_state_sha256": business_hash_after_rollout,
        "pre_rollout_full_snapshot_sha256": hash_before_rollout,
        "post_rollout_full_snapshot_sha256": hash_after_rollout,
        "artifact_sha256": FIXTURE_SHA256,
        "legacy_source_sha256": legacy_sha_after,
        "structured_sqlite_source_sha256": structured_source_sha_after,
        "legacy_source_preserved": True,
        "legacy_import_fingerprint": first_import["source_fixture_fingerprint"],
        "row_counts": {
            "financial_records": len(snapshot_after_rollout["financial_records"]),
            "artifact_versions": len(snapshot_after_rollout["artifact_versions"]),
            "tasks": len(snapshot_after_rollout["tasks"]),
            "audit_events_before_rollout": snapshot_before_rollout[
                "audit_event_count"
            ],
            "audit_events_after_rollout": snapshot_after_rollout[
                "audit_event_count"
            ],
        },
        "checks": {
            "concurrent_migration_startup": "PASS",
            "transaction_constraint_atomicity": "PASS",
            "concurrent_writers_no_loss_or_duplicate": "PASS",
            "two_application_nodes_shared_database": "PASS",
            "rolling_application_node_replacement": "PASS",
            "browser_state_cleared_recovery": "PASS",
            "database_container_replacement_same_volume": "PASS",
            "structured_business_state_identical_after_replacement": "PASS",
            "append_only_audit_survived_replacement": "PASS",
            "arbitrary_file_download_hash_identical": "PASS",
            "legacy_sqlite_import_idempotent": "PASS",
            "legacy_sqlite_source_byte_preserved": "PASS",
            "structured_sqlite_v2_rows_imported": "PASS",
            "capability_and_dsn_log_scan": "PASS",
        },
    }


class pytest_raises:
    """Tiny local context manager so the Docker Oracle has no pytest runtime."""

    def __init__(self, expected: type[BaseException]) -> None:
        self.expected = expected

    def __enter__(self) -> None:
        return None

    def __exit__(self, error_type, error, traceback) -> bool:
        if error_type is None:
            raise AssertionError(f"{self.expected.__name__} was not raised")
        return bool(issubclass(error_type, self.expected))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--prefix", default="kmfa-p51-e2e")
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
    resources = OwnedResources(
        arguments.prefix,
        arguments.image,
        state_dir,
    )
    capabilities: tuple[str, ...] = ()
    try:
        resources.initialize()
        report = run_oracle(resources, out_dir)
        encoded = json.dumps(
            report,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        assert ACCESS_RE.search(encoded) is None
        assert RECOVERY_RE.search(encoded) is None
        assert resources.postgres_password not in encoded
        (out_dir / "structured-database-oracle.json").write_text(
            encoded + "\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "structured_schema_version": report[
                        "structured_schema_version"
                    ],
                    "checks": len(report["checks"]),
                },
                sort_keys=True,
            )
        )
        return 0
    except Exception:
        sensitive_values = (*capabilities, resources.postgres_password)
        logs = _redact(resources.logs(), sensitive_values)
        if logs:
            print(logs[-8000:], file=sys.stderr)
        print(_redact(traceback.format_exc(), sensitive_values), file=sys.stderr)
        return 1
    finally:
        resources.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
