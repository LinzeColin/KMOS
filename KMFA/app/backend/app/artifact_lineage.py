"""Immutable upload lineage and bounded safe-text derivatives for S06/P6.3.

The original object is never opened by the web process for preview.  A
separately invoked worker may process only scanner-confirmed clean plain text
or JSON, emits at most 64 KiB of UTF-8 ``text/plain``, and records the
processor identity before publishing an immutable derived object.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .consistency_state import IDEMPOTENCY_KEY_RE, idempotency_key_hash
from .object_storage import (
    ObjectStorageError,
    content_md5_base64,
    object_store_for_backend,
)
from .structured_store import (
    StructuredStoreConnection,
    StructuredStoreError,
    StructuredStoreIntegrityError,
    open_structured_store,
)

DERIVATION_ENABLED_ENV = "KMFA_ARTIFACT_DERIVATION_ENABLED"
TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
PROCESSOR_NAME = "kmfa-safe-text-extract"
PROCESSOR_VERSION = "1.0.0"
OUTPUT_KIND = "text_extract"
OUTPUT_MEDIA_TYPE = "text/plain"
MAX_PREVIEW_BYTES = 64 * 1024
MAX_TEXT_PREFIX_BYTES = 256 * 1024
PROCESSING_LEASE_SECONDS = 60
PROCESSING_RETRY_SECONDS = 30
MAX_PROCESSING_RUNS_PER_VERSION = 16
MAX_TOTAL_ARTIFACT_BYTES = 512 * 1024 * 1024
SUPPORTED_DETECTED_MEDIA_TYPES = frozenset({"text/plain", "application/json"})
PROCESSOR_IMPLEMENTATION = (
    "kmfa-safe-text-extract-v1:utf8-strict:nfc:"
    "unicode-controls-filtered:prefix-262144:output-65536:text-plain"
)
PROCESSOR_IMPLEMENTATION_SHA256 = hashlib.sha256(
    PROCESSOR_IMPLEMENTATION.encode("ascii")
).hexdigest()


class ArtifactLineageError(StructuredStoreError):
    """Static, private-data-free lineage or processing failure."""


class ArtifactLineageConflict(ArtifactLineageError):
    pass


@dataclass(frozen=True)
class ProcessingClaim:
    processing_run_id: str
    workspace_id: str
    source_artifact_version_id: str
    artifact_id: str
    source_storage_backend: str
    source_storage_key: str
    source_size_bytes: int
    source_sha256: str
    detected_media_type: str
    derivative_id: str
    generation_number: int
    state: str
    attempt_count: int
    row_version: int
    output_storage_backend: str | None
    output_storage_key: str | None
    output_name: str | None
    output_media_type: str | None
    output_size_bytes: int | None
    output_sha256: str | None


@dataclass(frozen=True)
class ProcessingResult:
    processing_run_id: str
    source_artifact_version_id: str
    derivative_id: str
    state: str
    reason_code: str | None
    attempt_count: int


def derivation_enabled() -> bool:
    return (
        os.environ.get(DERIVATION_ENABLED_ENV, "").strip().lower()
        in TRUE_VALUES
    )


def _timestamp(value: datetime | None = None) -> str:
    return (
        (value or datetime.now(timezone.utc))
        .astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(18)}"


def _internal_idempotency_hash(source_artifact_version_id: str) -> str:
    value = (
        f"initial-preview\0{source_artifact_version_id}\0"
        f"{PROCESSOR_NAME}\0{PROCESSOR_VERSION}"
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_output_name() -> str:
    return "kmfa-safe-text-preview.txt"


class ArtifactLineageRepository:
    """Transactional repository; callers own the surrounding transaction."""

    def __init__(self, connection: StructuredStoreConnection) -> None:
        self.connection = connection

    def ensure_processor(self, *, timestamp: str) -> None:
        self.connection.execute(
            """
            INSERT INTO processor_registry(
              processor_name, processor_version, output_kind,
              output_media_type, implementation_sha256, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(processor_name, processor_version) DO NOTHING
            """,
            (
                PROCESSOR_NAME,
                PROCESSOR_VERSION,
                OUTPUT_KIND,
                OUTPUT_MEDIA_TYPE,
                PROCESSOR_IMPLEMENTATION_SHA256,
                timestamp,
            ),
        )
        row = self.connection.execute(
            """
            SELECT *
            FROM processor_registry
            WHERE processor_name = ? AND processor_version = ?
            """,
            (PROCESSOR_NAME, PROCESSOR_VERSION),
        ).fetchone()
        expected = {
            "output_kind": OUTPUT_KIND,
            "output_media_type": OUTPUT_MEDIA_TYPE,
            "implementation_sha256": PROCESSOR_IMPLEMENTATION_SHA256,
        }
        if row is None or any(row[key] != value for key, value in expected.items()):
            raise ArtifactLineageConflict("processor_registry_conflict")

    def ensure_version_lineage(
        self,
        *,
        artifact_version_id: str,
        artifact_id: str,
        version_number: int,
        source_operation_id: str | None,
        created_at: str,
    ) -> None:
        parent = self.connection.execute(
            """
            SELECT artifact_version_id
            FROM artifact_versions
            WHERE artifact_id = ? AND version_number < ?
            ORDER BY version_number DESC
            LIMIT 1
            """,
            (artifact_id, version_number),
        ).fetchone()
        parent_id = (
            str(parent["artifact_version_id"]) if parent is not None else None
        )
        relation_kind = "revision" if parent_id is not None else "root"
        self.connection.execute(
            """
            INSERT INTO artifact_version_lineage(
              artifact_version_id, parent_artifact_version_id,
              source_operation_id, relation_kind, created_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(artifact_version_id) DO NOTHING
            """,
            (
                artifact_version_id,
                parent_id,
                source_operation_id,
                relation_kind,
                created_at,
            ),
        )
        row = self.connection.execute(
            """
            SELECT *
            FROM artifact_version_lineage
            WHERE artifact_version_id = ?
            """,
            (artifact_version_id,),
        ).fetchone()
        expected = {
            "parent_artifact_version_id": parent_id,
            "source_operation_id": source_operation_id,
            "relation_kind": relation_kind,
            "created_at": created_at,
        }
        if row is None or any(row[key] != value for key, value in expected.items()):
            raise ArtifactLineageConflict("artifact_lineage_conflict")

    def _create_or_load_run(
        self,
        *,
        workspace_id: str,
        source_artifact_version_id: str,
        key_hash: str,
        timestamp: str,
    ) -> tuple[Any, bool]:
        self.ensure_processor(timestamp=timestamp)
        processing_run_id = _new_id("processing-run")
        derivative_id = _new_id("derivative")
        generation_number = int(
            self.connection.execute(
                """
                SELECT COALESCE(MAX(generation_number), 0) + 1
                  AS next_generation
                FROM artifact_processing_runs
                WHERE source_artifact_version_id = ?
                  AND processor_name = ?
                  AND processor_version = ?
                """,
                (
                    source_artifact_version_id,
                    PROCESSOR_NAME,
                    PROCESSOR_VERSION,
                ),
            ).fetchone()["next_generation"]
        )
        inserted = self.connection.execute(
            """
            INSERT INTO artifact_processing_runs(
              processing_run_id, workspace_id, source_artifact_version_id,
              processor_name, processor_version, idempotency_key_hash,
              derivative_id, generation_number, state, attempt_count,
              lease_until,
              last_error_code, row_version, requested_at, updated_at,
              completed_at
            ) VALUES (
              ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 0, NULL, NULL, 1, ?, ?, NULL
            )
            ON CONFLICT(
              source_artifact_version_id,
              processor_name,
              processor_version,
              idempotency_key_hash
            ) DO NOTHING
            """,
            (
                processing_run_id,
                workspace_id,
                source_artifact_version_id,
                PROCESSOR_NAME,
                PROCESSOR_VERSION,
                key_hash,
                derivative_id,
                generation_number,
                timestamp,
                timestamp,
            ),
        )
        row = self.connection.execute(
            """
            SELECT *
            FROM artifact_processing_runs
            WHERE source_artifact_version_id = ?
              AND processor_name = ?
              AND processor_version = ?
              AND idempotency_key_hash = ?
            """,
            (
                source_artifact_version_id,
                PROCESSOR_NAME,
                PROCESSOR_VERSION,
                key_hash,
            ),
        ).fetchone()
        if (
            row is None
            or str(row["workspace_id"]) != workspace_id
            or str(row["source_artifact_version_id"])
            != source_artifact_version_id
        ):
            raise ArtifactLineageConflict("processing_request_conflict")
        return row, inserted.rowcount == 1

    def ensure_initial_run(
        self,
        *,
        workspace_id: str,
        source_artifact_version_id: str,
        timestamp: str,
    ) -> Any:
        row, _ = self._create_or_load_run(
            workspace_id=workspace_id,
            source_artifact_version_id=source_artifact_version_id,
            key_hash=_internal_idempotency_hash(source_artifact_version_id),
            timestamp=timestamp,
        )
        return row

    def request_reprocess(
        self,
        *,
        workspace_id: str,
        source_artifact_version_id: str,
        idempotency_key: str,
        timestamp: str,
    ) -> tuple[Any, bool]:
        if IDEMPOTENCY_KEY_RE.fullmatch(idempotency_key) is None:
            raise ArtifactLineageError("invalid_idempotency_key")
        key_hash = idempotency_key_hash(idempotency_key)
        existing = self.connection.execute(
            """
            SELECT *
            FROM artifact_processing_runs
            WHERE source_artifact_version_id = ?
              AND processor_name = ?
              AND processor_version = ?
              AND idempotency_key_hash = ?
            """,
            (
                source_artifact_version_id,
                PROCESSOR_NAME,
                PROCESSOR_VERSION,
                key_hash,
            ),
        ).fetchone()
        if existing is not None:
            if str(existing["workspace_id"]) != workspace_id:
                raise ArtifactLineageConflict(
                    "processing_request_conflict"
                )
            return existing, False
        run_count = int(
            self.connection.execute(
                """
                SELECT COUNT(*) AS count_value
                FROM artifact_processing_runs
                WHERE source_artifact_version_id = ?
                  AND processor_name = ?
                  AND processor_version = ?
                """,
                (
                    source_artifact_version_id,
                    PROCESSOR_NAME,
                    PROCESSOR_VERSION,
                ),
            ).fetchone()["count_value"]
        )
        if run_count >= MAX_PROCESSING_RUNS_PER_VERSION:
            raise ArtifactLineageConflict(
                "processing_request_capacity_reached"
            )
        return self._create_or_load_run(
            workspace_id=workspace_id,
            source_artifact_version_id=source_artifact_version_id,
            key_hash=key_hash,
            timestamp=timestamp,
        )

    def seed_next_clean_version(self, *, timestamp: str) -> Any | None:
        self.ensure_processor(timestamp=timestamp)
        row = self.connection.execute(
            """
            SELECT
              av.artifact_version_id,
              p.workspace_id
            FROM artifact_versions av
            JOIN projects p ON p.project_id = av.project_id
            JOIN workspace_retention wr ON wr.workspace_id = p.workspace_id
            JOIN artifact_security_assessments security
              ON security.artifact_version_id = av.artifact_version_id
            WHERE av.lifecycle_state = 'active'
              AND p.lifecycle_state = 'active'
              AND wr.state = 'active'
              AND security.state = 'clean'
              AND security.detected_media_type IN ('text/plain', 'application/json')
              AND NOT EXISTS (
                SELECT 1
                FROM artifact_processing_runs run
                WHERE run.source_artifact_version_id =
                  av.artifact_version_id
                  AND run.processor_name = ?
                  AND run.processor_version = ?
              )
            ORDER BY av.created_at, av.artifact_version_id
            LIMIT 1
            """,
            (
                PROCESSOR_NAME,
                PROCESSOR_VERSION,
            ),
        ).fetchone()
        if row is None:
            return None
        # The SQL cannot portably calculate the application hash. A second
        # idempotent lookup with the exact value prevents duplicate seeds.
        return self.ensure_initial_run(
            workspace_id=str(row["workspace_id"]),
            source_artifact_version_id=str(row["artifact_version_id"]),
            timestamp=timestamp,
        )

    def claim(
        self,
        *,
        now: datetime,
        lease_seconds: int = PROCESSING_LEASE_SECONDS,
        retry_seconds: int = PROCESSING_RETRY_SECONDS,
    ) -> ProcessingClaim | None:
        now_text = _timestamp(now)
        retry_before = _timestamp(now - timedelta(seconds=retry_seconds))
        row = self.connection.execute(
            """
            SELECT
              run.*,
              av.artifact_id,
              av.storage_backend AS source_storage_backend,
              av.storage_key AS source_storage_key,
              av.size_bytes AS source_size_bytes,
              av.sha256 AS source_sha256,
              security.detected_media_type
            FROM artifact_processing_runs run
            JOIN artifact_versions av
              ON av.artifact_version_id = run.source_artifact_version_id
            JOIN artifact_security_assessments security
              ON security.artifact_version_id = run.source_artifact_version_id
            JOIN workspace_retention wr
              ON wr.workspace_id = run.workspace_id
            WHERE wr.state = 'active'
              AND security.state = 'clean'
              AND (
                (
                  run.state = 'pending'
                  AND (
                    run.last_error_code IS NULL
                    OR run.updated_at <= ?
                  )
                )
                OR (
                  run.state = 'processing'
                  AND run.lease_until <= ?
                )
                OR (
                  run.state = 'prepared'
                  AND (run.lease_until IS NULL OR run.lease_until <= ?)
                  AND (
                    run.last_error_code IS NULL
                    OR run.updated_at <= ?
                  )
                )
              )
            ORDER BY run.updated_at, run.processing_run_id
            LIMIT 1
            """,
            (retry_before, now_text, now_text, retry_before),
        ).fetchone()
        if row is None:
            return None
        from_state = str(row["state"])
        to_state = "prepared" if from_state == "prepared" else "processing"
        lease_until = _timestamp(now + timedelta(seconds=lease_seconds))
        updated = self.connection.execute(
            """
            UPDATE artifact_processing_runs
            SET state = ?, attempt_count = attempt_count + 1,
                lease_until = ?, last_error_code = NULL,
                row_version = row_version + 1, updated_at = ?
            WHERE processing_run_id = ? AND row_version = ? AND state = ?
            """,
            (
                to_state,
                lease_until,
                now_text,
                row["processing_run_id"],
                row["row_version"],
                from_state,
            ),
        )
        if updated.rowcount != 1:
            return None
        claimed = self.connection.execute(
            """
            SELECT
              run.*,
              av.artifact_id,
              av.storage_backend AS source_storage_backend,
              av.storage_key AS source_storage_key,
              av.size_bytes AS source_size_bytes,
              av.sha256 AS source_sha256,
              security.detected_media_type
            FROM artifact_processing_runs run
            JOIN artifact_versions av
              ON av.artifact_version_id = run.source_artifact_version_id
            JOIN artifact_security_assessments security
              ON security.artifact_version_id = run.source_artifact_version_id
            WHERE run.processing_run_id = ?
            """,
            (row["processing_run_id"],),
        ).fetchone()
        if claimed is None:
            raise ArtifactLineageConflict("processing_claim_missing")
        return ProcessingClaim(
            processing_run_id=str(claimed["processing_run_id"]),
            workspace_id=str(claimed["workspace_id"]),
            source_artifact_version_id=str(
                claimed["source_artifact_version_id"]
            ),
            artifact_id=str(claimed["artifact_id"]),
            source_storage_backend=str(claimed["source_storage_backend"]),
            source_storage_key=str(claimed["source_storage_key"]),
            source_size_bytes=int(claimed["source_size_bytes"]),
            source_sha256=str(claimed["source_sha256"]),
            detected_media_type=str(claimed["detected_media_type"]),
            derivative_id=str(claimed["derivative_id"]),
            generation_number=int(claimed["generation_number"]),
            state=str(claimed["state"]),
            attempt_count=int(claimed["attempt_count"]),
            row_version=int(claimed["row_version"]),
            output_storage_backend=claimed["output_storage_backend"],
            output_storage_key=claimed["output_storage_key"],
            output_name=claimed["output_name"],
            output_media_type=claimed["output_media_type"],
            output_size_bytes=(
                int(claimed["output_size_bytes"])
                if claimed["output_size_bytes"] is not None
                else None
            ),
            output_sha256=claimed["output_sha256"],
        )

    def prepare(
        self,
        claim: ProcessingClaim,
        *,
        storage_backend: str,
        storage_key: str,
        output: bytes,
        timestamp: str,
    ) -> ProcessingClaim:
        output_sha256 = hashlib.sha256(output).hexdigest()
        capacity = self.connection.execute(
            """
            SELECT
              COALESCE((SELECT SUM(size_bytes) FROM artifact_versions), 0)
              +
              COALESCE((SELECT SUM(size_bytes) FROM artifact_derivatives), 0)
              +
              COALESCE((
                SELECT SUM(operation.size_bytes)
                FROM consistency_operations operation
                WHERE operation.operation_kind = 'upload'
                  AND operation.size_bytes IS NOT NULL
                  AND NOT (
                    operation.state = 'isolated'
                    AND operation.last_error_code =
                      'resumable_upload_cancelled'
                    AND operation.staged_object_name LIKE ?
                  )
                  AND NOT EXISTS (
                    SELECT 1
                    FROM artifact_versions version
                    WHERE version.artifact_version_id =
                      operation.artifact_version_id
                  )
              ), 0)
              +
              COALESCE((
                SELECT SUM(run.output_size_bytes)
                FROM artifact_processing_runs run
                WHERE run.state = 'prepared'
                  AND run.output_size_bytes IS NOT NULL
                  AND NOT EXISTS (
                    SELECT 1
                    FROM artifact_derivatives derivative
                    WHERE derivative.processing_run_id =
                      run.processing_run_id
                  )
              ), 0) AS total_bytes
            """,
            ("resumable-%",),
        ).fetchone()
        if (
            int(capacity["total_bytes"]) + len(output)
            > MAX_TOTAL_ARTIFACT_BYTES
        ):
            raise ArtifactLineageConflict("processor_capacity_reached")
        updated = self.connection.execute(
            """
            UPDATE artifact_processing_runs
            SET state = 'prepared',
                output_storage_backend = ?,
                output_storage_key = ?,
                output_name = ?,
                output_media_type = ?,
                output_size_bytes = ?,
                output_sha256 = ?,
                lease_until = ?,
                last_error_code = NULL,
                row_version = row_version + 1,
                updated_at = ?
            WHERE processing_run_id = ?
              AND state = 'processing'
              AND row_version = ?
            """,
            (
                storage_backend,
                storage_key,
                _safe_output_name(),
                OUTPUT_MEDIA_TYPE,
                len(output),
                output_sha256,
                _timestamp(
                    datetime.now(timezone.utc)
                    + timedelta(seconds=PROCESSING_LEASE_SECONDS)
                ),
                timestamp,
                claim.processing_run_id,
                claim.row_version,
            ),
        )
        if updated.rowcount != 1:
            raise ArtifactLineageConflict("processing_state_conflict")
        row = self.connection.execute(
            """
            SELECT
              run.*,
              av.artifact_id,
              av.storage_backend AS source_storage_backend,
              av.storage_key AS source_storage_key,
              av.size_bytes AS source_size_bytes,
              av.sha256 AS source_sha256,
              security.detected_media_type
            FROM artifact_processing_runs run
            JOIN artifact_versions av
              ON av.artifact_version_id = run.source_artifact_version_id
            JOIN artifact_security_assessments security
              ON security.artifact_version_id = run.source_artifact_version_id
            WHERE run.processing_run_id = ?
            """,
            (claim.processing_run_id,),
        ).fetchone()
        if row is None:
            raise ArtifactLineageConflict("processing_claim_missing")
        return ProcessingClaim(
            processing_run_id=claim.processing_run_id,
            workspace_id=claim.workspace_id,
            source_artifact_version_id=claim.source_artifact_version_id,
            artifact_id=claim.artifact_id,
            source_storage_backend=claim.source_storage_backend,
            source_storage_key=claim.source_storage_key,
            source_size_bytes=claim.source_size_bytes,
            source_sha256=claim.source_sha256,
            detected_media_type=claim.detected_media_type,
            derivative_id=claim.derivative_id,
            generation_number=claim.generation_number,
            state="prepared",
            attempt_count=claim.attempt_count,
            row_version=int(row["row_version"]),
            output_storage_backend=str(row["output_storage_backend"]),
            output_storage_key=str(row["output_storage_key"]),
            output_name=str(row["output_name"]),
            output_media_type=str(row["output_media_type"]),
            output_size_bytes=int(row["output_size_bytes"]),
            output_sha256=str(row["output_sha256"]),
        )

    def mark_not_applicable(
        self,
        claim: ProcessingClaim,
        *,
        reason_code: str,
        timestamp: str,
    ) -> ProcessingResult:
        updated = self.connection.execute(
            """
            UPDATE artifact_processing_runs
            SET state = 'not_applicable', lease_until = NULL,
                last_error_code = ?, row_version = row_version + 1,
                updated_at = ?, completed_at = ?
            WHERE processing_run_id = ?
              AND state = 'processing'
              AND row_version = ?
            """,
            (
                reason_code,
                timestamp,
                timestamp,
                claim.processing_run_id,
                claim.row_version,
            ),
        )
        if updated.rowcount != 1:
            raise ArtifactLineageConflict("processing_state_conflict")
        return ProcessingResult(
            processing_run_id=claim.processing_run_id,
            source_artifact_version_id=claim.source_artifact_version_id,
            derivative_id=claim.derivative_id,
            state="not_applicable",
            reason_code=reason_code,
            attempt_count=claim.attempt_count,
        )

    def record_retry(
        self,
        claim: ProcessingClaim,
        *,
        reason_code: str,
        timestamp: str,
    ) -> None:
        retry_state = "prepared" if claim.state == "prepared" else "pending"
        self.connection.execute(
            """
            UPDATE artifact_processing_runs
            SET state = ?, lease_until = NULL, last_error_code = ?,
                row_version = row_version + 1, updated_at = ?
            WHERE processing_run_id = ?
              AND row_version = ?
              AND state = ?
            """,
            (
                retry_state,
                reason_code,
                timestamp,
                claim.processing_run_id,
                claim.row_version,
                claim.state,
            ),
        )

    def complete(
        self,
        claim: ProcessingClaim,
        *,
        timestamp: str,
    ) -> ProcessingResult:
        if (
            claim.state != "prepared"
            or claim.output_storage_backend is None
            or claim.output_storage_key is None
            or claim.output_name is None
            or claim.output_media_type != OUTPUT_MEDIA_TYPE
            or claim.output_size_bytes is None
            or claim.output_sha256 is None
        ):
            raise ArtifactLineageConflict("processing_output_incomplete")
        self.connection.execute(
            """
            INSERT INTO artifact_derivatives(
              derivative_id, processing_run_id,
              source_artifact_version_id, artifact_id,
              processor_name, processor_version, output_kind,
              generation_number, storage_backend, storage_key,
              original_name, media_type, size_bytes, sha256, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(processing_run_id) DO NOTHING
            """,
            (
                claim.derivative_id,
                claim.processing_run_id,
                claim.source_artifact_version_id,
                claim.artifact_id,
                PROCESSOR_NAME,
                PROCESSOR_VERSION,
                OUTPUT_KIND,
                claim.generation_number,
                claim.output_storage_backend,
                claim.output_storage_key,
                claim.output_name,
                claim.output_media_type,
                claim.output_size_bytes,
                claim.output_sha256,
                timestamp,
            ),
        )
        derivative = self.connection.execute(
            """
            SELECT *
            FROM artifact_derivatives
            WHERE processing_run_id = ?
            """,
            (claim.processing_run_id,),
        ).fetchone()
        expected = {
            "derivative_id": claim.derivative_id,
            "source_artifact_version_id": claim.source_artifact_version_id,
            "artifact_id": claim.artifact_id,
            "processor_name": PROCESSOR_NAME,
            "processor_version": PROCESSOR_VERSION,
            "output_kind": OUTPUT_KIND,
            "generation_number": claim.generation_number,
            "storage_backend": claim.output_storage_backend,
            "storage_key": claim.output_storage_key,
            "original_name": claim.output_name,
            "media_type": claim.output_media_type,
            "size_bytes": claim.output_size_bytes,
            "sha256": claim.output_sha256,
            "created_at": timestamp,
        }
        if derivative is None or any(
            derivative[key] != value for key, value in expected.items()
        ):
            raise StructuredStoreIntegrityError(
                "artifact derivative projection conflict"
            )
        updated = self.connection.execute(
            """
            UPDATE artifact_processing_runs
            SET state = 'converged', lease_until = NULL,
                last_error_code = NULL, row_version = row_version + 1,
                updated_at = ?, completed_at = ?
            WHERE processing_run_id = ?
              AND state = 'prepared'
              AND row_version = ?
            """,
            (
                timestamp,
                timestamp,
                claim.processing_run_id,
                claim.row_version,
            ),
        )
        if updated.rowcount != 1:
            current = self.connection.execute(
                """
                SELECT state FROM artifact_processing_runs
                WHERE processing_run_id = ?
                """,
                (claim.processing_run_id,),
            ).fetchone()
            if current is None or str(current["state"]) != "converged":
                raise ArtifactLineageConflict("processing_state_conflict")
        return ProcessingResult(
            processing_run_id=claim.processing_run_id,
            source_artifact_version_id=claim.source_artifact_version_id,
            derivative_id=claim.derivative_id,
            state="converged",
            reason_code=None,
            attempt_count=claim.attempt_count,
        )

    def latest_derivative(self, artifact_version_id: str) -> Any | None:
        return self.connection.execute(
            """
            SELECT *
            FROM artifact_derivatives
            WHERE source_artifact_version_id = ?
            ORDER BY generation_number DESC
            LIMIT 1
            """,
            (artifact_version_id,),
        ).fetchone()

    def lineage_graph(self, workspace_id: str) -> dict[str, Any]:
        versions = self.connection.execute(
            """
            SELECT
              av.artifact_version_id,
              av.artifact_id,
              av.version_number,
              av.original_name,
              av.reported_media_type,
              av.size_bytes,
              av.sha256,
              av.created_at,
              lineage.parent_artifact_version_id,
              lineage.relation_kind,
              lineage.source_operation_id
            FROM artifact_versions av
            JOIN projects p ON p.project_id = av.project_id
            LEFT JOIN artifact_version_lineage lineage
              ON lineage.artifact_version_id = av.artifact_version_id
            WHERE p.workspace_id = ?
            ORDER BY av.version_number, av.artifact_version_id
            """,
            (workspace_id,),
        ).fetchall()
        derivatives = self.connection.execute(
            """
            SELECT
              derivative.derivative_id,
              derivative.processing_run_id,
              derivative.source_artifact_version_id,
              derivative.output_kind,
              derivative.media_type,
              derivative.size_bytes,
              derivative.sha256,
              derivative.processor_name,
              derivative.processor_version,
              derivative.generation_number,
              derivative.created_at
            FROM artifact_derivatives derivative
            JOIN artifact_versions av
              ON av.artifact_version_id =
                derivative.source_artifact_version_id
            JOIN projects p ON p.project_id = av.project_id
            WHERE p.workspace_id = ?
            ORDER BY derivative.generation_number, derivative.derivative_id
            """,
            (workspace_id,),
        ).fetchall()
        version_nodes = []
        edges = []
        lineage_gaps = 0
        version_ids = {
            str(row["artifact_version_id"]) for row in versions
        }
        for row in versions:
            node_id = str(row["artifact_version_id"])
            parent_id = row["parent_artifact_version_id"]
            relation = row["relation_kind"]
            if relation not in {"root", "revision"}:
                lineage_gaps += 1
            if relation == "revision":
                if parent_id is None or str(parent_id) not in version_ids:
                    lineage_gaps += 1
                else:
                    edges.append(
                        {
                            "from": str(parent_id),
                            "to": node_id,
                            "relation": "revision",
                        }
                    )
            elif relation == "root" and parent_id is not None:
                lineage_gaps += 1
            version_nodes.append(
                {
                    "id": node_id,
                    "kind": "original",
                    "artifact_id": str(row["artifact_id"]),
                    "version_number": int(row["version_number"]),
                    "name": str(row["original_name"]),
                    "media_type": str(row["reported_media_type"]),
                    "size_bytes": int(row["size_bytes"]),
                    "sha256": str(row["sha256"]),
                    "source_operation_id": row["source_operation_id"],
                    "created_at": str(row["created_at"]),
                }
            )
        derivative_nodes = []
        for row in derivatives:
            source_id = str(row["source_artifact_version_id"])
            derivative_id = str(row["derivative_id"])
            if source_id not in version_ids:
                lineage_gaps += 1
            else:
                edges.append(
                    {
                        "from": source_id,
                        "to": derivative_id,
                        "relation": "derived",
                    }
                )
            derivative_nodes.append(
                {
                    "id": derivative_id,
                    "kind": str(row["output_kind"]),
                    "processing_run_id": str(row["processing_run_id"]),
                    "media_type": str(row["media_type"]),
                    "size_bytes": int(row["size_bytes"]),
                    "sha256": str(row["sha256"]),
                    "processor": {
                        "name": str(row["processor_name"]),
                        "version": str(row["processor_version"]),
                    },
                    "generation_number": int(row["generation_number"]),
                    "created_at": str(row["created_at"]),
                }
            )
        return {
            "schema_version": "kmfa.s06.p63.artifact-lineage.v1",
            "workspace_id": workspace_id,
            "nodes": [*version_nodes, *derivative_nodes],
            "edges": edges,
            "version_count": len(version_nodes),
            "derivative_count": len(derivative_nodes),
            "lineage_gaps": lineage_gaps,
        }


def _safe_text_extract(source: Path) -> bytes:
    with source.open("rb") as handle:
        prefix = handle.read(MAX_TEXT_PREFIX_BYTES + 1)
    truncated_source = len(prefix) > MAX_TEXT_PREFIX_BYTES
    prefix = prefix[:MAX_TEXT_PREFIX_BYTES]
    try:
        text = prefix.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ArtifactLineageError("processor_utf8_required") from exc
    normalized = unicodedata.normalize("NFC", text)
    cleaned = "".join(
        character
        if (
            character in {"\n", "\r", "\t"}
            or not unicodedata.category(character).startswith("C")
        )
        else "\ufffd"
        for character in normalized
    )
    suffix = "\n…[KMFA preview truncated]\n" if truncated_source else ""
    candidate = (cleaned + suffix).encode("utf-8")
    if len(candidate) <= MAX_PREVIEW_BYTES:
        return candidate
    suffix_bytes = "\n…[KMFA preview truncated]\n".encode()
    budget = MAX_PREVIEW_BYTES - len(suffix_bytes)
    output = cleaned.encode("utf-8")[:budget]
    while True:
        try:
            output.decode("utf-8", errors="strict")
            break
        except UnicodeDecodeError:
            output = output[:-1]
    return output + suffix_bytes


def _write_private_temp(directory: Path, payload: bytes) -> Path:
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory.chmod(0o700)
    target = directory / f"derivative-{secrets.token_urlsafe(24)}.part"
    descriptor = os.open(
        target,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY,
        0o600,
    )
    with os.fdopen(descriptor, "wb") as output:
        output.write(payload)
        output.flush()
        os.fsync(output.fileno())
    return target


def _output_for_claim(
    state_root: Path,
    claim: ProcessingClaim,
) -> tuple[bytes, Any]:
    if claim.detected_media_type not in SUPPORTED_DETECTED_MEDIA_TYPES:
        raise ArtifactLineageError("processor_media_type_not_supported")
    source_store = object_store_for_backend(
        state_root,
        claim.source_storage_backend,
    )
    materialized = source_store.materialize_verified(
        storage_key=claim.source_storage_key,
        expected_size=claim.source_size_bytes,
        expected_sha256=claim.source_sha256,
    )
    try:
        output = _safe_text_extract(materialized.path)
    finally:
        if materialized.temporary:
            materialized.path.unlink(missing_ok=True)
    return output, source_store


def run_artifact_derivation_once(
    *,
    state_root: Path,
    now: datetime | None = None,
) -> ProcessingResult | None:
    """Seed and process at most one scanner-clean derivative request."""

    if not derivation_enabled():
        return None
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    connection = open_structured_store(
        state_root / "walking_skeleton.sqlite3"
    )
    try:
        with connection.transaction():
            repository = ArtifactLineageRepository(connection)
            repository.seed_next_clean_version(timestamp=_timestamp(current_time))
            claim = repository.claim(now=current_time)
    finally:
        connection.close()
    if claim is None:
        return None

    output: bytes | None = None
    output_store: Any | None = None
    prepared = claim
    try:
        output, output_store = _output_for_claim(state_root, claim)
        output_sha256 = hashlib.sha256(output).hexdigest()
        if claim.state == "processing":
            storage_key = output_store.build_storage_key(
                workspace_id=claim.workspace_id,
                artifact_id=claim.artifact_id,
                artifact_version_id=claim.derivative_id,
                version_number=1,
                sha256=output_sha256,
            )
            connection = open_structured_store(
                state_root / "walking_skeleton.sqlite3"
            )
            try:
                with connection.transaction():
                    prepared = ArtifactLineageRepository(connection).prepare(
                        claim,
                        storage_backend=output_store.storage_backend,
                        storage_key=storage_key,
                        output=output,
                        timestamp=_timestamp(),
                    )
            finally:
                connection.close()
        else:
            if (
                claim.output_size_bytes != len(output)
                or claim.output_sha256 != output_sha256
                or claim.output_storage_backend
                != output_store.storage_backend
            ):
                raise ArtifactLineageConflict("processing_output_conflict")
        assert prepared.output_storage_key is not None
        assert prepared.output_size_bytes is not None
        assert prepared.output_sha256 is not None
        temp = _write_private_temp(state_root / "tmp", output)
        try:
            md5_digest = hashlib.md5(output, usedforsecurity=False)
            try:
                output_store.put_file(
                    temp,
                    storage_key=prepared.output_storage_key,
                    size_bytes=prepared.output_size_bytes,
                    sha256=prepared.output_sha256,
                    content_md5=content_md5_base64(md5_digest),
                    artifact_id=prepared.artifact_id,
                    artifact_version_id=prepared.derivative_id,
                )
            except ObjectStorageError:
                output_store.verify_existing(
                    storage_key=prepared.output_storage_key,
                    expected_size=prepared.output_size_bytes,
                    expected_sha256=prepared.output_sha256,
                    artifact_id=prepared.artifact_id,
                    artifact_version_id=prepared.derivative_id,
                )
        finally:
            temp.unlink(missing_ok=True)
        connection = open_structured_store(
            state_root / "walking_skeleton.sqlite3"
        )
        try:
            with connection.transaction():
                return ArtifactLineageRepository(connection).complete(
                    prepared,
                    timestamp=_timestamp(),
                )
        finally:
            connection.close()
    except ArtifactLineageError as exc:
        reason_code = str(exc)
        connection = open_structured_store(
            state_root / "walking_skeleton.sqlite3"
        )
        try:
            with connection.transaction():
                repository = ArtifactLineageRepository(connection)
                if claim.state == "processing" and reason_code in {
                    "processor_capacity_reached",
                    "processor_media_type_not_supported",
                    "processor_utf8_required",
                }:
                    return repository.mark_not_applicable(
                        claim,
                        reason_code=reason_code,
                        timestamp=_timestamp(),
                    )
                repository.record_retry(
                    prepared,
                    reason_code="processor_retryable_error",
                    timestamp=_timestamp(),
                )
        finally:
            connection.close()
        return ProcessingResult(
            processing_run_id=claim.processing_run_id,
            source_artifact_version_id=claim.source_artifact_version_id,
            derivative_id=claim.derivative_id,
            state="pending",
            reason_code="processor_retryable_error",
            attempt_count=claim.attempt_count,
        )
    except (ObjectStorageError, OSError):
        connection = open_structured_store(
            state_root / "walking_skeleton.sqlite3"
        )
        try:
            with connection.transaction():
                ArtifactLineageRepository(connection).record_retry(
                    prepared,
                    reason_code="processor_storage_retryable",
                    timestamp=_timestamp(),
                )
        finally:
            connection.close()
        return ProcessingResult(
            processing_run_id=claim.processing_run_id,
            source_artifact_version_id=claim.source_artifact_version_id,
            derivative_id=claim.derivative_id,
            state=prepared.state,
            reason_code="processor_storage_retryable",
            attempt_count=claim.attempt_count,
        )


def public_derivation_contract() -> dict[str, Any]:
    enabled = derivation_enabled()
    return {
        "enabled": enabled,
        "mode": (
            "immutable-safe-text-v1"
            if enabled
            else "rollback-originals-preserved"
        ),
        "processor": {
            "name": PROCESSOR_NAME,
            "version": PROCESSOR_VERSION,
            "implementation_sha256": PROCESSOR_IMPLEMENTATION_SHA256,
        },
        "eligible_security_state": "clean",
        "supported_detected_media_types": sorted(
            SUPPORTED_DETECTED_MEDIA_TYPES
        ),
        "output_media_type": OUTPUT_MEDIA_TYPE,
        "max_preview_bytes": MAX_PREVIEW_BYTES,
        "max_processing_runs_per_version": MAX_PROCESSING_RUNS_PER_VERSION,
        "max_total_artifact_bytes": MAX_TOTAL_ARTIFACT_BYTES,
        "executes_user_code_or_macros": False,
        "web_process_parses_originals": False,
        "rollback_preserves_originals_and_lineage": True,
    }
