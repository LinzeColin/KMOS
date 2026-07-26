"""Additive, idempotent v1.5 SQLite-to-PostgreSQL structured-state import.

The source is opened read-only and is never removed or modified.  The target
DSN is accepted only from ``KMFA_STRUCTURED_DATABASE_URL``; command-line
arguments and result JSON therefore cannot accidentally persist credentials.
Conflicting target rows abort the whole import instead of silently overwriting
either history or newer PostgreSQL state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import quote

from .retention_lifecycle import LifecycleRepository
from .structured_repository import StructuredRepository
from .structured_store import (
    POSTGRESQL_MODE,
    StructuredStoreConnection,
    StructuredStoreError,
    configured_mode,
    open_structured_store,
)

_CORE_TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "workspaces": (
        "workspace_id",
        "recovery_hash",
        "project_name",
        "progress",
        "created_at",
        "updated_at",
    ),
    "access_tokens": (
        "token_hash",
        "workspace_id",
        "created_at",
        "expires_at",
        "issuance_order",
    ),
    "artifacts": (
        "artifact_id",
        "workspace_id",
        "object_name",
        "original_name",
        "reported_media_type",
        "size_bytes",
        "sha256",
        "created_at",
    ),
    "audit_events": (
        "event_id",
        "workspace_id",
        "action",
        "result_status",
        "artifact_sha256",
        "created_at",
    ),
}
_STRUCTURED_TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "projects": (
        "project_id",
        "workspace_id",
        "name",
        "lifecycle_state",
        "row_version",
        "created_at",
        "updated_at",
    ),
    "project_metrics": (
        "project_id",
        "progress",
        "score",
        "row_version",
        "updated_at",
    ),
    "financial_records": (
        "financial_record_id",
        "project_id",
        "record_type",
        "category",
        "amount_minor",
        "currency",
        "effective_date",
        "source_ref",
        "row_version",
        "created_at",
        "updated_at",
    ),
    "artifact_versions": (
        "artifact_version_id",
        "artifact_id",
        "project_id",
        "version_number",
        "storage_backend",
        "storage_key",
        "original_name",
        "reported_media_type",
        "size_bytes",
        "sha256",
        "lifecycle_state",
        "created_at",
    ),
    "workspace_tasks": (
        "task_id",
        "project_id",
        "title",
        "status",
        "sort_order",
        "due_at",
        "row_version",
        "created_at",
        "updated_at",
    ),
}
_CONSISTENCY_TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "consistency_operations": (
        "operation_id",
        "workspace_id",
        "operation_kind",
        "idempotency_key_hash",
        "request_fingerprint",
        "artifact_id",
        "artifact_version_id",
        "storage_backend",
        "storage_key",
        "staged_object_name",
        "original_name",
        "reported_media_type",
        "size_bytes",
        "content_sha256",
        "state",
        "attempt_count",
        "next_attempt_at",
        "last_error_code",
        "row_version",
        "created_at",
        "updated_at",
    ),
    "consistency_outbox": (
        "outbox_event_id",
        "operation_id",
        "effect_kind",
        "dedupe_key",
        "state",
        "attempt_count",
        "available_at",
        "lease_until",
        "last_error_code",
        "created_at",
        "updated_at",
    ),
    "consistency_effect_receipts": (
        "dedupe_key",
        "operation_id",
        "effect_kind",
        "receipt_hash",
        "applied_at",
    ),
    "consistency_trace": (
        "trace_event_id",
        "operation_id",
        "from_state",
        "to_state",
        "transition_code",
        "error_code",
        "created_at",
    ),
    "object_quarantine": (
        "quarantine_id",
        "operation_id",
        "storage_backend",
        "storage_key",
        "object_ref",
        "reason_code",
        "state",
        "first_seen_at",
        "last_seen_at",
    ),
}
_SECURITY_TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "artifact_security_assessments": (
        "artifact_version_id",
        "operation_id",
        "normalized_name",
        "reported_media_type",
        "detected_media_type",
        "source_size_bytes",
        "source_sha256",
        "state",
        "reason_code",
        "scanner_engine",
        "scanner_version",
        "policy_version",
        "attempt_count",
        "lease_until",
        "row_version",
        "created_at",
        "updated_at",
        "completed_at",
    ),
    "artifact_security_events": (
        "event_id",
        "artifact_ref",
        "from_state",
        "to_state",
        "reason_code",
        "created_at",
    ),
}
_LIFECYCLE_TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "restore_drill_proofs": (
        "proof_id",
        "backup_id",
        "backup_manifest_sha256",
        "source_schema_version",
        "expected_fixture_count",
        "restored_fixture_count",
        "invariant_failures",
        "measured_rpo_ms",
        "measured_rto_ms",
        "artifact_identity_hash",
        "status",
        "verified_at",
    ),
    "workspace_retention": (
        "workspace_id",
        "state",
        "active_deletion_request_id",
        "row_version",
        "created_at",
        "updated_at",
        "deleted_at",
    ),
    "legal_holds": (
        "hold_id",
        "workspace_id",
        "reason_code",
        "authority_ref_hash",
        "state",
        "imposed_at",
        "released_at",
    ),
    "deletion_requests": (
        "deletion_request_id",
        "workspace_id",
        "idempotency_key_hash",
        "request_fingerprint",
        "restore_proof_id",
        "state",
        "public_purge_due_at",
        "public_purged_at",
        "attempt_count",
        "last_error_code",
        "row_version",
        "requested_at",
        "updated_at",
        "completed_at",
    ),
    "deletion_object_targets": (
        "deletion_request_id",
        "artifact_version_id",
        "artifact_id",
        "storage_backend",
        "storage_key",
        "size_bytes",
        "sha256",
        "state",
        "attempt_count",
        "last_error_code",
        "deleted_at",
    ),
    "publication_bindings": (
        "publication_id",
        "workspace_id",
        "subject_ref",
        "state",
        "cache_state",
        "index_state",
        "published_at",
        "revoked_at",
        "purged_at",
    ),
    "lifecycle_events": (
        "event_id",
        "workspace_ref",
        "deletion_request_id",
        "action",
        "result_status",
        "object_ref",
        "created_at",
    ),
}
_TABLE_COLUMNS = (
    _CORE_TABLE_COLUMNS
    | _STRUCTURED_TABLE_COLUMNS
    | _CONSISTENCY_TABLE_COLUMNS
    | _SECURITY_TABLE_COLUMNS
    | _LIFECYCLE_TABLE_COLUMNS
)
_PRIMARY_KEYS = {
    "workspaces": ("workspace_id",),
    "access_tokens": ("token_hash",),
    "artifacts": ("artifact_id",),
    "audit_events": ("event_id",),
    "projects": ("project_id",),
    "project_metrics": ("project_id",),
    "financial_records": ("financial_record_id",),
    "artifact_versions": ("artifact_version_id",),
    "workspace_tasks": ("task_id",),
    "consistency_operations": ("operation_id",),
    "consistency_outbox": ("outbox_event_id",),
    "consistency_effect_receipts": ("dedupe_key",),
    "consistency_trace": ("trace_event_id",),
    "object_quarantine": ("quarantine_id",),
    "artifact_security_assessments": ("artifact_version_id",),
    "artifact_security_events": ("event_id",),
    "restore_drill_proofs": ("proof_id",),
    "workspace_retention": ("workspace_id",),
    "legal_holds": ("hold_id",),
    "deletion_requests": ("deletion_request_id",),
    "deletion_object_targets": (
        "deletion_request_id",
        "artifact_version_id",
    ),
    "publication_bindings": ("publication_id",),
    "lifecycle_events": ("event_id",),
}


class LegacyImportError(StructuredStoreError):
    """The read-only source or additive target verification failed."""


def _canonical_fingerprint(snapshot: dict[str, list[dict[str, Any]]]) -> str:
    payload = json.dumps(
        snapshot,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def read_legacy_snapshot(source_path: Path) -> dict[str, list[dict[str, Any]]]:
    source = source_path.expanduser().resolve()
    if not source.is_file():
        raise LegacyImportError("legacy SQLite source is unavailable")
    uri = f"file:{quote(str(source), safe='/')}?mode=ro"
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(uri, uri=True, isolation_level=None, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("BEGIN")
        available = {
            str(row["name"])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        missing = set(_CORE_TABLE_COLUMNS) - available
        if missing:
            raise LegacyImportError("legacy SQLite schema is incomplete")
        present_structured = set(_STRUCTURED_TABLE_COLUMNS) & available
        if present_structured and present_structured != set(
            _STRUCTURED_TABLE_COLUMNS
        ):
            raise LegacyImportError("legacy SQLite structured schema is partial")
        present_consistency = set(_CONSISTENCY_TABLE_COLUMNS) & available
        if present_consistency and present_consistency != set(
            _CONSISTENCY_TABLE_COLUMNS
        ):
            raise LegacyImportError("legacy SQLite consistency schema is partial")
        present_security = set(_SECURITY_TABLE_COLUMNS) & available
        if present_security and present_security != set(
            _SECURITY_TABLE_COLUMNS
        ):
            raise LegacyImportError("legacy SQLite security schema is partial")
        present_lifecycle = set(_LIFECYCLE_TABLE_COLUMNS) & available
        if present_lifecycle and present_lifecycle != set(
            _LIFECYCLE_TABLE_COLUMNS
        ):
            raise LegacyImportError("legacy SQLite lifecycle schema is partial")
        snapshot: dict[str, list[dict[str, Any]]] = {}
        selected_tables = dict(_CORE_TABLE_COLUMNS)
        if present_structured:
            selected_tables.update(_STRUCTURED_TABLE_COLUMNS)
        if present_consistency:
            selected_tables.update(_CONSISTENCY_TABLE_COLUMNS)
        if present_security:
            selected_tables.update(_SECURITY_TABLE_COLUMNS)
        if present_lifecycle:
            selected_tables.update(_LIFECYCLE_TABLE_COLUMNS)
        for table, columns in selected_tables.items():
            order_column = (
                "issuance_order"
                if table == "access_tokens"
                else (
                    "seq"
                    if table
                    in {
                        "consistency_trace",
                        "artifact_security_events",
                        "lifecycle_events",
                    }
                    else ", ".join(_PRIMARY_KEYS[table])
                )
            )
            selected_columns = list(columns)
            if table == "access_tokens":
                source_token_columns = {
                    str(row["name"])
                    for row in connection.execute(
                        "PRAGMA table_info(access_tokens)"
                    ).fetchall()
                }
                if "issuance_order" not in source_token_columns:
                    selected_columns[-1] = "rowid AS issuance_order"
            selected = ", ".join(selected_columns)
            rows = connection.execute(
                f"SELECT {selected} FROM {table} ORDER BY {order_column}"
            ).fetchall()
            snapshot[table] = [dict(row) for row in rows]
        connection.execute("COMMIT")
        return snapshot
    except LegacyImportError:
        if connection is not None and connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
    except (OSError, sqlite3.Error) as error:
        if connection is not None and connection.in_transaction:
            connection.execute("ROLLBACK")
        raise LegacyImportError("legacy SQLite read failed") from error
    finally:
        if connection is not None:
            connection.close()


def _insert_if_absent(
    connection: StructuredStoreConnection,
    *,
    table: str,
    row: dict[str, Any],
) -> None:
    columns = _TABLE_COLUMNS[table]
    primary_keys = _PRIMARY_KEYS[table]
    column_sql = ", ".join(columns)
    placeholders = ", ".join("?" for _ in columns)
    conflict_sql = ", ".join(primary_keys)
    where_sql = " AND ".join(f"{column} = ?" for column in primary_keys)
    connection.execute(
        f"""
        INSERT INTO {table}({column_sql})
        VALUES ({placeholders})
        ON CONFLICT({conflict_sql}) DO NOTHING
        """,
        tuple(row[column] for column in columns),
    )
    stored = connection.execute(
        f"SELECT {column_sql} FROM {table} WHERE {where_sql}",
        tuple(row[column] for column in primary_keys),
    ).fetchone()
    if stored is None or any(stored[column] != row[column] for column in columns):
        raise LegacyImportError("legacy import target conflict")


def _insert_access_token(
    connection: StructuredStoreConnection,
    row: dict[str, Any],
) -> None:
    expected_columns = (
        "token_hash",
        "workspace_id",
        "created_at",
        "expires_at",
    )
    stored = connection.execute(
        """
        SELECT
          token_hash, workspace_id, created_at, expires_at, issuance_order
        FROM access_tokens
        WHERE token_hash = ?
        """,
        (row["token_hash"],),
    ).fetchone()
    if stored is None:
        next_order = int(
            connection.execute(
                """
                SELECT COALESCE(MAX(issuance_order), 0) + 1 AS next_issuance_order
                FROM access_tokens
                """
            ).fetchone()["next_issuance_order"]
        )
        connection.execute(
            """
            INSERT INTO access_tokens(
              token_hash, workspace_id, created_at, expires_at, issuance_order
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                row["token_hash"],
                row["workspace_id"],
                row["created_at"],
                row["expires_at"],
                next_order,
            ),
        )
        stored = connection.execute(
            """
            SELECT
              token_hash, workspace_id, created_at, expires_at, issuance_order
            FROM access_tokens
            WHERE token_hash = ?
            """,
            (row["token_hash"],),
        ).fetchone()
    if (
        stored is None
        or int(stored["issuance_order"]) < 1
        or any(stored[column] != row[column] for column in expected_columns)
    ):
        raise LegacyImportError("legacy access-token import target conflict")


def import_legacy_sqlite(source_path: Path) -> dict[str, Any]:
    if configured_mode() != POSTGRESQL_MODE:
        raise LegacyImportError("legacy import requires PostgreSQL primary mode")
    snapshot = read_legacy_snapshot(source_path)
    connection = open_structured_store(Path("/nonexistent/kmfa-import.sqlite3"))
    try:
        with connection.transaction():
            repository = StructuredRepository(connection)
            for row in snapshot["workspaces"]:
                _insert_if_absent(
                    connection,
                    table="workspaces",
                    row=row,
                )
            if "workspace_retention" not in snapshot:
                lifecycle_repository = LifecycleRepository(connection)
                for row in snapshot["workspaces"]:
                    lifecycle_repository.ensure_workspace_retention(
                        workspace_id=str(row["workspace_id"]),
                        created_at=str(row["created_at"]),
                        updated_at=str(row["updated_at"]),
                    )
            if "projects" in snapshot:
                for row in snapshot["projects"]:
                    _insert_if_absent(connection, table="projects", row=row)
                for row in snapshot["project_metrics"]:
                    _insert_if_absent(
                        connection,
                        table="project_metrics",
                        row=row,
                    )
            else:
                for row in snapshot["workspaces"]:
                    repository.ensure_project_projection(
                        workspace_id=str(row["workspace_id"]),
                        name=str(row["project_name"]),
                        progress=int(row["progress"]),
                        created_at=str(row["created_at"]),
                        updated_at=str(row["updated_at"]),
                    )
            for row in snapshot["access_tokens"]:
                _insert_access_token(connection, row)
            for row in snapshot["artifacts"]:
                _insert_if_absent(
                    connection,
                    table="artifacts",
                    row=row,
                )
            if "artifact_versions" in snapshot:
                for row in snapshot["artifact_versions"]:
                    _insert_if_absent(
                        connection,
                        table="artifact_versions",
                        row=row,
                    )
            else:
                for row in snapshot["artifacts"]:
                    repository.ensure_artifact_version(
                        workspace_id=str(row["workspace_id"]),
                        artifact_id=str(row["artifact_id"]),
                        storage_key=str(row["object_name"]),
                        original_name=str(row["original_name"]),
                        reported_media_type=str(row["reported_media_type"]),
                        size_bytes=int(row["size_bytes"]),
                        sha256=str(row["sha256"]),
                        created_at=str(row["created_at"]),
                    )
            for table in ("financial_records", "workspace_tasks"):
                for row in snapshot.get(table, []):
                    _insert_if_absent(connection, table=table, row=row)
            for table in (
                "consistency_operations",
                "consistency_outbox",
                "consistency_effect_receipts",
                "consistency_trace",
                "object_quarantine",
            ):
                for row in snapshot.get(table, []):
                    _insert_if_absent(connection, table=table, row=row)
            for table in (
                "artifact_security_assessments",
                "artifact_security_events",
            ):
                for row in snapshot.get(table, []):
                    _insert_if_absent(connection, table=table, row=row)
            for table in (
                "restore_drill_proofs",
                "workspace_retention",
                "legal_holds",
                "deletion_requests",
                "deletion_object_targets",
                "publication_bindings",
                "lifecycle_events",
            ):
                for row in snapshot.get(table, []):
                    _insert_if_absent(connection, table=table, row=row)
            for row in snapshot["audit_events"]:
                _insert_if_absent(
                    connection,
                    table="audit_events",
                    row=row,
                )
        counts = {table: len(rows) for table, rows in snapshot.items()}
        return {
            "status": "pass",
            "mode": "additive-idempotent-read-only-source",
            "source_preserved": True,
            "target_backend": connection.backend_name,
            "schema_version": connection.schema_version(),
            "source_fixture_fingerprint": _canonical_fingerprint(snapshot),
            "row_counts": counts,
        }
    finally:
        connection.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import a quiesced KMFA legacy SQLite snapshot into PostgreSQL."
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Read-only path to walking_skeleton.sqlite3; target DSN comes from env.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        result = import_legacy_sqlite(arguments.source)
    except (LegacyImportError, StructuredStoreError):
        print(
            json.dumps(
                {
                    "status": "fail",
                    "error": "legacy_structured_import_failed",
                },
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
