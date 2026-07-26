"""Portable full + logical-incremental backup and isolated restore for P5.4.

Backups are private directories with a checksum-closed manifest, database row
deltas, and deduplicated verified object blobs. Incrementals contain only
changed rows, row tombstones, new object versions, and object tombstones.
Restoring a chain reconstructs its final target point in an empty database and
empty object prefix; old full-backup bytes are never implicitly resurrected.

The bundle is intentionally provider-neutral. Production policy must replicate
the completed private directory to an independently controlled encrypted
destination; a same-host directory alone is not claimed as disaster recovery.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from .object_storage import (
    LEGACY_FILESYSTEM_MODE,
    LEGACY_STORAGE_BACKEND,
    S3_COMPATIBLE_MODE,
    S3_STORAGE_BACKEND,
    FilesystemObjectStore,
    ObjectStorageError,
    S3ObjectStore,
    content_md5_base64,
    lifecycle_store_for_backend,
    object_store_for_backend,
)
from .retention_lifecycle import (
    LIFECYCLE_PAUSED_MODE,
    LifecycleRepository,
    RestoreDrillProof,
    lifecycle_mode,
    parse_timestamp,
    utc_timestamp,
)
from .structured_store import (
    SCHEMA_VERSION,
    StructuredStoreConnection,
    StructuredStoreError,
    open_structured_store,
)

BACKUP_FORMAT = "kmfa-private-logical-backup-v1"
DATABASE_DELTA_FORMAT = "kmfa-private-logical-delta-v1"
BACKUP_ID_RE = re.compile(r"^backup_[A-Za-z0-9_-]{12,80}$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class BackupRestoreError(StructuredStoreError):
    """Static, credential-free backup or restore failure."""


@dataclass(frozen=True)
class TableSpec:
    name: str
    columns: tuple[str, ...]
    key_columns: tuple[str, ...]


TABLES: tuple[TableSpec, ...] = (
    TableSpec(
        "workspaces",
        (
            "workspace_id",
            "recovery_hash",
            "project_name",
            "progress",
            "created_at",
            "updated_at",
        ),
        ("workspace_id",),
    ),
    TableSpec(
        "restore_drill_proofs",
        (
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
        ("proof_id",),
    ),
    TableSpec(
        "workspace_retention",
        (
            "workspace_id",
            "state",
            "active_deletion_request_id",
            "row_version",
            "created_at",
            "updated_at",
            "deleted_at",
        ),
        ("workspace_id",),
    ),
    TableSpec(
        "legal_holds",
        (
            "hold_id",
            "workspace_id",
            "reason_code",
            "authority_ref_hash",
            "state",
            "imposed_at",
            "released_at",
        ),
        ("hold_id",),
    ),
    TableSpec(
        "projects",
        (
            "project_id",
            "workspace_id",
            "name",
            "lifecycle_state",
            "row_version",
            "created_at",
            "updated_at",
        ),
        ("project_id",),
    ),
    TableSpec(
        "project_metrics",
        ("project_id", "progress", "score", "row_version", "updated_at"),
        ("project_id",),
    ),
    TableSpec(
        "financial_records",
        (
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
        ("financial_record_id",),
    ),
    TableSpec(
        "workspace_tasks",
        (
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
        ("task_id",),
    ),
    TableSpec(
        "artifacts",
        (
            "artifact_id",
            "workspace_id",
            "object_name",
            "original_name",
            "reported_media_type",
            "size_bytes",
            "sha256",
            "created_at",
        ),
        ("artifact_id",),
    ),
    TableSpec(
        "artifact_versions",
        (
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
        ("artifact_version_id",),
    ),
    TableSpec(
        "access_tokens",
        (
            "token_hash",
            "workspace_id",
            "created_at",
            "expires_at",
            "issuance_order",
        ),
        ("token_hash",),
    ),
    TableSpec(
        "audit_events",
        (
            "seq",
            "event_id",
            "workspace_id",
            "action",
            "result_status",
            "artifact_sha256",
            "created_at",
        ),
        ("event_id",),
    ),
    TableSpec(
        "consistency_operations",
        (
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
        ("operation_id",),
    ),
    TableSpec(
        "consistency_outbox",
        (
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
        ("outbox_event_id",),
    ),
    TableSpec(
        "consistency_effect_receipts",
        (
            "dedupe_key",
            "operation_id",
            "effect_kind",
            "receipt_hash",
            "applied_at",
        ),
        ("dedupe_key",),
    ),
    TableSpec(
        "consistency_trace",
        (
            "seq",
            "trace_event_id",
            "operation_id",
            "from_state",
            "to_state",
            "transition_code",
            "error_code",
            "created_at",
        ),
        ("trace_event_id",),
    ),
    TableSpec(
        "object_quarantine",
        (
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
        ("quarantine_id",),
    ),
    TableSpec(
        "deletion_requests",
        (
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
        ("deletion_request_id",),
    ),
    TableSpec(
        "deletion_object_targets",
        (
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
        ("deletion_request_id", "artifact_version_id"),
    ),
    TableSpec(
        "publication_bindings",
        (
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
        ("publication_id",),
    ),
    TableSpec(
        "lifecycle_events",
        (
            "seq",
            "event_id",
            "workspace_ref",
            "deletion_request_id",
            "action",
            "result_status",
            "object_ref",
            "created_at",
        ),
        ("event_id",),
    ),
)
TABLE_BY_NAME = {table.name: table for table in TABLES}


@dataclass(frozen=True)
class BackupResult:
    backup_id: str
    kind: str
    directory: Path
    manifest_sha256: str
    recovery_point_at: str
    duration_ms: int
    table_upserts: int
    table_deletes: int
    object_upserts: int
    object_deletes: int


@dataclass(frozen=True)
class RestoreResult:
    backup_id: str
    manifest_sha256: str
    restored_rows: int
    restored_objects: int
    invariant_failures: int
    measured_rpo_ms: int
    measured_rto_ms: int
    artifact_identity_hash: str


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_private(path: Path, value: bytes) -> None:
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(value)
            output.flush()
            os.fsync(output.fileno())
    except Exception:
        raise


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _row_key(spec: TableSpec, row: dict[str, Any]) -> str:
    return json.dumps(
        [row[column] for column in spec.key_columns],
        ensure_ascii=True,
        separators=(",", ":"),
    )


def _snapshot_database(
    connection: StructuredStoreConnection,
) -> dict[str, list[dict[str, Any]]]:
    snapshot: dict[str, list[dict[str, Any]]] = {}
    for spec in TABLES:
        selected = ", ".join(spec.columns)
        ordered = ", ".join(spec.key_columns)
        rows = connection.execute(
            f"SELECT {selected} FROM {spec.name} ORDER BY {ordered}"
        ).fetchall()
        snapshot[spec.name] = [dict(row) for row in rows]
    return snapshot


def _object_index(
    snapshot: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in snapshot["artifact_versions"]:
        if str(row["lifecycle_state"]) == "missing":
            raise BackupRestoreError("backup_object_missing")
        entry = {
            "storage_backend": str(row["storage_backend"]),
            "storage_key": str(row["storage_key"]),
            "size_bytes": int(row["size_bytes"]),
            "sha256": str(row["sha256"]),
            "artifact_id": str(row["artifact_id"]),
            "artifact_version_id": str(row["artifact_version_id"]),
        }
        identity = f"{entry['storage_backend']}\0{entry['storage_key']}"
        if identity in result and result[identity] != entry:
            raise BackupRestoreError("backup_duplicate_object_identity")
        result[identity] = entry
    operations = {
        str(row["operation_id"]): row
        for row in snapshot["consistency_operations"]
    }
    for quarantine in snapshot["object_quarantine"]:
        if str(quarantine["state"]) != "isolated":
            continue
        operation_id = quarantine["operation_id"]
        operation = operations.get(str(operation_id))
        if operation is None:
            raise BackupRestoreError("backup_quarantine_operation_missing")
        required = (
            "storage_backend",
            "storage_key",
            "size_bytes",
            "content_sha256",
            "artifact_id",
            "artifact_version_id",
        )
        if any(operation[field] is None for field in required):
            raise BackupRestoreError("backup_quarantine_object_incomplete")
        entry = {
            "storage_backend": str(operation["storage_backend"]),
            "storage_key": str(operation["storage_key"]),
            "size_bytes": int(operation["size_bytes"]),
            "sha256": str(operation["content_sha256"]),
            "artifact_id": str(operation["artifact_id"]),
            "artifact_version_id": str(operation["artifact_version_id"]),
        }
        identity = f"{entry['storage_backend']}\0{entry['storage_key']}"
        if identity in result and result[identity] != entry:
            raise BackupRestoreError("backup_duplicate_object_identity")
        result[identity] = entry
    return result


def _prepare_new_backup_directory(
    directory: Path,
    *,
    state_root: Path,
) -> Path:
    expanded = directory.expanduser()
    if expanded.is_symlink():
        raise BackupRestoreError("backup_destination_symlink")
    resolved = expanded.resolve()
    state = state_root.expanduser().resolve()
    if resolved == state or state in resolved.parents or resolved in state.parents:
        raise BackupRestoreError("backup_destination_not_independent")
    if resolved.exists():
        raise BackupRestoreError("backup_destination_must_be_new")
    resolved.mkdir(mode=0o700, parents=False)
    resolved.chmod(0o700)
    (resolved / "objects").mkdir(mode=0o700)
    return resolved


def _read_bundle(directory: Path) -> tuple[dict[str, Any], dict[str, Any], str]:
    expanded = directory.expanduser()
    if expanded.is_symlink():
        raise BackupRestoreError("backup_bundle_unavailable")
    resolved = expanded.resolve()
    if not resolved.is_dir() or resolved.is_symlink():
        raise BackupRestoreError("backup_bundle_unavailable")
    objects_path = resolved / "objects"
    if not objects_path.is_dir() or objects_path.is_symlink():
        raise BackupRestoreError("backup_bundle_incomplete")
    manifest_path = resolved / "manifest.json"
    delta_path = resolved / "database-delta.json"
    complete_path = resolved / "COMPLETE"
    if not all(
        path.is_file() and not path.is_symlink()
        for path in (manifest_path, delta_path, complete_path)
    ):
        raise BackupRestoreError("backup_bundle_incomplete")
    manifest_bytes = manifest_path.read_bytes()
    manifest_hash = _sha256_bytes(manifest_bytes)
    if complete_path.read_text(encoding="ascii").strip() != manifest_hash:
        raise BackupRestoreError("backup_manifest_checksum_mismatch")
    try:
        manifest = json.loads(manifest_bytes)
        delta = json.loads(delta_path.read_bytes())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BackupRestoreError("backup_bundle_invalid") from exc
    if (
        manifest.get("format") != BACKUP_FORMAT
        or delta.get("format") != DATABASE_DELTA_FORMAT
        or manifest.get("source_schema_version") != SCHEMA_VERSION
        or _sha256_file(delta_path) != manifest.get("database_delta_sha256")
    ):
        raise BackupRestoreError("backup_bundle_invalid")
    return manifest, delta, manifest_hash


def _load_chain(
    directories: Sequence[Path],
) -> list[tuple[Path, dict[str, Any], dict[str, Any], str]]:
    if not directories:
        raise BackupRestoreError("backup_chain_required")
    chain: list[tuple[Path, dict[str, Any], dict[str, Any], str]] = []
    previous_manifest: dict[str, Any] | None = None
    previous_hash: str | None = None
    for index, directory in enumerate(directories):
        manifest, delta, manifest_hash = _read_bundle(directory)
        resolved = directory.expanduser().resolve()
        expected_kind = "full" if index == 0 else "incremental"
        if manifest.get("kind") != expected_kind:
            raise BackupRestoreError("backup_chain_kind_invalid")
        if index == 0:
            if (
                manifest.get("parent_backup_id") is not None
                or manifest.get("parent_manifest_sha256") is not None
            ):
                raise BackupRestoreError("backup_chain_parent_invalid")
        else:
            assert previous_manifest is not None and previous_hash is not None
            if (
                manifest.get("parent_backup_id")
                != previous_manifest.get("backup_id")
                or manifest.get("parent_manifest_sha256") != previous_hash
            ):
                raise BackupRestoreError("backup_chain_parent_invalid")
        chain.append((resolved, manifest, delta, manifest_hash))
        previous_manifest = manifest
        previous_hash = manifest_hash
    return chain


def _reconstruct_tables(
    chain: Sequence[tuple[Path, dict[str, Any], dict[str, Any], str]],
) -> dict[str, dict[str, dict[str, Any]]]:
    state = {spec.name: {} for spec in TABLES}
    for _, _, delta, _ in chain:
        upserts = delta.get("table_upserts")
        deletes = delta.get("table_deletes")
        if set(upserts or {}) != set(TABLE_BY_NAME) or set(deletes or {}) != set(
            TABLE_BY_NAME
        ):
            raise BackupRestoreError("backup_database_delta_invalid")
        for spec in TABLES:
            for key in deletes[spec.name]:
                if not isinstance(key, list) or len(key) != len(spec.key_columns):
                    raise BackupRestoreError("backup_database_delta_invalid")
                encoded = json.dumps(key, ensure_ascii=True, separators=(",", ":"))
                state[spec.name].pop(encoded, None)
            for row in upserts[spec.name]:
                if set(row) != set(spec.columns):
                    raise BackupRestoreError("backup_database_delta_invalid")
                state[spec.name][_row_key(spec, row)] = row
    return state


def _reconstruct_objects(
    chain: Sequence[tuple[Path, dict[str, Any], dict[str, Any], str]],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for _, manifest, _, _ in chain:
        object_deletes = manifest.get("object_deletes")
        object_upserts = manifest.get("object_upserts")
        if not isinstance(object_deletes, list) or not isinstance(
            object_upserts, list
        ):
            raise BackupRestoreError("backup_object_manifest_invalid")
        for identity in object_deletes:
            if not isinstance(identity, str) or "\0" not in identity:
                raise BackupRestoreError("backup_object_manifest_invalid")
            result.pop(str(identity), None)
        for entry in object_upserts:
            required = {
                "identity",
                "storage_backend",
                "storage_key",
                "size_bytes",
                "sha256",
                "artifact_id",
                "artifact_version_id",
                "blob_sha256",
            }
            if not isinstance(entry, dict) or set(entry) != required:
                raise BackupRestoreError("backup_object_manifest_invalid")
            identity = str(entry["identity"])
            storage_backend = str(entry["storage_backend"])
            storage_key = str(entry["storage_key"])
            sha256 = str(entry["sha256"])
            blob_sha256 = str(entry["blob_sha256"])
            try:
                size_bytes = int(entry["size_bytes"])
            except (TypeError, ValueError) as exc:
                raise BackupRestoreError(
                    "backup_object_manifest_invalid"
                ) from exc
            if (
                storage_backend
                not in {LEGACY_STORAGE_BACKEND, S3_STORAGE_BACKEND}
                or not storage_key
                or identity != f"{storage_backend}\0{storage_key}"
                or size_bytes < 0
                or not HASH_RE.fullmatch(sha256)
                or blob_sha256 != sha256
                or not str(entry["artifact_id"])
                or not str(entry["artifact_version_id"])
            ):
                raise BackupRestoreError("backup_object_manifest_invalid")
            result[identity] = dict(entry)
    return result


def _assert_reconstructed_counts(
    manifest: dict[str, Any],
    tables: dict[str, dict[str, dict[str, Any]]],
    objects: dict[str, dict[str, Any]],
) -> None:
    try:
        expected_rows = int(manifest["final_row_count"])
        expected_objects = int(manifest["final_object_count"])
    except (KeyError, TypeError, ValueError) as exc:
        raise BackupRestoreError("backup_manifest_count_invalid") from exc
    if (
        expected_rows < 0
        or expected_objects < 0
        or sum(len(rows) for rows in tables.values()) != expected_rows
        or len(objects) != expected_objects
    ):
        raise BackupRestoreError("backup_manifest_count_invalid")


def _copy_verified_object(
    *,
    state_root: Path,
    backup_directory: Path,
    entry: dict[str, Any],
) -> str:
    store = object_store_for_backend(
        state_root,
        str(entry["storage_backend"]),
    )
    materialized = store.materialize_verified(
        storage_key=str(entry["storage_key"]),
        expected_size=int(entry["size_bytes"]),
        expected_sha256=str(entry["sha256"]),
    )
    blob_hash = str(entry["sha256"])
    target = backup_directory / "objects" / f"{blob_hash}.blob"
    try:
        if target.exists():
            if _sha256_file(target) != blob_hash:
                raise BackupRestoreError("backup_blob_collision")
        else:
            descriptor = os.open(
                target,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )
            with materialized.path.open("rb") as source, os.fdopen(
                descriptor, "wb"
            ) as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
                output.flush()
                os.fsync(output.fileno())
            if _sha256_file(target) != blob_hash:
                raise BackupRestoreError("backup_object_checksum_mismatch")
    finally:
        if materialized.temporary:
            materialized.path.unlink(missing_ok=True)
    return blob_hash


def create_backup(
    *,
    connection: StructuredStoreConnection,
    state_root: Path,
    destination: Path,
    kind: str,
    parent_chain: Sequence[Path] = (),
    artifact_identity: str,
    backup_id: str | None = None,
    now: datetime | None = None,
) -> BackupResult:
    if (
        lifecycle_mode() != LIFECYCLE_PAUSED_MODE
        or os.environ.get("KMFA_CONSISTENCY_STATE_MODE", "").strip()
        != "paused"
    ):
        raise BackupRestoreError("backup_requires_quiesced_writes")
    if kind not in {"full", "incremental"}:
        raise BackupRestoreError("backup_kind_invalid")
    if (kind == "full" and parent_chain) or (
        kind == "incremental" and not parent_chain
    ):
        raise BackupRestoreError("backup_parent_chain_invalid")
    resolved_backup_id = backup_id or f"backup_{secrets.token_urlsafe(18)}"
    if BACKUP_ID_RE.fullmatch(resolved_backup_id) is None:
        raise BackupRestoreError("backup_id_invalid")
    if not artifact_identity.strip():
        raise BackupRestoreError("artifact_identity_required")
    started = time.monotonic()
    started_at = utc_timestamp(now)
    parent = _load_chain(parent_chain) if parent_chain else []
    parent_tables = _reconstruct_tables(parent) if parent else {
        spec.name: {} for spec in TABLES
    }
    parent_objects = _reconstruct_objects(parent) if parent else {}
    if parent:
        _assert_reconstructed_counts(
            parent[-1][1],
            parent_tables,
            parent_objects,
        )

    with connection.transaction():
        if connection.schema_version() != SCHEMA_VERSION:
            raise BackupRestoreError("backup_schema_version_mismatch")
        pending_consistency = connection.execute(
            """
            SELECT 1
            FROM consistency_operations
            WHERE state NOT IN ('converged', 'isolated')
            LIMIT 1
            """
        ).fetchone()
        if pending_consistency is not None:
            raise BackupRestoreError(
                "backup_consistency_operations_pending"
            )
        current_snapshot = _snapshot_database(connection)
        recovery_point_at = utc_timestamp(now)
    directory = _prepare_new_backup_directory(
        destination,
        state_root=state_root,
    )
    current_objects = _object_index(current_snapshot)

    table_upserts: dict[str, list[dict[str, Any]]] = {}
    table_deletes: dict[str, list[list[Any]]] = {}
    for spec in TABLES:
        current_by_key = {
            _row_key(spec, row): row for row in current_snapshot[spec.name]
        }
        previous_by_key = parent_tables[spec.name]
        table_upserts[spec.name] = [
            row
            for key, row in sorted(current_by_key.items())
            if previous_by_key.get(key) != row
        ]
        table_deletes[spec.name] = [
            json.loads(key)
            for key in sorted(set(previous_by_key) - set(current_by_key))
        ]

    object_upserts: list[dict[str, Any]] = []
    for identity, entry in sorted(current_objects.items()):
        previous = parent_objects.get(identity)
        comparable = {
            key: previous.get(key)
            for key in (
                "storage_backend",
                "storage_key",
                "size_bytes",
                "sha256",
                "artifact_id",
                "artifact_version_id",
            )
        } if previous else None
        if comparable == entry:
            continue
        blob_hash = _copy_verified_object(
            state_root=state_root,
            backup_directory=directory,
            entry=entry,
        )
        object_upserts.append(
            {
                "identity": identity,
                **entry,
                "blob_sha256": blob_hash,
            }
        )
    object_deletes = sorted(set(parent_objects) - set(current_objects))

    delta = {
        "format": DATABASE_DELTA_FORMAT,
        "table_upserts": table_upserts,
        "table_deletes": table_deletes,
    }
    delta_bytes = _canonical_bytes(delta)
    delta_path = directory / "database-delta.json"
    _write_private(delta_path, delta_bytes)
    duration_ms = max(0, round((time.monotonic() - started) * 1000))
    parent_manifest = parent[-1][1] if parent else None
    parent_hash = parent[-1][3] if parent else None
    manifest = {
        "format": BACKUP_FORMAT,
        "backup_id": resolved_backup_id,
        "kind": kind,
        "parent_backup_id": (
            parent_manifest["backup_id"] if parent_manifest else None
        ),
        "parent_manifest_sha256": parent_hash,
        "source_schema_version": SCHEMA_VERSION,
        "source_backend": connection.backend_name,
        "artifact_identity_hash": _sha256_bytes(
            artifact_identity.encode("utf-8")
        ),
        "created_at": started_at,
        "recovery_point_at": recovery_point_at,
        "duration_ms": duration_ms,
        "database_delta_sha256": _sha256_bytes(delta_bytes),
        "table_upsert_count": sum(len(rows) for rows in table_upserts.values()),
        "table_delete_count": sum(len(rows) for rows in table_deletes.values()),
        "object_upserts": object_upserts,
        "object_deletes": object_deletes,
        "final_row_count": sum(len(rows) for rows in current_snapshot.values()),
        "final_object_count": len(current_objects),
        "default_auto_expiry": False,
    }
    manifest_bytes = _canonical_bytes(manifest)
    manifest_hash = _sha256_bytes(manifest_bytes)
    _write_private(directory / "manifest.json", manifest_bytes)
    _write_private(directory / "COMPLETE", (manifest_hash + "\n").encode("ascii"))
    _fsync_directory(directory / "objects")
    _fsync_directory(directory)
    return BackupResult(
        backup_id=resolved_backup_id,
        kind=kind,
        directory=directory,
        manifest_sha256=manifest_hash,
        recovery_point_at=recovery_point_at,
        duration_ms=duration_ms,
        table_upserts=int(manifest["table_upsert_count"]),
        table_deletes=int(manifest["table_delete_count"]),
        object_upserts=len(object_upserts),
        object_deletes=len(object_deletes),
    )


def _locate_blob(
    chain: Sequence[tuple[Path, dict[str, Any], dict[str, Any], str]],
    blob_sha256: str,
) -> Path:
    for directory, _, _, _ in reversed(chain):
        objects_directory = directory / "objects"
        if objects_directory.is_symlink():
            raise BackupRestoreError("backup_bundle_incomplete")
        candidate = objects_directory / f"{blob_sha256}.blob"
        if candidate.is_symlink():
            raise BackupRestoreError("backup_object_blob_invalid")
        if candidate.is_file():
            if _sha256_file(candidate) != blob_sha256:
                raise BackupRestoreError("backup_object_checksum_mismatch")
            return candidate
    raise BackupRestoreError("backup_object_blob_missing")


def _assert_empty_destination(
    connection: StructuredStoreConnection,
    *,
    state_root: Path,
    backends: Iterable[str],
) -> None:
    for spec in TABLES:
        count = connection.execute(
            f"SELECT COUNT(*) AS count_value FROM {spec.name}"
        ).fetchone()
        if int(count["count_value"]) != 0:
            raise BackupRestoreError("restore_database_not_empty")
    checked_backends = {LEGACY_STORAGE_BACKEND, *backends}
    configured_mode = os.environ.get(
        "KMFA_ARTIFACT_STORAGE_MODE",
        LEGACY_FILESYSTEM_MODE,
    ).strip()
    if configured_mode == S3_COMPATIBLE_MODE:
        checked_backends.add(S3_STORAGE_BACKEND)
    elif configured_mode != LEGACY_FILESYSTEM_MODE:
        raise BackupRestoreError("restore_object_backend_invalid")
    for backend in checked_backends:
        store = object_store_for_backend(state_root, backend)
        store.ensure_ready()
        if isinstance(store, FilesystemObjectStore):
            if any(store.objects_dir.iterdir()):
                raise BackupRestoreError("restore_object_target_not_empty")
        elif isinstance(store, S3ObjectStore):
            # Current-object inventory is insufficient for a versioned bucket:
            # a delete marker can hide historical bytes. The separately
            # credentialed lifecycle adapter must prove the entire private
            # prefix contains no versions before an isolated restore starts.
            version_store = lifecycle_store_for_backend(
                state_root,
                S3_STORAGE_BACKEND,
            )
            if (
                not isinstance(version_store, S3ObjectStore)
                or version_store.provider_version_count() != 0
            ):
                raise BackupRestoreError("restore_object_target_not_empty")
        else:
            raise BackupRestoreError("restore_object_backend_invalid")


def _restore_object(
    *,
    chain: Sequence[tuple[Path, dict[str, Any], dict[str, Any], str]],
    state_root: Path,
    entry: dict[str, Any],
) -> None:
    blob = _locate_blob(chain, str(entry["blob_sha256"]))
    tmp = state_root / "tmp"
    tmp.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp.chmod(0o700)
    staging = tmp / f"restore-{secrets.token_urlsafe(24)}.part"
    descriptor = os.open(staging, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with blob.open("rb") as source, os.fdopen(descriptor, "wb") as output:
            digest = hashlib.sha256()
            size = 0
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                digest.update(chunk)
                size += len(chunk)
            output.flush()
            os.fsync(output.fileno())
        if (
            size != int(entry["size_bytes"])
            or digest.hexdigest() != str(entry["sha256"])
        ):
            raise BackupRestoreError("backup_object_checksum_mismatch")
        md5 = hashlib.md5(usedforsecurity=False)
        with staging.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                md5.update(chunk)
        store = object_store_for_backend(
            state_root,
            str(entry["storage_backend"]),
        )
        store.put_file(
            staging,
            storage_key=str(entry["storage_key"]),
            size_bytes=int(entry["size_bytes"]),
            sha256=str(entry["sha256"]),
            content_md5=content_md5_base64(md5),
            artifact_id=str(entry["artifact_id"]),
            artifact_version_id=str(entry["artifact_version_id"]),
        )
    finally:
        staging.unlink(missing_ok=True)


def _insert_row(
    connection: StructuredStoreConnection,
    spec: TableSpec,
    row: dict[str, Any],
) -> None:
    columns = ", ".join(spec.columns)
    placeholders = ", ".join("?" for _ in spec.columns)
    connection.execute(
        f"INSERT INTO {spec.name}({columns}) VALUES ({placeholders})",
        tuple(row[column] for column in spec.columns),
    )


def _reset_sequences(connection: StructuredStoreConnection) -> None:
    if connection.backend_name.startswith("sqlite"):
        return
    for table, column in (
        ("audit_events", "seq"),
        ("consistency_trace", "seq"),
        ("lifecycle_events", "seq"),
    ):
        connection.execute(
            f"""
            SELECT setval(
              pg_get_serial_sequence('{table}', '{column}'),
              COALESCE(MAX({column}), 1),
              MAX({column}) IS NOT NULL
            )
            FROM {table}
            """
        )


def restore_backup(
    *,
    connection: StructuredStoreConnection,
    state_root: Path,
    chain_directories: Sequence[Path],
    incident_at: datetime,
) -> RestoreResult:
    if (
        lifecycle_mode() != LIFECYCLE_PAUSED_MODE
        or os.environ.get("KMFA_CONSISTENCY_STATE_MODE", "").strip()
        != "paused"
    ):
        raise BackupRestoreError("restore_requires_quiesced_target")
    if incident_at.tzinfo is None:
        raise BackupRestoreError("backup_incident_timestamp_invalid")
    started = time.monotonic()
    chain = _load_chain(chain_directories)
    tables = _reconstruct_tables(chain)
    objects = _reconstruct_objects(chain)
    final_manifest = chain[-1][1]
    final_hash = chain[-1][3]
    recovery_point = parse_timestamp(str(final_manifest["recovery_point_at"]))
    normalized_incident = incident_at.astimezone(timezone.utc)
    if normalized_incident < recovery_point:
        raise BackupRestoreError(
            "backup_incident_before_recovery_point"
        )
    _assert_reconstructed_counts(final_manifest, tables, objects)
    # Browser sessions are derived, revocable capabilities rather than durable
    # user data. Restoring them could resurrect a token revoked after the
    # recovery point. Preserve the high-entropy workspace recovery verifier but
    # require every browser/device to establish a fresh post-restore session.
    tables["access_tokens"] = {}
    chain_backends = {
        str(entry["storage_backend"])
        for _, manifest, _, _ in chain
        for entry in manifest["object_upserts"]
    }
    _assert_empty_destination(
        connection,
        state_root=state_root,
        backends=chain_backends,
    )
    for _, entry in sorted(objects.items()):
        _restore_object(chain=chain, state_root=state_root, entry=entry)

    with connection.transaction():
        for spec in TABLES:
            rows = tables[spec.name]
            for key in sorted(rows):
                _insert_row(connection, spec, rows[key])
        # A proof copied from another environment cannot authorize deletion in
        # this recovered environment. A new application-level drill records a
        # fresh passed proof only after all recovery Oracles succeed.
        connection.execute(
            "UPDATE restore_drill_proofs SET status = 'failed'"
        )
        _reset_sequences(connection)

    invariant_failures = 0
    restored_rows = 0
    for spec in TABLES:
        expected = len(tables[spec.name])
        actual = int(
            connection.execute(
                f"SELECT COUNT(*) AS count_value FROM {spec.name}"
            ).fetchone()["count_value"]
        )
        restored_rows += actual
        invariant_failures += int(actual != expected)
    for entry in objects.values():
        try:
            materialized = object_store_for_backend(
                state_root,
                str(entry["storage_backend"]),
            ).materialize_verified(
                storage_key=str(entry["storage_key"]),
                expected_size=int(entry["size_bytes"]),
                expected_sha256=str(entry["sha256"]),
            )
            if materialized.temporary:
                materialized.path.unlink(missing_ok=True)
        except (ObjectStorageError, OSError):
            invariant_failures += 1
    retention_count = int(
        connection.execute(
            "SELECT COUNT(*) AS count_value FROM workspace_retention"
        ).fetchone()["count_value"]
    )
    workspace_count = int(
        connection.execute(
            "SELECT COUNT(*) AS count_value FROM workspaces"
        ).fetchone()["count_value"]
    )
    invariant_failures += int(retention_count != workspace_count)
    invariant_failures += int(
        bool(
            connection.execute(
                """
                SELECT 1 FROM workspace_retention
                WHERE deleted_at IS NULL AND state = 'deleted'
                LIMIT 1
                """
            ).fetchone()
        )
    )
    rto_ms = max(0, round((time.monotonic() - started) * 1000))
    rpo_ms = round(
        (normalized_incident - recovery_point).total_seconds() * 1000
    )
    return RestoreResult(
        backup_id=str(final_manifest["backup_id"]),
        manifest_sha256=final_hash,
        restored_rows=restored_rows,
        restored_objects=len(objects),
        invariant_failures=invariant_failures,
        measured_rpo_ms=rpo_ms,
        measured_rto_ms=rto_ms,
        artifact_identity_hash=str(final_manifest["artifact_identity_hash"]),
    )


def _state_root() -> Path:
    explicit = os.environ.get("KMFA_WALKING_SKELETON_STATE_DIR", "").strip()
    if explicit:
        return Path(explicit)
    return Path(
        os.environ.get("KMFA_APP_STATE_DIR", "/var/lib/kmfa/state")
    ) / "walking-skeleton"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    backup = subparsers.add_parser("backup")
    backup.add_argument("--destination", type=Path, required=True)
    backup.add_argument("--kind", choices=("full", "incremental"), required=True)
    backup.add_argument("--parent", type=Path, action="append", default=[])
    backup.add_argument("--artifact-identity", required=True)
    backup.add_argument("--backup-id")
    restore = subparsers.add_parser("restore")
    restore.add_argument("--chain", type=Path, action="append", required=True)
    restore.add_argument("--incident-at", required=True)
    proof = subparsers.add_parser("record-proof")
    proof.add_argument("--backup-id", required=True)
    proof.add_argument("--manifest-sha256", required=True)
    proof.add_argument("--expected-fixtures", type=int, required=True)
    proof.add_argument("--restored-fixtures", type=int, required=True)
    proof.add_argument("--invariant-failures", type=int, required=True)
    proof.add_argument("--measured-rpo-ms", type=int, required=True)
    proof.add_argument("--measured-rto-ms", type=int, required=True)
    proof.add_argument("--artifact-identity-hash", required=True)
    proof.add_argument("--proof-id")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    state_root = _state_root()
    state_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    connection = open_structured_store(
        state_root / "walking_skeleton.sqlite3"
    )
    try:
        if arguments.command == "backup":
            result = create_backup(
                connection=connection,
                state_root=state_root,
                destination=arguments.destination,
                kind=arguments.kind,
                parent_chain=arguments.parent,
                artifact_identity=arguments.artifact_identity,
                backup_id=arguments.backup_id,
            )
            payload = {
                "status": "pass",
                "backup_id": result.backup_id,
                "kind": result.kind,
                "manifest_sha256": result.manifest_sha256,
                "recovery_point_at": result.recovery_point_at,
                "duration_ms": result.duration_ms,
                "table_upserts": result.table_upserts,
                "table_deletes": result.table_deletes,
                "object_upserts": result.object_upserts,
                "object_deletes": result.object_deletes,
            }
        elif arguments.command == "restore":
            incident_at = parse_timestamp(arguments.incident_at)
            result = restore_backup(
                connection=connection,
                state_root=state_root,
                chain_directories=arguments.chain,
                incident_at=incident_at,
            )
            payload = {
                "status": (
                    "pass" if result.invariant_failures == 0 else "fail"
                ),
                "backup_id": result.backup_id,
                "manifest_sha256": result.manifest_sha256,
                "restored_rows": result.restored_rows,
                "restored_objects": result.restored_objects,
                "invariant_failures": result.invariant_failures,
                "measured_rpo_ms": result.measured_rpo_ms,
                "measured_rto_ms": result.measured_rto_ms,
                "artifact_identity_hash": result.artifact_identity_hash,
            }
        else:
            if (
                lifecycle_mode() != LIFECYCLE_PAUSED_MODE
                or os.environ.get("KMFA_CONSISTENCY_STATE_MODE", "").strip()
                != "paused"
                or BACKUP_ID_RE.fullmatch(arguments.backup_id) is None
            ):
                raise BackupRestoreError("restore_proof_requires_quiesced_state")
            proof_id = arguments.proof_id or (
                f"proof_{secrets.token_urlsafe(18)}"
            )
            proof = RestoreDrillProof(
                proof_id=proof_id,
                backup_id=arguments.backup_id,
                backup_manifest_sha256=arguments.manifest_sha256,
                source_schema_version=SCHEMA_VERSION,
                expected_fixture_count=arguments.expected_fixtures,
                restored_fixture_count=arguments.restored_fixtures,
                invariant_failures=arguments.invariant_failures,
                measured_rpo_ms=arguments.measured_rpo_ms,
                measured_rto_ms=arguments.measured_rto_ms,
                artifact_identity_hash=arguments.artifact_identity_hash,
                verified_at=utc_timestamp(),
            )
            with connection.transaction():
                LifecycleRepository(connection).record_restore_proof(proof)
            payload = {
                "status": "pass",
                "proof_id": proof_id,
                "backup_id": arguments.backup_id,
                "source_schema_version": SCHEMA_VERSION,
                "expected_fixtures": arguments.expected_fixtures,
                "restored_fixtures": arguments.restored_fixtures,
                "invariant_failures": arguments.invariant_failures,
                "measured_rpo_ms": arguments.measured_rpo_ms,
                "measured_rto_ms": arguments.measured_rto_ms,
            }
    except (BackupRestoreError, StructuredStoreError, ObjectStorageError):
        print(
            json.dumps(
                {"status": "fail", "error": "backup_restore_failed"},
                sort_keys=True,
            )
        )
        return 1
    finally:
        connection.close()
    print(json.dumps(payload, sort_keys=True))
    return int(payload["status"] != "pass")


if __name__ == "__main__":
    raise SystemExit(main())
