"""Durable, bounded report-export jobs for S07/P7.3.

The web process records an explicit command and returns.  A separately invoked
worker claims at most the configured number of jobs, renders one bounded
artifact at a time, and atomically commits the job result with the existing
append-only export/audit records.  GET and HEAD paths only read this state.

Raw idempotency keys and report bodies are never stored in job metadata or
events.  Generated artifacts live under the private application-state volume;
expiration applies only to these reproducible export artifacts, never to the
source report, user uploads, recovery material, or workspace state.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import sqlite3
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

EXPORT_JOBS_ENABLED_ENV = "KMFA_EXPORT_JOBS_ENABLED"
TRUE_VALUES = frozenset({"1", "true", "yes", "on"})

EXPORT_FORMATS = frozenset({"html", "csv", "pdf"})
EXPORT_JOB_STATES = frozenset(
    {
        "queued",
        "running",
        "retry",
        "succeeded",
        "failed",
        "cancelled",
        "expired",
    }
)
ACTIVE_EXPORT_JOB_STATES = frozenset({"queued", "running", "retry"})

MAX_ACTIVE_EXPORT_JOBS = 64
MAX_RUNNING_EXPORT_JOBS = 2
MAX_EXPORT_JOB_RECORDS = 10_000
MAX_EXPORT_ATTEMPTS = 3
MAX_ESTIMATED_COST_UNITS = 64
MAX_ACTIVE_COST_UNITS = 256
MAX_EXPORT_SOURCE_BYTES = 2 * 1024 * 1024
MAX_EXPORT_ARTIFACT_BYTES = 16 * 1024 * 1024
EXPORT_JOB_LEASE_SECONDS = 60
EXPORT_JOB_RETRY_DELAY_SECONDS = 5
EXPORT_ARTIFACT_TTL_SECONDS = 24 * 60 * 60
EXPORT_STREAM_CHUNK_BYTES = 64 * 1024

EXPORT_JOB_SCHEMA_VERSION = 1
JOB_ID_RE = re.compile(r"^export_[A-Za-z0-9_-]{24}$")
IDEMPOTENCY_KEY_RE = re.compile(r"^[A-Za-z0-9._~-]{16,128}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ERROR_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{2,80}$")
ARTIFACT_NAME_RE = re.compile(
    r"^export_[A-Za-z0-9_-]{24}\.(?:html|csv|pdf)$"
)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS export_job_schema (
  version INTEGER PRIMARY KEY,
  sha256 TEXT NOT NULL,
  applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS export_jobs (
  job_id TEXT PRIMARY KEY,
  idempotency_key_hash TEXT NOT NULL UNIQUE,
  request_fingerprint TEXT NOT NULL,
  source_fingerprint TEXT NOT NULL,
  report_no INTEGER NOT NULL CHECK(report_no >= 1),
  artifact_format TEXT NOT NULL
    CHECK(artifact_format IN ('html', 'csv', 'pdf')),
  state TEXT NOT NULL
    CHECK(state IN (
      'queued', 'running', 'retry', 'succeeded',
      'failed', 'cancelled', 'expired'
    )),
  attempt_count INTEGER NOT NULL DEFAULT 0
    CHECK(attempt_count >= 0 AND attempt_count <= 3),
  estimated_cost_units INTEGER NOT NULL
    CHECK(estimated_cost_units >= 1 AND estimated_cost_units <= 64),
  actual_cost_units INTEGER,
  available_at TEXT NOT NULL,
  lease_until TEXT,
  claim_id TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  completed_at TEXT,
  expires_at TEXT,
  artifact_name TEXT,
  artifact_sha256 TEXT,
  artifact_size_bytes INTEGER,
  artifact_media_type TEXT,
  report_grade TEXT CHECK(report_grade IS NULL OR length(report_grade) <= 64),
  quality_grade TEXT CHECK(quality_grade IS NULL OR length(quality_grade) <= 64),
  delivery_allowed INTEGER
    CHECK(delivery_allowed IS NULL OR delivery_allowed IN (0, 1)),
  watermark_applied INTEGER
    CHECK(watermark_applied IS NULL OR watermark_applied IN (0, 1)),
  error_code TEXT,
  row_version INTEGER NOT NULL DEFAULT 1 CHECK(row_version >= 1),
  CHECK(
    (state = 'running' AND lease_until IS NOT NULL AND claim_id IS NOT NULL)
    OR state != 'running'
  ),
  CHECK(
    artifact_name IS NULL
    OR state IN ('succeeded', 'expired')
  )
);

CREATE INDEX IF NOT EXISTS export_jobs_claim_idx
ON export_jobs(state, available_at, created_at);

CREATE INDEX IF NOT EXISTS export_jobs_expiry_idx
ON export_jobs(state, expires_at);

CREATE TABLE IF NOT EXISTS export_job_events (
  sequence INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL UNIQUE,
  job_id TEXT NOT NULL,
  event_kind TEXT NOT NULL,
  from_state TEXT,
  to_state TEXT NOT NULL,
  attempt_count INTEGER NOT NULL,
  cost_units INTEGER,
  reason_code TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(job_id) REFERENCES export_jobs(job_id)
);

CREATE TRIGGER IF NOT EXISTS export_job_events_no_update
BEFORE UPDATE ON export_job_events
BEGIN
  SELECT RAISE(ABORT, 'export_job_events is append-only');
END;

CREATE TRIGGER IF NOT EXISTS export_job_events_no_delete
BEFORE DELETE ON export_job_events
BEGIN
  SELECT RAISE(ABORT, 'export_job_events is append-only');
END;
""".strip()
_SCHEMA_SHA256 = hashlib.sha256(_SCHEMA_SQL.encode("utf-8")).hexdigest()


class ExportJobError(RuntimeError):
    """Static, non-sensitive export job failure."""


class ExportJobConflict(ExportJobError):
    """An idempotency key or state transition conflicts."""


class ExportJobCapacity(ExportJobError):
    """The explicit queue or cost budget is exhausted."""


class ExportJobNotFound(ExportJobError):
    """The opaque job identifier does not resolve."""


class ExportJobLeaseLost(ExportJobError):
    """A worker no longer owns the claimed job."""


@dataclass(frozen=True)
class ClaimedExportJob:
    job_id: str
    claim_id: str
    report_no: int
    artifact_format: str
    source_fingerprint: str
    attempt_count: int
    estimated_cost_units: int
    lease_until: str


@dataclass(frozen=True)
class StoredExportArtifact:
    name: str
    path: Path
    sha256: str
    size_bytes: int


def export_jobs_enabled() -> bool:
    """Only explicit true values enable new job creation and worker claims."""

    return (
        os.environ.get(EXPORT_JOBS_ENABLED_ENV, "0").strip().lower()
        in TRUE_VALUES
    )


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ExportJobError("export_job_clock_invalid")
    return (
        value.astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ExportJobError("export_job_timestamp_invalid") from exc
    if parsed.tzinfo is None:
        raise ExportJobError("export_job_timestamp_invalid")
    return parsed.astimezone(timezone.utc)


def request_fingerprint(
    *,
    report_no: int,
    artifact_format: str,
    source_fingerprint: str,
) -> str:
    payload = json.dumps(
        {
            "artifact_format": artifact_format,
            "report_no": report_no,
            "source_fingerprint": source_fingerprint,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def estimated_cost_units(
    *,
    source_bytes: int,
    artifact_format: str,
) -> int:
    if source_bytes < 0 or source_bytes > MAX_EXPORT_SOURCE_BYTES:
        raise ExportJobCapacity("export_source_bytes_exceeded")
    factors = {"html": 1, "csv": 1, "pdf": 4}
    if artifact_format not in factors:
        raise ExportJobError("export_format_invalid")
    blocks = max(1, (source_bytes + 65_535) // 65_536)
    units = blocks * factors[artifact_format]
    if units > MAX_ESTIMATED_COST_UNITS:
        raise ExportJobCapacity("export_cost_budget_exceeded")
    return units


def actual_cost_units(
    *,
    estimated_units: int,
    artifact_size_bytes: int,
) -> int:
    if (
        estimated_units < 1
        or artifact_size_bytes < 0
        or artifact_size_bytes > MAX_EXPORT_ARTIFACT_BYTES
    ):
        raise ExportJobCapacity("export_artifact_bytes_exceeded")
    output_blocks = max(
        1,
        (artifact_size_bytes + 65_535) // 65_536,
    )
    return estimated_units + output_blocks


def _idempotency_hash(value: str) -> str:
    if IDEMPOTENCY_KEY_RE.fullmatch(value) is None:
        raise ExportJobError("invalid_idempotency_key")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _new_job_id() -> str:
    value = f"export_{secrets.token_urlsafe(18)}"
    assert JOB_ID_RE.fullmatch(value)
    return value


def _new_claim_id() -> str:
    return f"claim_{secrets.token_urlsafe(18)}"


def _new_event_id() -> str:
    return f"export_event_{secrets.token_urlsafe(18)}"


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


class ExportJobRepository:
    """SQLite-backed command queue sharing the durable app-state database."""

    def __init__(
        self,
        db_path: Path,
        artifacts_root: Path,
        *,
        initialize: bool = True,
    ) -> None:
        self.db_path = db_path
        self.artifacts_root = artifacts_root
        if initialize:
            self._initialize()

    def _connect(
        self,
        *,
        read_only: bool = False,
    ) -> sqlite3.Connection:
        if read_only:
            if not self.db_path.is_file():
                raise ExportJobNotFound("export_job_not_found")
            connection = sqlite3.connect(
                f"{self.db_path.resolve().as_uri()}?mode=ro",
                uri=True,
                isolation_level=None,
                timeout=5,
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA busy_timeout=5000")
            connection.execute("PRAGMA query_only=ON")
            return connection
        self.db_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.db_path.parent.chmod(0o700)
        connection = sqlite3.connect(
            str(self.db_path),
            isolation_level=None,
            timeout=5,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        if self.db_path.exists():
            self.db_path.chmod(0o600)
        return connection

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            statement = ""
            for line in _SCHEMA_SQL.splitlines(keepends=True):
                statement += line
                if sqlite3.complete_statement(statement):
                    cleaned = statement.strip()
                    if cleaned:
                        connection.execute(cleaned)
                    statement = ""
            if statement.strip():
                raise ExportJobError("export_job_schema_invalid")
            rows = connection.execute(
                """
                SELECT version, sha256
                FROM export_job_schema
                ORDER BY version
                """
            ).fetchall()
            if not rows:
                connection.execute(
                    """
                    INSERT INTO export_job_schema(version, sha256, applied_at)
                    VALUES (?, ?, ?)
                    """,
                    (
                        EXPORT_JOB_SCHEMA_VERSION,
                        _SCHEMA_SHA256,
                        timestamp(utc_now()),
                    ),
                )
            elif (
                len(rows) != 1
                or int(rows[0]["version"]) != EXPORT_JOB_SCHEMA_VERSION
                or str(rows[0]["sha256"]) != _SCHEMA_SHA256
            ):
                raise ExportJobError("export_job_schema_mismatch")
            connection.execute("COMMIT")
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.execute("COMMIT")
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    @staticmethod
    def _append_event(
        connection: sqlite3.Connection,
        *,
        job_id: str,
        event_kind: str,
        from_state: str | None,
        to_state: str,
        attempt_count: int,
        now: datetime,
        cost_units: int | None = None,
        reason_code: str | None = None,
    ) -> None:
        if (
            to_state not in EXPORT_JOB_STATES
            or from_state not in EXPORT_JOB_STATES | {None}
            or (
                reason_code is not None
                and ERROR_CODE_RE.fullmatch(reason_code) is None
            )
        ):
            raise ExportJobError("export_job_event_invalid")
        connection.execute(
            """
            INSERT INTO export_job_events(
              event_id, job_id, event_kind, from_state, to_state,
              attempt_count, cost_units, reason_code, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _new_event_id(),
                job_id,
                event_kind,
                from_state,
                to_state,
                attempt_count,
                cost_units,
                reason_code,
                timestamp(now),
            ),
        )

    @staticmethod
    def _row_for_job(
        connection: sqlite3.Connection,
        job_id: str,
    ) -> sqlite3.Row:
        if JOB_ID_RE.fullmatch(job_id) is None:
            raise ExportJobNotFound("export_job_not_found")
        row = connection.execute(
            "SELECT * FROM export_jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            raise ExportJobNotFound("export_job_not_found")
        return row

    def create(
        self,
        *,
        idempotency_key: str,
        report_no: int,
        artifact_format: str,
        source_fingerprint: str,
        estimated_units: int,
        now: datetime,
    ) -> tuple[dict[str, Any], bool]:
        if (
            type(report_no) is not int
            or report_no < 1
            or artifact_format not in EXPORT_FORMATS
            or SHA256_RE.fullmatch(source_fingerprint) is None
            or not 1 <= estimated_units <= MAX_ESTIMATED_COST_UNITS
        ):
            raise ExportJobError("export_job_request_invalid")
        key_hash = _idempotency_hash(idempotency_key)
        fingerprint = request_fingerprint(
            report_no=report_no,
            artifact_format=artifact_format,
            source_fingerprint=source_fingerprint,
        )
        created_at = timestamp(now)
        with self._transaction() as connection:
            existing = connection.execute(
                """
                SELECT * FROM export_jobs
                WHERE idempotency_key_hash = ?
                """,
                (key_hash,),
            ).fetchone()
            if existing is not None:
                if str(existing["request_fingerprint"]) != fingerprint:
                    raise ExportJobConflict("idempotency_key_conflict")
                return dict(existing), False

            total = int(
                connection.execute(
                    "SELECT COUNT(*) AS count_value FROM export_jobs"
                ).fetchone()["count_value"]
            )
            active = connection.execute(
                """
                SELECT COUNT(*) AS count_value,
                       COALESCE(SUM(estimated_cost_units), 0) AS cost_value
                FROM export_jobs
                WHERE state IN ('queued', 'running', 'retry')
                """
            ).fetchone()
            if (
                total >= MAX_EXPORT_JOB_RECORDS
                or int(active["count_value"]) >= MAX_ACTIVE_EXPORT_JOBS
            ):
                raise ExportJobCapacity("export_job_capacity_reached")
            if (
                int(active["cost_value"]) + estimated_units
                > MAX_ACTIVE_COST_UNITS
            ):
                raise ExportJobCapacity("export_cost_capacity_reached")

            job_id = _new_job_id()
            connection.execute(
                """
                INSERT INTO export_jobs(
                  job_id, idempotency_key_hash, request_fingerprint,
                  source_fingerprint, report_no, artifact_format, state,
                  attempt_count, estimated_cost_units, available_at,
                  created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'queued', 0, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    key_hash,
                    fingerprint,
                    source_fingerprint,
                    report_no,
                    artifact_format,
                    estimated_units,
                    created_at,
                    created_at,
                    created_at,
                ),
            )
            self._append_event(
                connection,
                job_id=job_id,
                event_kind="created",
                from_state=None,
                to_state="queued",
                attempt_count=0,
                cost_units=estimated_units,
                now=now,
            )
            return dict(
                self._row_for_job(connection, job_id)
            ), True

    def _recover_stale_claims(
        self,
        connection: sqlite3.Connection,
        *,
        now: datetime,
    ) -> None:
        now_text = timestamp(now)
        rows = connection.execute(
            """
            SELECT * FROM export_jobs
            WHERE state = 'running' AND lease_until <= ?
            ORDER BY created_at, job_id
            """,
            (now_text,),
        ).fetchall()
        for row in rows:
            attempts = int(row["attempt_count"])
            next_state = (
                "failed"
                if attempts >= MAX_EXPORT_ATTEMPTS
                else "retry"
            )
            connection.execute(
                """
                UPDATE export_jobs
                SET state = ?, available_at = ?, lease_until = NULL,
                    claim_id = NULL, error_code = 'export_job_timeout',
                    updated_at = ?, row_version = row_version + 1
                WHERE job_id = ? AND state = 'running'
                """,
                (
                    next_state,
                    now_text,
                    now_text,
                    str(row["job_id"]),
                ),
            )
            self._append_event(
                connection,
                job_id=str(row["job_id"]),
                event_kind=(
                    "attempts_exhausted"
                    if next_state == "failed"
                    else "lease_recovered"
                ),
                from_state="running",
                to_state=next_state,
                attempt_count=attempts,
                now=now,
                reason_code="export_job_timeout",
            )
            _safe_unlink(
                self.artifacts_root
                / (
                    f"{row['job_id']}."
                    f"{row['artifact_format']}"
                )
            )

    def claim_next(
        self,
        *,
        now: datetime,
        job_id: str | None = None,
    ) -> ClaimedExportJob | None:
        with self._transaction() as connection:
            self._recover_stale_claims(connection, now=now)
            running = int(
                connection.execute(
                    """
                    SELECT COUNT(*) AS count_value
                    FROM export_jobs
                    WHERE state = 'running' AND lease_until > ?
                    """,
                    (timestamp(now),),
                ).fetchone()["count_value"]
            )
            if running >= MAX_RUNNING_EXPORT_JOBS:
                return None

            parameters: list[Any] = [timestamp(now)]
            job_filter = ""
            if job_id is not None:
                if JOB_ID_RE.fullmatch(job_id) is None:
                    raise ExportJobNotFound("export_job_not_found")
                job_filter = "AND job_id = ?"
                parameters.append(job_id)
            row = connection.execute(
                f"""
                SELECT * FROM export_jobs
                WHERE state IN ('queued', 'retry')
                  AND available_at <= ?
                  {job_filter}
                ORDER BY created_at, job_id
                LIMIT 1
                """,
                tuple(parameters),
            ).fetchone()
            if row is None:
                return None

            claim_id = _new_claim_id()
            attempts = int(row["attempt_count"]) + 1
            lease_until = now + timedelta(
                seconds=EXPORT_JOB_LEASE_SECONDS
            )
            connection.execute(
                """
                UPDATE export_jobs
                SET state = 'running', attempt_count = ?,
                    lease_until = ?, claim_id = ?, updated_at = ?,
                    error_code = NULL, row_version = row_version + 1
                WHERE job_id = ? AND state IN ('queued', 'retry')
                """,
                (
                    attempts,
                    timestamp(lease_until),
                    claim_id,
                    timestamp(now),
                    str(row["job_id"]),
                ),
            )
            self._append_event(
                connection,
                job_id=str(row["job_id"]),
                event_kind="claimed",
                from_state=str(row["state"]),
                to_state="running",
                attempt_count=attempts,
                cost_units=int(row["estimated_cost_units"]),
                now=now,
            )
            return ClaimedExportJob(
                job_id=str(row["job_id"]),
                claim_id=claim_id,
                report_no=int(row["report_no"]),
                artifact_format=str(row["artifact_format"]),
                source_fingerprint=str(row["source_fingerprint"]),
                attempt_count=attempts,
                estimated_cost_units=int(
                    row["estimated_cost_units"]
                ),
                lease_until=timestamp(lease_until),
            )

    def fail(
        self,
        claim: ClaimedExportJob,
        *,
        error_code: str,
        retryable: bool,
        now: datetime,
    ) -> dict[str, Any]:
        if ERROR_CODE_RE.fullmatch(error_code) is None:
            raise ExportJobError("export_job_error_code_invalid")
        with self._transaction() as connection:
            row = self._row_for_job(connection, claim.job_id)
            if (
                str(row["state"]) != "running"
                or str(row["claim_id"]) != claim.claim_id
            ):
                raise ExportJobLeaseLost("export_job_lease_lost")
            attempts = int(row["attempt_count"])
            can_retry = retryable and attempts < MAX_EXPORT_ATTEMPTS
            next_state = "retry" if can_retry else "failed"
            available_at = (
                now
                + timedelta(seconds=EXPORT_JOB_RETRY_DELAY_SECONDS)
                if can_retry
                else now
            )
            connection.execute(
                """
                UPDATE export_jobs
                SET state = ?, available_at = ?, lease_until = NULL,
                    claim_id = NULL, error_code = ?, updated_at = ?,
                    row_version = row_version + 1
                WHERE job_id = ? AND state = 'running' AND claim_id = ?
                """,
                (
                    next_state,
                    timestamp(available_at),
                    error_code,
                    timestamp(now),
                    claim.job_id,
                    claim.claim_id,
                ),
            )
            self._append_event(
                connection,
                job_id=claim.job_id,
                event_kind=(
                    "retry_scheduled"
                    if can_retry
                    else "failed"
                ),
                from_state="running",
                to_state=next_state,
                attempt_count=attempts,
                now=now,
                reason_code=error_code,
            )
            return dict(
                self._row_for_job(connection, claim.job_id)
            )

    def complete(
        self,
        claim: ClaimedExportJob,
        *,
        artifact: StoredExportArtifact,
        media_type: str,
        actual_units: int,
        report_grade: str,
        quality_grade: str,
        delivery_allowed: bool,
        watermark_applied: bool,
        export_record: dict[str, Any],
        audit_event: dict[str, Any],
        now: datetime,
    ) -> dict[str, Any]:
        if (
            ARTIFACT_NAME_RE.fullmatch(artifact.name) is None
            or SHA256_RE.fullmatch(artifact.sha256) is None
            or artifact.size_bytes < 0
            or artifact.size_bytes > MAX_EXPORT_ARTIFACT_BYTES
            or actual_units < 1
            or not 1 <= len(report_grade) <= 64
            or not 1 <= len(quality_grade) <= 64
            or type(delivery_allowed) is not bool
            or type(watermark_applied) is not bool
        ):
            raise ExportJobError("export_artifact_metadata_invalid")
        with self._transaction() as connection:
            row = self._row_for_job(connection, claim.job_id)
            if (
                str(row["state"]) != "running"
                or str(row["claim_id"]) != claim.claim_id
            ):
                raise ExportJobLeaseLost("export_job_lease_lost")
            if parse_timestamp(str(row["lease_until"])) <= now:
                raise ExportJobLeaseLost("export_job_lease_expired")
            completed_at = timestamp(now)
            expires_at = timestamp(
                now + timedelta(seconds=EXPORT_ARTIFACT_TTL_SECONDS)
            )
            connection.execute(
                """
                UPDATE export_jobs
                SET state = 'succeeded', actual_cost_units = ?,
                    lease_until = NULL, claim_id = NULL,
                    completed_at = ?, expires_at = ?,
                    artifact_name = ?, artifact_sha256 = ?,
                    artifact_size_bytes = ?, artifact_media_type = ?,
                    report_grade = ?, quality_grade = ?,
                    delivery_allowed = ?, watermark_applied = ?,
                    error_code = NULL, updated_at = ?,
                    row_version = row_version + 1
                WHERE job_id = ? AND state = 'running' AND claim_id = ?
                """,
                (
                    actual_units,
                    completed_at,
                    expires_at,
                    artifact.name,
                    artifact.sha256,
                    artifact.size_bytes,
                    media_type,
                    report_grade,
                    quality_grade,
                    int(delivery_allowed),
                    int(watermark_applied),
                    completed_at,
                    claim.job_id,
                    claim.claim_id,
                ),
            )
            connection.execute(
                "INSERT INTO export_records(payload) VALUES (?)",
                (
                    json.dumps(
                        export_record,
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                ),
            )
            connection.execute(
                "INSERT INTO audit_events(payload) VALUES (?)",
                (
                    json.dumps(
                        audit_event,
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                ),
            )
            self._append_event(
                connection,
                job_id=claim.job_id,
                event_kind="succeeded",
                from_state="running",
                to_state="succeeded",
                attempt_count=int(row["attempt_count"]),
                cost_units=actual_units,
                now=now,
            )
            return dict(
                self._row_for_job(connection, claim.job_id)
            )

    def cancel(
        self,
        job_id: str,
        *,
        now: datetime,
    ) -> dict[str, Any]:
        with self._transaction() as connection:
            row = self._row_for_job(connection, job_id)
            state = str(row["state"])
            if state == "cancelled":
                result = dict(row)
            else:
                if state not in {"queued", "retry", "running"}:
                    raise ExportJobConflict("export_job_not_cancellable")
                connection.execute(
                    """
                    UPDATE export_jobs
                    SET state = 'cancelled', lease_until = NULL,
                        claim_id = NULL, error_code = 'export_job_cancelled',
                        updated_at = ?, completed_at = ?,
                        row_version = row_version + 1
                    WHERE job_id = ?
                    """,
                    (timestamp(now), timestamp(now), job_id),
                )
                self._append_event(
                    connection,
                    job_id=job_id,
                    event_kind="cancelled",
                    from_state=state,
                    to_state="cancelled",
                    attempt_count=int(row["attempt_count"]),
                    now=now,
                    reason_code="export_job_cancelled",
                )
                result = dict(
                    self._row_for_job(connection, job_id)
                )
            artifact_name = (
                f"{job_id}.{row['artifact_format']}"
            )
        if ARTIFACT_NAME_RE.fullmatch(artifact_name):
            _safe_unlink(self.artifacts_root / artifact_name)
        return result

    def get(self, job_id: str) -> dict[str, Any]:
        connection = self._connect(read_only=True)
        try:
            try:
                return dict(self._row_for_job(connection, job_id))
            except sqlite3.OperationalError as exc:
                raise ExportJobNotFound(
                    "export_job_not_found"
                ) from exc
        finally:
            connection.close()

    def events(self, job_id: str) -> list[dict[str, Any]]:
        connection = self._connect(read_only=True)
        try:
            self._row_for_job(connection, job_id)
            return [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT event_kind, from_state, to_state,
                           attempt_count, cost_units, reason_code,
                           created_at
                    FROM export_job_events
                    WHERE job_id = ?
                    ORDER BY sequence
                    """,
                    (job_id,),
                ).fetchall()
            ]
        finally:
            connection.close()

    def payload(
        self,
        job_id: str,
        *,
        now: datetime,
    ) -> dict[str, Any]:
        row = self.get(job_id)
        state = str(row["state"])
        effective_state = state
        expires_at = (
            str(row["expires_at"])
            if row["expires_at"] is not None
            else None
        )
        if (
            state == "succeeded"
            and expires_at is not None
            and parse_timestamp(expires_at) <= now
        ):
            effective_state = "expired"
        artifact = None
        if effective_state == "succeeded":
            artifact = {
                "filename": str(row["artifact_name"]),
                "media_type": str(row["artifact_media_type"]),
                "size_bytes": int(row["artifact_size_bytes"]),
                "sha256": f"sha256:{row['artifact_sha256']}",
                "expires_at": expires_at,
                "download_url": (
                    f"/api/exports/jobs/{job_id}/artifact"
                ),
                "report_grade": str(row["report_grade"]),
                "quality_grade": str(row["quality_grade"]),
                "delivery_allowed": bool(row["delivery_allowed"]),
                "watermark_applied": bool(row["watermark_applied"]),
            }
        return {
            "job_id": job_id,
            "state": effective_state,
            "report_no": int(row["report_no"]),
            "format": str(row["artifact_format"]),
            "attempt_count": int(row["attempt_count"]),
            "max_attempts": MAX_EXPORT_ATTEMPTS,
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
            "completed_at": (
                str(row["completed_at"])
                if row["completed_at"] is not None
                else None
            ),
            "error_code": (
                str(row["error_code"])
                if row["error_code"] is not None
                else None
            ),
            "cost": {
                "unit": "bounded-render-unit-v1",
                "estimated": int(row["estimated_cost_units"]),
                "actual": (
                    int(row["actual_cost_units"])
                    if row["actual_cost_units"] is not None
                    else None
                ),
            },
            "artifact": artifact,
            "events": self.events(job_id),
        }

    def metrics(self, *, now: datetime) -> dict[str, Any]:
        counts = {state: 0 for state in sorted(EXPORT_JOB_STATES)}
        if not self.db_path.is_file():
            return self._metrics_payload(
                counts=counts,
                estimated_total=0,
                actual_total=0,
                now=now,
            )
        connection = self._connect(read_only=True)
        try:
            try:
                rows = connection.execute(
                    """
                    SELECT state, COUNT(*) AS count_value,
                           COALESCE(SUM(estimated_cost_units), 0) AS estimated,
                           COALESCE(SUM(actual_cost_units), 0) AS actual
                    FROM export_jobs
                    GROUP BY state
                    """
                ).fetchall()
            except sqlite3.OperationalError:
                rows = []
        finally:
            connection.close()
        estimated_total = 0
        actual_total = 0
        for row in rows:
            counts[str(row["state"])] = int(row["count_value"])
            estimated_total += int(row["estimated"])
            actual_total += int(row["actual"])
        return self._metrics_payload(
            counts=counts,
            estimated_total=estimated_total,
            actual_total=actual_total,
            now=now,
        )

    @staticmethod
    def _metrics_payload(
        *,
        counts: dict[str, int],
        estimated_total: int,
        actual_total: int,
        now: datetime,
    ) -> dict[str, Any]:
        return {
            "states": counts,
            "active": sum(
                counts[state] for state in ACTIVE_EXPORT_JOB_STATES
            ),
            "limits": {
                "max_active_jobs": MAX_ACTIVE_EXPORT_JOBS,
                "max_running_jobs": MAX_RUNNING_EXPORT_JOBS,
                "max_attempts": MAX_EXPORT_ATTEMPTS,
                "max_active_cost_units": MAX_ACTIVE_COST_UNITS,
                "max_artifact_bytes": MAX_EXPORT_ARTIFACT_BYTES,
                "artifact_ttl_seconds": EXPORT_ARTIFACT_TTL_SECONDS,
            },
            "cost": {
                "unit": "bounded-render-unit-v1",
                "estimated_total": estimated_total,
                "actual_total": actual_total,
            },
            "observed_at": timestamp(now),
        }

    def artifact_path(
        self,
        job_id: str,
        *,
        now: datetime,
    ) -> tuple[Path, dict[str, Any]]:
        row = self.get(job_id)
        if (
            str(row["state"]) != "succeeded"
            or row["artifact_name"] is None
            or row["expires_at"] is None
            or parse_timestamp(str(row["expires_at"])) <= now
        ):
            raise ExportJobConflict("export_artifact_unavailable")
        name = str(row["artifact_name"])
        if ARTIFACT_NAME_RE.fullmatch(name) is None:
            raise ExportJobError("export_artifact_metadata_invalid")
        root = self.artifacts_root.resolve()
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ExportJobError("export_artifact_missing")
        digest = hashlib.sha256()
        size_bytes = 0
        with path.open("rb") as artifact:
            while True:
                chunk = artifact.read(EXPORT_STREAM_CHUNK_BYTES)
                if not chunk:
                    break
                size_bytes += len(chunk)
                if size_bytes > MAX_EXPORT_ARTIFACT_BYTES:
                    raise ExportJobError("export_artifact_integrity_failed")
                digest.update(chunk)
        if (
            size_bytes != int(row["artifact_size_bytes"])
            or digest.hexdigest() != str(row["artifact_sha256"])
        ):
            raise ExportJobError("export_artifact_integrity_failed")
        return path, row

    def store_artifact(
        self,
        claim: ClaimedExportJob,
        payload: bytes,
    ) -> StoredExportArtifact:
        if len(payload) > MAX_EXPORT_ARTIFACT_BYTES:
            raise ExportJobCapacity("export_artifact_bytes_exceeded")
        extension = claim.artifact_format
        name = f"{claim.job_id}.{extension}"
        if ARTIFACT_NAME_RE.fullmatch(name) is None:
            raise ExportJobError("export_artifact_name_invalid")
        self.artifacts_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.artifacts_root.chmod(0o700)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=self.artifacts_root,
            prefix=f".{claim.job_id}.",
        )
        temporary = Path(temporary_name)
        target = self.artifacts_root / name
        try:
            with os.fdopen(descriptor, "wb") as artifact:
                artifact.write(payload)
                artifact.flush()
                os.fsync(artifact.fileno())
            temporary.chmod(0o600)
            os.replace(temporary, target)
            target.chmod(0o600)
            directory_fd = os.open(self.artifacts_root, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except BaseException:
            _safe_unlink(temporary)
            raise
        return StoredExportArtifact(
            name=name,
            path=target,
            sha256=hashlib.sha256(payload).hexdigest(),
            size_bytes=len(payload),
        )

    def remove_artifact(self, artifact: StoredExportArtifact) -> None:
        _safe_unlink(artifact.path)

    def sweep_expired(self, *, now: datetime) -> int:
        now_text = timestamp(now)
        with self._transaction() as connection:
            rows = connection.execute(
                """
                SELECT * FROM export_jobs
                WHERE state = 'succeeded' AND expires_at <= ?
                ORDER BY expires_at, job_id
                """,
                (now_text,),
            ).fetchall()
            for row in rows:
                connection.execute(
                    """
                    UPDATE export_jobs
                    SET state = 'expired', updated_at = ?,
                        row_version = row_version + 1
                    WHERE job_id = ? AND state = 'succeeded'
                    """,
                    (now_text, str(row["job_id"])),
                )
                self._append_event(
                    connection,
                    job_id=str(row["job_id"]),
                    event_kind="artifact_expired",
                    from_state="succeeded",
                    to_state="expired",
                    attempt_count=int(row["attempt_count"]),
                    now=now,
                    reason_code="export_artifact_expired",
                )
            expired_names = [
                str(row["artifact_name"])
                for row in connection.execute(
                    """
                    SELECT artifact_name FROM export_jobs
                    WHERE state = 'expired' AND artifact_name IS NOT NULL
                    """
                ).fetchall()
                if ARTIFACT_NAME_RE.fullmatch(
                    str(row["artifact_name"])
                )
            ]
        for name in expired_names:
            _safe_unlink(self.artifacts_root / name)
        return len(rows)
