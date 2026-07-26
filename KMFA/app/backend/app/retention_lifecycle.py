"""Auditable retention and explicit-deletion lifecycle for KMFA S05/P5.4.

The public application may request deletion but never receives object-delete
credentials.  A separately configured lifecycle worker revokes publication
effects, deletes the exact immutable object versions, and only then scrubs
business rows.  A passed restore drill for the current schema is a hard
precondition, so an untested deletion implementation cannot destroy the sole
copy of user state.

Default retention has no time-based transition.  Advancing the worker clock
alone is therefore incapable of deleting a workspace.
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

from .object_storage import (
    ObjectStorageError,
    ObjectStorageIntegrityError,
    ObjectStorageMissingError,
    lifecycle_store_for_backend,
)
from .structured_store import (
    SCHEMA_VERSION,
    StructuredStoreConnection,
    StructuredStoreError,
)

LIFECYCLE_MODE_ENV = "KMFA_LIFECYCLE_MODE"
LIFECYCLE_ACTIVE_MODE = "active"
LIFECYCLE_PAUSED_MODE = "paused"
LIFECYCLE_MODES = frozenset({LIFECYCLE_ACTIVE_MODE, LIFECYCLE_PAUSED_MODE})
DELETE_CONFIRMATION = "delete-workspace"
PUBLIC_PURGE_SLA = timedelta(minutes=5)
DELETION_WORKER_LEASE = timedelta(minutes=10)
RESTORE_PROOF_MAX_AGE = timedelta(days=93)
RESTORE_PROOF_FUTURE_SKEW = timedelta(minutes=5)
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
IDEMPOTENCY_RE = re.compile(r"^[A-Za-z0-9._~:+/-]{16,200}$")
HOLD_REASONS = frozenset({"legal", "security", "regulatory"})


class LifecycleError(StructuredStoreError):
    """Static, public-safe lifecycle failure."""


class LifecyclePausedError(LifecycleError):
    pass


class LifecycleConflictError(LifecycleError):
    pass


class LifecycleLegalHoldError(LifecycleError):
    pass


class RestoreProofRequiredError(LifecycleError):
    pass


class LifecycleWorkerError(LifecycleError):
    pass


class LifecycleWorkerBusyError(LifecycleWorkerError):
    pass


def lifecycle_mode() -> str:
    mode = os.environ.get(LIFECYCLE_MODE_ENV, LIFECYCLE_PAUSED_MODE).strip()
    if mode not in LIFECYCLE_MODES:
        raise LifecyclePausedError("lifecycle_mode_invalid")
    return mode


def utc_timestamp(value: datetime | None = None) -> str:
    return (
        (value or datetime.now(timezone.utc))
        .astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LifecycleError("invalid_lifecycle_timestamp") from exc
    if parsed.tzinfo is None:
        raise LifecycleError("invalid_lifecycle_timestamp")
    return parsed.astimezone(timezone.utc)


def opaque_ref(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]


def hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def deletion_request_fingerprint(
    *,
    workspace_id: str,
    confirmation: str,
    idempotency_key: str,
    workspace_secret: str,
) -> str:
    """Build a hash-only verifier for safe replay after access revocation."""

    return hash_value(
        "workspace-delete-v2"
        f"\0{workspace_id}"
        f"\0{confirmation}"
        f"\0{hash_value(idempotency_key)}"
        f"\0{hash_value(workspace_secret)}"
    )


def new_deletion_request_id() -> str:
    return f"deletion_{secrets.token_urlsafe(18)}"


def new_lifecycle_event_id() -> str:
    return f"lifecycle_{secrets.token_urlsafe(18)}"


def new_hold_id() -> str:
    return f"hold_{secrets.token_urlsafe(18)}"


@dataclass(frozen=True)
class RestoreDrillProof:
    proof_id: str
    backup_id: str
    backup_manifest_sha256: str
    source_schema_version: int
    expected_fixture_count: int
    restored_fixture_count: int
    invariant_failures: int
    measured_rpo_ms: int
    measured_rto_ms: int
    artifact_identity_hash: str
    verified_at: str


class PublicationEffects(Protocol):
    """External publication/cache/index revocation adapter."""

    def revoke_and_purge(
        self,
        *,
        publication_id: str,
        subject_ref: str,
    ) -> None: ...


class NoPublicationEffects:
    """Fail closed if a future publication exists without a real adapter."""

    def revoke_and_purge(
        self,
        *,
        publication_id: str,
        subject_ref: str,
    ) -> None:
        del publication_id, subject_ref
        raise LifecycleWorkerError("publication_adapter_unavailable")


class LifecycleRepository:
    def __init__(self, connection: StructuredStoreConnection) -> None:
        self.connection = connection

    def _event(
        self,
        *,
        workspace_id: str,
        action: str,
        result_status: str,
        timestamp: str,
        deletion_request_id: str | None = None,
        object_ref: str | None = None,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO lifecycle_events(
              event_id, workspace_ref, deletion_request_id, action,
              result_status, object_ref, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_lifecycle_event_id(),
                opaque_ref(workspace_id),
                deletion_request_id,
                action,
                result_status,
                object_ref,
                timestamp,
            ),
        )

    def ensure_workspace_retention(
        self,
        *,
        workspace_id: str,
        created_at: str,
        updated_at: str,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO workspace_retention(
              workspace_id, state, active_deletion_request_id, row_version,
              created_at, updated_at, deleted_at
            ) VALUES (?, 'active', NULL, 1, ?, ?, NULL)
            ON CONFLICT(workspace_id) DO NOTHING
            """,
            (workspace_id, created_at, updated_at),
        )
        row = self.connection.execute(
            """
            SELECT state, created_at
            FROM workspace_retention
            WHERE workspace_id = ?
            """,
            (workspace_id,),
        ).fetchone()
        if row is None or str(row["state"]) not in {
            "active",
            "deletion_requested",
            "blocked_hold",
            "purge_pending",
            "deleted",
        }:
            raise LifecycleError("workspace_retention_projection_invalid")

    def retention_state(self, workspace_id: str) -> str | None:
        row = self.connection.execute(
            "SELECT state FROM workspace_retention WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()
        return None if row is None else str(row["state"])

    def active_restore_proof(
        self,
        *,
        now: datetime | None = None,
    ) -> Any | None:
        rows = self.connection.execute(
            """
            SELECT *
            FROM restore_drill_proofs
            WHERE status = 'passed'
              AND source_schema_version = ?
              AND restored_fixture_count = expected_fixture_count
              AND invariant_failures = 0
            ORDER BY verified_at DESC, proof_id DESC
            """,
            (SCHEMA_VERSION,),
        ).fetchall()
        reference = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        for row in rows:
            try:
                verified_at = parse_timestamp(str(row["verified_at"]))
            except LifecycleError:
                continue
            age = reference - verified_at
            if (
                age >= -RESTORE_PROOF_FUTURE_SKEW
                and age <= RESTORE_PROOF_MAX_AGE
            ):
                return row
        return None

    def record_restore_proof(self, proof: RestoreDrillProof) -> None:
        if (
            not HASH_RE.fullmatch(proof.backup_manifest_sha256)
            or not HASH_RE.fullmatch(proof.artifact_identity_hash)
            or proof.source_schema_version != SCHEMA_VERSION
            or proof.expected_fixture_count <= 0
            or proof.restored_fixture_count != proof.expected_fixture_count
            or proof.invariant_failures != 0
            or proof.measured_rpo_ms < 0
            or proof.measured_rto_ms < 0
        ):
            raise LifecycleError("restore_drill_proof_failed")
        verified_at = parse_timestamp(proof.verified_at)
        age = datetime.now(timezone.utc) - verified_at
        if (
            age < -RESTORE_PROOF_FUTURE_SKEW
            or age > RESTORE_PROOF_MAX_AGE
        ):
            raise LifecycleError("restore_drill_proof_expired")
        self.connection.execute(
            """
            INSERT INTO restore_drill_proofs(
              proof_id, backup_id, backup_manifest_sha256,
              source_schema_version, expected_fixture_count,
              restored_fixture_count, invariant_failures, measured_rpo_ms,
              measured_rto_ms, artifact_identity_hash, status, verified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'passed', ?)
            ON CONFLICT(proof_id) DO NOTHING
            """,
            (
                proof.proof_id,
                proof.backup_id,
                proof.backup_manifest_sha256,
                proof.source_schema_version,
                proof.expected_fixture_count,
                proof.restored_fixture_count,
                proof.invariant_failures,
                proof.measured_rpo_ms,
                proof.measured_rto_ms,
                proof.artifact_identity_hash,
                proof.verified_at,
            ),
        )
        stored = self.connection.execute(
            "SELECT * FROM restore_drill_proofs WHERE proof_id = ?",
            (proof.proof_id,),
        ).fetchone()
        if (
            stored is None
            or str(stored["status"]) != "passed"
            or any(
                stored[field] != getattr(proof, field)
                for field in (
                    "backup_id",
                    "backup_manifest_sha256",
                    "source_schema_version",
                    "expected_fixture_count",
                    "restored_fixture_count",
                    "invariant_failures",
                    "measured_rpo_ms",
                    "measured_rto_ms",
                    "artifact_identity_hash",
                    "verified_at",
                )
            )
        ):
            raise LifecycleConflictError("restore_drill_proof_conflict")

    def impose_legal_hold(
        self,
        *,
        workspace_id: str,
        reason_code: str,
        authority_ref: str,
        timestamp: str,
        hold_id: str | None = None,
    ) -> str:
        if reason_code not in HOLD_REASONS or not authority_ref.strip():
            raise LifecycleError("invalid_legal_hold")
        retention = self.connection.execute(
            """
            SELECT active_deletion_request_id
            FROM workspace_retention
            WHERE workspace_id = ?
            """,
            (workspace_id,),
        ).fetchone()
        active_request_id = (
            None
            if retention is None
            else retention["active_deletion_request_id"]
        )
        if active_request_id is not None:
            irreversible = self.connection.execute(
                """
                SELECT 1
                FROM deletion_object_targets
                WHERE deletion_request_id = ?
                  AND state IN ('deleting', 'deleted')
                LIMIT 1
                """,
                (active_request_id,),
            ).fetchone()
            if irreversible is not None:
                raise LifecycleConflictError(
                    "legal_hold_after_irreversible_delete"
                )
        resolved_hold_id = hold_id or new_hold_id()
        self.connection.execute(
            """
            INSERT INTO legal_holds(
              hold_id, workspace_id, reason_code, authority_ref_hash,
              state, imposed_at, released_at
            ) VALUES (?, ?, ?, ?, 'active', ?, NULL)
            """,
            (
                resolved_hold_id,
                workspace_id,
                reason_code,
                hash_value(authority_ref),
                timestamp,
            ),
        )
        if active_request_id is not None:
            self.block_for_active_hold(
                deletion_request_id=str(active_request_id),
                timestamp=timestamp,
            )
        self._event(
            workspace_id=workspace_id,
            action="legal_hold_imposed",
            result_status="active",
            timestamp=timestamp,
        )
        return resolved_hold_id

    def release_legal_hold(self, *, hold_id: str, timestamp: str) -> None:
        row = self.connection.execute(
            "SELECT workspace_id, state FROM legal_holds WHERE hold_id = ?",
            (hold_id,),
        ).fetchone()
        if row is None:
            raise LifecycleError("legal_hold_not_found")
        workspace_id = str(row["workspace_id"])
        if str(row["state"]) == "active":
            self.connection.execute(
                """
                UPDATE legal_holds
                SET state = 'released', released_at = ?
                WHERE hold_id = ? AND state = 'active'
                """,
                (timestamp, hold_id),
            )
        active = self.connection.execute(
            """
            SELECT 1 FROM legal_holds
            WHERE workspace_id = ? AND state = 'active'
            LIMIT 1
            """,
            (workspace_id,),
        ).fetchone()
        if active is None:
            retention = self.connection.execute(
                """
                SELECT active_deletion_request_id, state
                FROM workspace_retention WHERE workspace_id = ?
                """,
                (workspace_id,),
            ).fetchone()
            if retention is not None and str(retention["state"]) == "blocked_hold":
                request_id = retention["active_deletion_request_id"]
                self.connection.execute(
                    """
                    UPDATE workspace_retention
                    SET state = 'deletion_requested',
                        row_version = row_version + 1,
                        updated_at = ?
                    WHERE workspace_id = ?
                    """,
                    (timestamp, workspace_id),
                )
                self.connection.execute(
                    """
                    UPDATE deletion_requests
                    SET state = 'retry', last_error_code = NULL,
                        row_version = row_version + 1, updated_at = ?
                    WHERE deletion_request_id = ?
                      AND state = 'blocked_hold'
                    """,
                    (timestamp, request_id),
                )
        self._event(
            workspace_id=workspace_id,
            action="legal_hold_released",
            result_status="released",
            timestamp=timestamp,
        )

    def _has_active_hold(self, workspace_id: str) -> bool:
        return (
            self.connection.execute(
                """
                SELECT 1 FROM legal_holds
                WHERE workspace_id = ? AND state = 'active'
                LIMIT 1
                """,
                (workspace_id,),
            ).fetchone()
            is not None
        )

    def block_for_active_hold(
        self,
        *,
        deletion_request_id: str,
        timestamp: str,
    ) -> bool:
        request = self.connection.execute(
            """
            SELECT workspace_id, state
            FROM deletion_requests
            WHERE deletion_request_id = ?
            """,
            (deletion_request_id,),
        ).fetchone()
        if request is None:
            raise LifecycleWorkerError("deletion_request_not_found")
        if str(request["state"]) == "completed":
            return False
        workspace_id = str(request["workspace_id"])
        if not self._has_active_hold(workspace_id):
            return False
        already_blocked = str(request["state"]) == "blocked_hold"
        self.connection.execute(
            """
            UPDATE deletion_requests
            SET state = 'blocked_hold', last_error_code = 'legal_hold',
                row_version = row_version + 1, updated_at = ?
            WHERE deletion_request_id = ? AND state != 'completed'
            """,
            (timestamp, deletion_request_id),
        )
        self.connection.execute(
            """
            UPDATE workspace_retention
            SET state = 'blocked_hold', row_version = row_version + 1,
                updated_at = ?
            WHERE workspace_id = ? AND state != 'deleted'
            """,
            (timestamp, workspace_id),
        )
        if not already_blocked:
            self._event(
                workspace_id=workspace_id,
                deletion_request_id=deletion_request_id,
                action="workspace_deletion_worker",
                result_status="blocked_hold",
                timestamp=timestamp,
            )
        return True

    def register_publication(
        self,
        *,
        publication_id: str,
        workspace_id: str,
        subject_identity: str,
        timestamp: str,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO publication_bindings(
              publication_id, workspace_id, subject_ref, state,
              cache_state, index_state, published_at, revoked_at, purged_at
            ) VALUES (?, ?, ?, 'active', 'active', 'active', ?, NULL, NULL)
            """,
            (
                publication_id,
                workspace_id,
                opaque_ref(subject_identity),
                timestamp,
            ),
        )

    def _deletion_targets(self, workspace_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT
              av.artifact_version_id, av.artifact_id, av.storage_backend,
              av.storage_key, av.size_bytes, av.sha256
            FROM artifact_versions av
            JOIN projects p ON p.project_id = av.project_id
            WHERE p.workspace_id = ?
            ORDER BY av.artifact_version_id
            """,
            (workspace_id,),
        ).fetchall()
        targets = [dict(row) for row in rows]
        derivatives = self.connection.execute(
            """
            SELECT
              derivative.derivative_id AS artifact_version_id,
              derivative.artifact_id,
              derivative.storage_backend,
              derivative.storage_key,
              derivative.size_bytes,
              derivative.sha256
            FROM artifact_derivatives derivative
            JOIN artifact_versions av
              ON av.artifact_version_id =
                derivative.source_artifact_version_id
            JOIN projects p ON p.project_id = av.project_id
            WHERE p.workspace_id = ?
            ORDER BY derivative.derivative_id
            """,
            (workspace_id,),
        ).fetchall()
        targets.extend(dict(row) for row in derivatives)
        known_keys = {str(row["storage_key"]) for row in targets}
        quarantined = self.connection.execute(
            """
            SELECT
              co.artifact_version_id, co.artifact_id, co.storage_backend,
              co.storage_key, co.size_bytes, co.content_sha256
            FROM consistency_operations co
            JOIN object_quarantine oq ON oq.operation_id = co.operation_id
            WHERE co.workspace_id = ?
              AND co.state = 'isolated'
              AND oq.state = 'isolated'
            ORDER BY co.operation_id
            """,
            (workspace_id,),
        ).fetchall()
        for index, row in enumerate(quarantined):
            storage_key = str(row["storage_key"])
            if storage_key in known_keys:
                continue
            if row["size_bytes"] is None or row["content_sha256"] is None:
                raise LifecycleConflictError("deletion_target_incomplete")
            targets.append(
                {
                    "artifact_version_id": (
                        str(row["artifact_version_id"])
                        if row["artifact_version_id"] is not None
                        else f"isolated_{opaque_ref(storage_key)}_{index}"
                    ),
                    "artifact_id": (
                        str(row["artifact_id"])
                        if row["artifact_id"] is not None
                        else f"isolated_{opaque_ref(storage_key)}"
                    ),
                    "storage_backend": str(row["storage_backend"]),
                    "storage_key": storage_key,
                    "size_bytes": int(row["size_bytes"]),
                    "sha256": str(row["content_sha256"]),
                }
            )
            known_keys.add(storage_key)
        return targets

    def replay_workspace_deletion(
        self,
        *,
        workspace_id: str,
        idempotency_key: str,
        request_fingerprint: str,
    ) -> Any | None:
        """Return an exact prior request without requiring a revoked session.

        The verifier binds the original high-entropy recovery capability,
        confirmation text and idempotency key, but stores none of those raw
        values. A mismatch is indistinguishable from an unknown workspace.
        """

        if IDEMPOTENCY_RE.fullmatch(idempotency_key) is None:
            raise LifecycleConflictError("invalid_idempotency_key")
        if HASH_RE.fullmatch(request_fingerprint) is None:
            raise LifecycleConflictError("workspace_not_found")
        existing = self.connection.execute(
            """
            SELECT *
            FROM deletion_requests
            WHERE workspace_id = ? AND idempotency_key_hash = ?
            """,
            (workspace_id, hash_value(idempotency_key)),
        ).fetchone()
        if existing is None:
            return None
        if str(existing["request_fingerprint"]) != request_fingerprint:
            raise LifecycleConflictError("workspace_not_found")
        return existing

    def request_workspace_deletion(
        self,
        *,
        workspace_id: str,
        idempotency_key: str,
        confirmation: str,
        request_fingerprint: str,
        deletion_request_id: str,
        timestamp: str,
    ) -> Any:
        if lifecycle_mode() != LIFECYCLE_ACTIVE_MODE:
            raise LifecyclePausedError("lifecycle_deletion_paused")
        if confirmation != DELETE_CONFIRMATION:
            raise LifecycleConflictError("deletion_confirmation_required")
        if IDEMPOTENCY_RE.fullmatch(idempotency_key) is None:
            raise LifecycleConflictError("invalid_idempotency_key")
        if HASH_RE.fullmatch(request_fingerprint) is None:
            raise LifecycleConflictError("workspace_not_found")
        key_hash = hash_value(idempotency_key)
        existing = self.connection.execute(
            """
            SELECT * FROM deletion_requests
            WHERE workspace_id = ? AND idempotency_key_hash = ?
            """,
            (workspace_id, key_hash),
        ).fetchone()
        if existing is not None:
            if str(existing["request_fingerprint"]) != request_fingerprint:
                raise LifecycleConflictError("workspace_not_found")
            return existing

        retention = self.connection.execute(
            "SELECT * FROM workspace_retention WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()
        if retention is None or str(retention["state"]) == "deleted":
            raise LifecycleConflictError("workspace_not_found")
        if retention["active_deletion_request_id"] is not None:
            raise LifecycleConflictError("deletion_already_requested")
        if self._has_active_hold(workspace_id):
            self._event(
                workspace_id=workspace_id,
                action="workspace_deletion_requested",
                result_status="blocked_hold",
                timestamp=timestamp,
            )
            raise LifecycleLegalHoldError("workspace_legal_hold")
        proof = self.active_restore_proof()
        if proof is None:
            raise RestoreProofRequiredError("deletion_restore_proof_required")
        partial = self.connection.execute(
            """
            SELECT 1 FROM consistency_operations
            WHERE workspace_id = ?
              AND state NOT IN ('converged', 'isolated')
            LIMIT 1
            """,
            (workspace_id,),
        ).fetchone()
        if partial is not None:
            raise LifecycleConflictError("deletion_consistency_pending")
        active_derivation = self.connection.execute(
            """
            SELECT 1
            FROM artifact_processing_runs
            WHERE workspace_id = ? AND state IN ('processing', 'prepared')
            LIMIT 1
            """,
            (workspace_id,),
        ).fetchone()
        if active_derivation is not None:
            raise LifecycleConflictError("deletion_consistency_pending")

        now_value = parse_timestamp(timestamp)
        purge_due = utc_timestamp(now_value + PUBLIC_PURGE_SLA)
        self.connection.execute(
            """
            INSERT INTO deletion_requests(
              deletion_request_id, workspace_id, idempotency_key_hash,
              request_fingerprint, restore_proof_id, state,
              public_purge_due_at, public_purged_at, attempt_count,
              last_error_code, row_version, requested_at, updated_at,
              completed_at
            ) VALUES (
              ?, ?, ?, ?, ?, 'requested', ?, NULL, 0, NULL, 1, ?, ?, NULL
            )
            """,
            (
                deletion_request_id,
                workspace_id,
                key_hash,
                request_fingerprint,
                proof["proof_id"],
                purge_due,
                timestamp,
                timestamp,
            ),
        )
        for target in self._deletion_targets(workspace_id):
            self.connection.execute(
                """
                INSERT INTO deletion_object_targets(
                  deletion_request_id, artifact_version_id, artifact_id,
                  storage_backend, storage_key, size_bytes, sha256, state,
                  attempt_count, last_error_code, deleted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', 0, NULL, NULL)
                """,
                (
                    deletion_request_id,
                    target["artifact_version_id"],
                    target["artifact_id"],
                    target["storage_backend"],
                    target["storage_key"],
                    target["size_bytes"],
                    target["sha256"],
                ),
            )
        self.connection.execute(
            """
            UPDATE workspace_retention
            SET state = 'deletion_requested',
                active_deletion_request_id = ?,
                row_version = row_version + 1,
                updated_at = ?
            WHERE workspace_id = ? AND state = 'active'
            """,
            (deletion_request_id, timestamp, workspace_id),
        )
        self.connection.execute(
            "DELETE FROM access_tokens WHERE workspace_id = ?",
            (workspace_id,),
        )
        self._event(
            workspace_id=workspace_id,
            deletion_request_id=deletion_request_id,
            action="workspace_deletion_requested",
            result_status="accepted",
            timestamp=timestamp,
        )
        return self.connection.execute(
            "SELECT * FROM deletion_requests WHERE deletion_request_id = ?",
            (deletion_request_id,),
        ).fetchone()

    def claim_request(self, deletion_request_id: str, *, timestamp: str) -> Any:
        request = self.connection.execute(
            "SELECT * FROM deletion_requests WHERE deletion_request_id = ?",
            (deletion_request_id,),
        ).fetchone()
        if request is None:
            raise LifecycleWorkerError("deletion_request_not_found")
        if str(request["state"]) == "completed":
            return request
        workspace_id = str(request["workspace_id"])
        if self.block_for_active_hold(
            deletion_request_id=deletion_request_id,
            timestamp=timestamp,
        ):
            return self.connection.execute(
                """
                SELECT *
                FROM deletion_requests
                WHERE deletion_request_id = ?
                """,
                (deletion_request_id,),
            ).fetchone()
        request_state = str(request["state"])
        if request_state not in {
            "requested",
            "retry",
            "blocked_hold",
            "revoking",
            "purge_pending",
        }:
            raise LifecycleWorkerError("deletion_request_state_invalid")
        if request_state in {"revoking", "purge_pending"}:
            lease_age = parse_timestamp(timestamp) - parse_timestamp(
                str(request["updated_at"])
            )
            if lease_age < DELETION_WORKER_LEASE:
                raise LifecycleWorkerBusyError(
                    "deletion_request_lease_active"
                )
        self.connection.execute(
            """
            UPDATE deletion_requests
            SET state = 'revoking', attempt_count = attempt_count + 1,
                last_error_code = NULL, row_version = row_version + 1,
                updated_at = ?
            WHERE deletion_request_id = ?
            """,
            (timestamp, deletion_request_id),
        )
        self.connection.execute(
            """
            UPDATE workspace_retention
            SET state = 'purge_pending', row_version = row_version + 1,
                updated_at = ?
            WHERE workspace_id = ?
            """,
            (timestamp, workspace_id),
        )
        return self.connection.execute(
            "SELECT * FROM deletion_requests WHERE deletion_request_id = ?",
            (deletion_request_id,),
        ).fetchone()

    def publications(self, workspace_id: str) -> list[Any]:
        return self.connection.execute(
            """
            SELECT * FROM publication_bindings
            WHERE workspace_id = ?
              AND (
                state != 'revoked'
                OR cache_state != 'purged'
                OR index_state != 'purged'
              )
            ORDER BY publication_id
            """,
            (workspace_id,),
        ).fetchall()

    def mark_publication_purged(
        self,
        *,
        deletion_request_id: str,
        publication_id: str,
        timestamp: str,
    ) -> None:
        self.connection.execute(
            """
            UPDATE publication_bindings
            SET state = 'revoked', cache_state = 'purged',
                index_state = 'purged', revoked_at = COALESCE(revoked_at, ?),
                purged_at = ?
            WHERE publication_id = ?
            """,
            (timestamp, timestamp, publication_id),
        )
        self.connection.execute(
            """
            UPDATE deletion_requests
            SET updated_at = ?, row_version = row_version + 1
            WHERE deletion_request_id = ? AND state != 'completed'
            """,
            (timestamp, deletion_request_id),
        )

    def mark_public_purge_complete(
        self,
        *,
        deletion_request_id: str,
        timestamp: str,
    ) -> bool:
        request = self.connection.execute(
            """
            SELECT workspace_id, requested_at, public_purge_due_at
            FROM deletion_requests
            WHERE deletion_request_id = ?
            """,
            (deletion_request_id,),
        ).fetchone()
        if request is None:
            raise LifecycleWorkerError("deletion_request_not_found")
        incomplete = self.connection.execute(
            """
            SELECT 1
            FROM publication_bindings
            WHERE workspace_id = ?
              AND (
                state != 'revoked'
                OR cache_state != 'purged'
                OR index_state != 'purged'
              )
            LIMIT 1
            """,
            (request["workspace_id"],),
        ).fetchone()
        if incomplete is not None:
            raise LifecycleWorkerError("public_purge_incomplete")
        purge_rows = self.connection.execute(
            """
            SELECT purged_at
            FROM publication_bindings
            WHERE workspace_id = ? AND purged_at IS NOT NULL
            """,
            (request["workspace_id"],),
        ).fetchall()
        purge_times = [
            parse_timestamp(str(row["purged_at"])) for row in purge_rows
        ]
        effective_purge = (
            max(purge_times)
            if purge_times
            else parse_timestamp(str(request["requested_at"]))
        )
        effective_timestamp = utc_timestamp(effective_purge)
        within_sla = effective_purge <= parse_timestamp(
            str(request["public_purge_due_at"])
        )
        state = "purge_pending" if within_sla else "retry"
        error_code = None if within_sla else "public_purge_sla_exceeded"
        self.connection.execute(
            """
            UPDATE deletion_requests
            SET state = ?, public_purged_at = ?,
                last_error_code = ?, row_version = row_version + 1,
                updated_at = ?
            WHERE deletion_request_id = ?
            """,
            (
                state,
                effective_timestamp,
                error_code,
                timestamp,
                deletion_request_id,
            ),
        )
        self._event(
            workspace_id=str(request["workspace_id"]),
            deletion_request_id=deletion_request_id,
            action="public_cache_index_revoked",
            result_status="purged" if within_sla else "sla_exceeded",
            timestamp=timestamp,
        )
        return within_sla

    def deletion_targets(self, deletion_request_id: str) -> list[Any]:
        return self.connection.execute(
            """
            SELECT * FROM deletion_object_targets
            WHERE deletion_request_id = ?
            ORDER BY artifact_version_id
            """,
            (deletion_request_id,),
        ).fetchall()

    def claim_target(
        self,
        *,
        deletion_request_id: str,
        artifact_version_id: str,
        timestamp: str,
    ) -> dict[str, Any] | None:
        existing = self.connection.execute(
            """
            SELECT *
            FROM deletion_object_targets
            WHERE deletion_request_id = ? AND artifact_version_id = ?
            """,
            (deletion_request_id, artifact_version_id),
        ).fetchone()
        if existing is None:
            return None
        missing_is_success = (
            str(existing["state"]) == "deleting"
            and str(existing["last_error_code"] or "")
            not in {
                "object_missing_before_delete",
                "object_integrity_unverified",
            }
        )
        self.connection.execute(
            """
            UPDATE deletion_object_targets
            SET state = 'deleting', attempt_count = attempt_count + 1,
                last_error_code = NULL
            WHERE deletion_request_id = ? AND artifact_version_id = ?
              AND state != 'deleted'
            """,
            (deletion_request_id, artifact_version_id),
        )
        self.connection.execute(
            """
            UPDATE deletion_requests
            SET updated_at = ?, row_version = row_version + 1
            WHERE deletion_request_id = ? AND state != 'completed'
            """,
            (timestamp, deletion_request_id),
        )
        claimed = self.connection.execute(
            """
            SELECT * FROM deletion_object_targets
            WHERE deletion_request_id = ? AND artifact_version_id = ?
            """,
            (deletion_request_id, artifact_version_id),
        ).fetchone()
        if claimed is None:
            return None
        result = dict(claimed)
        result["missing_is_success"] = missing_is_success
        return result

    def mark_target_retry(
        self,
        *,
        deletion_request_id: str,
        artifact_version_id: str,
        error_code: str,
    ) -> None:
        self.connection.execute(
            """
            UPDATE deletion_object_targets
            SET last_error_code = ?
            WHERE deletion_request_id = ? AND artifact_version_id = ?
              AND state != 'deleted'
            """,
            (error_code, deletion_request_id, artifact_version_id),
        )

    def mark_target_deleted(
        self,
        *,
        deletion_request_id: str,
        artifact_version_id: str,
        timestamp: str,
    ) -> None:
        request = self.connection.execute(
            "SELECT workspace_id FROM deletion_requests WHERE deletion_request_id = ?",
            (deletion_request_id,),
        ).fetchone()
        target = self.connection.execute(
            """
            SELECT storage_key FROM deletion_object_targets
            WHERE deletion_request_id = ? AND artifact_version_id = ?
            """,
            (deletion_request_id, artifact_version_id),
        ).fetchone()
        if request is None or target is None:
            raise LifecycleWorkerError("deletion_target_not_found")
        self.connection.execute(
            """
            UPDATE deletion_object_targets
            SET state = 'deleted', last_error_code = NULL, deleted_at = ?
            WHERE deletion_request_id = ? AND artifact_version_id = ?
            """,
            (timestamp, deletion_request_id, artifact_version_id),
        )
        self.connection.execute(
            """
            UPDATE deletion_requests
            SET updated_at = ?, row_version = row_version + 1
            WHERE deletion_request_id = ? AND state != 'completed'
            """,
            (timestamp, deletion_request_id),
        )
        self._event(
            workspace_id=str(request["workspace_id"]),
            deletion_request_id=deletion_request_id,
            action="object_versions_deleted",
            result_status="deleted",
            object_ref=opaque_ref(str(target["storage_key"])),
            timestamp=timestamp,
        )

    def mark_retry(
        self,
        *,
        deletion_request_id: str,
        error_code: str,
        timestamp: str,
    ) -> None:
        request = self.connection.execute(
            "SELECT workspace_id FROM deletion_requests WHERE deletion_request_id = ?",
            (deletion_request_id,),
        ).fetchone()
        if request is None:
            raise LifecycleWorkerError("deletion_request_not_found")
        self.connection.execute(
            """
            UPDATE deletion_requests
            SET state = 'retry', last_error_code = ?,
                row_version = row_version + 1, updated_at = ?
            WHERE deletion_request_id = ? AND state != 'completed'
            """,
            (error_code, timestamp, deletion_request_id),
        )
        self._event(
            workspace_id=str(request["workspace_id"]),
            deletion_request_id=deletion_request_id,
            action="workspace_deletion_worker",
            result_status="retry",
            timestamp=timestamp,
        )

    def finalize(self, deletion_request_id: str, *, timestamp: str) -> Any:
        request = self.connection.execute(
            "SELECT * FROM deletion_requests WHERE deletion_request_id = ?",
            (deletion_request_id,),
        ).fetchone()
        if request is None:
            raise LifecycleWorkerError("deletion_request_not_found")
        if str(request["state"]) == "completed":
            return request
        workspace_id = str(request["workspace_id"])
        if self._has_active_hold(workspace_id):
            raise LifecycleLegalHoldError("workspace_legal_hold")
        if str(request["state"]) != "purge_pending":
            raise LifecycleWorkerError("deletion_request_state_invalid")
        remaining_targets = self.connection.execute(
            """
            SELECT COUNT(*) AS count_value
            FROM deletion_object_targets
            WHERE deletion_request_id = ? AND state != 'deleted'
            """,
            (deletion_request_id,),
        ).fetchone()
        remaining_publications = self.connection.execute(
            """
            SELECT COUNT(*) AS count_value
            FROM publication_bindings
            WHERE workspace_id = ?
              AND (
                state != 'revoked'
                OR cache_state != 'purged'
                OR index_state != 'purged'
              )
            """,
            (workspace_id,),
        ).fetchone()
        if (
            int(remaining_targets["count_value"]) != 0
            or int(remaining_publications["count_value"]) != 0
            or request["public_purged_at"] is None
        ):
            raise LifecycleWorkerError("deletion_effects_incomplete")

        deleted_targets = self.connection.execute(
            """
            SELECT artifact_version_id, artifact_id, storage_key
            FROM deletion_object_targets
            WHERE deletion_request_id = ?
            """,
            (deletion_request_id,),
        ).fetchall()
        for target in deleted_targets:
            self.connection.execute(
                """
                UPDATE deletion_object_targets
                SET artifact_id = ?, storage_key = ?, size_bytes = 0,
                    sha256 = ?
                WHERE deletion_request_id = ?
                  AND artifact_version_id = ?
                  AND state = 'deleted'
                """,
                (
                    f"deleted_{opaque_ref(str(target['artifact_id']))}",
                    f"deleted/{opaque_ref(str(target['storage_key']))}",
                    "0" * 64,
                    deletion_request_id,
                    target["artifact_version_id"],
                ),
            )

        project = self.connection.execute(
            "SELECT project_id FROM projects WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()
        if project is not None:
            project_id = str(project["project_id"])
            self.connection.execute(
                "DELETE FROM financial_records WHERE project_id = ?",
                (project_id,),
            )
            self.connection.execute(
                "DELETE FROM workspace_tasks WHERE project_id = ?",
                (project_id,),
            )
            self.connection.execute(
                "DELETE FROM artifact_versions WHERE project_id = ?",
                (project_id,),
            )
            self.connection.execute(
                "DELETE FROM project_metrics WHERE project_id = ?",
                (project_id,),
            )
            self.connection.execute(
                "DELETE FROM projects WHERE project_id = ?",
                (project_id,),
            )
        self.connection.execute(
            "DELETE FROM artifacts WHERE workspace_id = ?",
            (workspace_id,),
        )
        self.connection.execute(
            "DELETE FROM access_tokens WHERE workspace_id = ?",
            (workspace_id,),
        )

        operations = self.connection.execute(
            """
            SELECT operation_id, storage_key
            FROM consistency_operations
            WHERE workspace_id = ?
            """,
            (workspace_id,),
        ).fetchall()
        for operation in operations:
            storage_ref = opaque_ref(str(operation["storage_key"] or "none"))
            self.connection.execute(
                """
                UPDATE consistency_operations
                SET storage_key = ?,
                    staged_object_name = CASE
                      WHEN staged_object_name IS NULL THEN NULL ELSE 'deleted.part'
                    END,
                    original_name = CASE
                      WHEN original_name IS NULL THEN NULL ELSE 'deleted'
                    END,
                    reported_media_type = CASE
                      WHEN reported_media_type IS NULL THEN NULL
                      ELSE 'application/octet-stream'
                    END,
                    size_bytes = CASE
                      WHEN size_bytes IS NULL THEN NULL ELSE 0
                    END,
                    content_sha256 = CASE
                      WHEN content_sha256 IS NULL THEN NULL ELSE ?
                    END,
                    row_version = row_version + 1,
                    updated_at = ?
                WHERE operation_id = ?
                """,
                (
                    f"deleted/{storage_ref}",
                    "0" * 64,
                    timestamp,
                    operation["operation_id"],
                ),
            )
        quarantines = self.connection.execute(
            """
            SELECT quarantine_id, storage_key
            FROM object_quarantine
            WHERE operation_id IN (
              SELECT operation_id FROM consistency_operations
              WHERE workspace_id = ?
            )
            """,
            (workspace_id,),
        ).fetchall()
        for quarantine in quarantines:
            self.connection.execute(
                """
                UPDATE object_quarantine
                SET storage_key = ?, state = 'released', last_seen_at = ?
                WHERE quarantine_id = ?
                """,
                (
                    f"deleted/{opaque_ref(str(quarantine['storage_key']))}",
                    timestamp,
                    quarantine["quarantine_id"],
                ),
            )

        tombstone_hash = hash_value(
            f"deleted-workspace-v1\0{workspace_id}\0{deletion_request_id}"
        )
        self.connection.execute(
            """
            UPDATE workspaces
            SET recovery_hash = ?, project_name = 'Deleted workspace',
                progress = 0, updated_at = ?
            WHERE workspace_id = ?
            """,
            (tombstone_hash, timestamp, workspace_id),
        )
        self.connection.execute(
            """
            UPDATE workspace_retention
            SET state = 'deleted', row_version = row_version + 1,
                updated_at = ?, deleted_at = ?
            WHERE workspace_id = ?
            """,
            (timestamp, timestamp, workspace_id),
        )
        self.connection.execute(
            """
            UPDATE deletion_requests
            SET state = 'completed', last_error_code = NULL,
                row_version = row_version + 1, updated_at = ?,
                completed_at = ?
            WHERE deletion_request_id = ?
            """,
            (timestamp, timestamp, deletion_request_id),
        )
        self._event(
            workspace_id=workspace_id,
            deletion_request_id=deletion_request_id,
            action="workspace_deletion_completed",
            result_status="deleted",
            timestamp=timestamp,
        )
        return self.connection.execute(
            "SELECT * FROM deletion_requests WHERE deletion_request_id = ?",
            (deletion_request_id,),
        ).fetchone()


def process_deletion_request(
    *,
    open_connection: Callable[[], StructuredStoreConnection],
    state_root: Path,
    deletion_request_id: str,
    publication_effects: PublicationEffects | None = None,
    now: datetime | None = None,
    clock: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    """Run one idempotent deletion attempt.

    Physical effects occur outside database transactions.  Each object target
    is moved to ``deleting`` before the effect; a missing object in that state
    is therefore an expected crash-recovery outcome, not an unexplained loss.
    """

    if lifecycle_mode() != LIFECYCLE_ACTIVE_MODE:
        raise LifecyclePausedError("lifecycle_deletion_paused")
    if now is not None and clock is not None:
        raise LifecycleWorkerError("deletion_worker_clock_ambiguous")

    def current_timestamp() -> str:
        current = (
            now
            if now is not None
            else (
                clock()
                if clock is not None
                else datetime.now(timezone.utc)
            )
        )
        if current.tzinfo is None:
            raise LifecycleWorkerError("deletion_worker_clock_invalid")
        return utc_timestamp(current)

    attempt_timestamp = current_timestamp()
    effects = publication_effects or NoPublicationEffects()
    connection = open_connection()
    claimed_artifact_version_id: str | None = None
    try:
        with connection.transaction():
            request = LifecycleRepository(connection).claim_request(
                deletion_request_id,
                timestamp=attempt_timestamp,
            )
        if str(request["state"]) == "completed":
            return dict(request)
        if str(request["state"]) == "blocked_hold":
            raise LifecycleLegalHoldError("workspace_legal_hold")
        workspace_id = str(request["workspace_id"])

        connection.close()
        connection = open_connection()
        publications = LifecycleRepository(connection).publications(workspace_id)
        connection.close()
        connection = None
        for publication in publications:
            effects.revoke_and_purge(
                publication_id=str(publication["publication_id"]),
                subject_ref=str(publication["subject_ref"]),
            )
            connection = open_connection()
            try:
                with connection.transaction():
                    LifecycleRepository(connection).mark_publication_purged(
                        deletion_request_id=deletion_request_id,
                        publication_id=str(publication["publication_id"]),
                        timestamp=current_timestamp(),
                    )
            finally:
                connection.close()
                connection = None

        connection = open_connection()
        try:
            with connection.transaction():
                purge_within_sla = LifecycleRepository(
                    connection
                ).mark_public_purge_complete(
                    deletion_request_id=deletion_request_id,
                    timestamp=current_timestamp(),
                )
            if not purge_within_sla:
                raise LifecycleWorkerError(
                    "public_purge_sla_exceeded"
                )
            targets = [
                dict(row)
                for row in LifecycleRepository(connection).deletion_targets(
                    deletion_request_id
                )
            ]
        finally:
            connection.close()
            connection = None

        for target in targets:
            if str(target["state"]) == "deleted":
                continue
            connection = open_connection()
            try:
                with connection.transaction():
                    repository = LifecycleRepository(connection)
                    target_timestamp = current_timestamp()
                    blocked_hold = repository.block_for_active_hold(
                        deletion_request_id=deletion_request_id,
                        timestamp=target_timestamp,
                    )
                    if blocked_hold:
                        claimed = None
                    else:
                        claimed_artifact_version_id = str(
                            target["artifact_version_id"]
                        )
                        claimed = repository.claim_target(
                            deletion_request_id=deletion_request_id,
                            artifact_version_id=claimed_artifact_version_id,
                            timestamp=target_timestamp,
                        )
                        if claimed is None:
                            raise LifecycleWorkerError(
                                "deletion_target_not_found"
                            )
                        claimed = dict(claimed)
            finally:
                connection.close()
                connection = None
            if blocked_hold:
                raise LifecycleLegalHoldError("workspace_legal_hold")
            assert claimed is not None
            store = lifecycle_store_for_backend(
                state_root,
                str(claimed["storage_backend"]),
            )
            store.delete_all_versions(
                storage_key=str(claimed["storage_key"]),
                expected_size=int(claimed["size_bytes"]),
                expected_sha256=str(claimed["sha256"]),
                artifact_id=str(claimed["artifact_id"]),
                artifact_version_id=str(claimed["artifact_version_id"]),
                missing_is_success=bool(claimed["missing_is_success"]),
            )
            connection = open_connection()
            try:
                with connection.transaction():
                    LifecycleRepository(connection).mark_target_deleted(
                        deletion_request_id=deletion_request_id,
                        artifact_version_id=str(claimed["artifact_version_id"]),
                        timestamp=current_timestamp(),
                    )
            finally:
                connection.close()
                connection = None

        connection = open_connection()
        try:
            with connection.transaction():
                repository = LifecycleRepository(connection)
                finalize_timestamp = current_timestamp()
                blocked_hold = repository.block_for_active_hold(
                    deletion_request_id=deletion_request_id,
                    timestamp=finalize_timestamp,
                )
                completed = (
                    None
                    if blocked_hold
                    else repository.finalize(
                        deletion_request_id,
                        timestamp=finalize_timestamp,
                    )
                )
            if blocked_hold:
                raise LifecycleLegalHoldError("workspace_legal_hold")
            assert completed is not None
            return dict(completed)
        finally:
            connection.close()
            connection = None
    except LifecycleLegalHoldError:
        raise
    except LifecycleWorkerBusyError:
        raise
    except (LifecycleError, ObjectStorageError, OSError) as error:
        if connection is not None:
            connection.close()
            connection = None
        if str(error) == "public_purge_sla_exceeded":
            raise LifecycleWorkerError(
                "public_purge_sla_exceeded"
            ) from error
        retry_connection = open_connection()
        try:
            with retry_connection.transaction():
                repository = LifecycleRepository(retry_connection)
                if claimed_artifact_version_id is not None:
                    target_error_code = "object_effect_retryable"
                    if isinstance(error, ObjectStorageMissingError):
                        target_error_code = "object_missing_before_delete"
                    elif isinstance(error, ObjectStorageIntegrityError):
                        target_error_code = "object_integrity_unverified"
                    repository.mark_target_retry(
                        deletion_request_id=deletion_request_id,
                        artifact_version_id=claimed_artifact_version_id,
                        error_code=target_error_code,
                    )
                repository.mark_retry(
                    deletion_request_id=deletion_request_id,
                    error_code="deletion_effect_retryable",
                    timestamp=current_timestamp(),
                )
        finally:
            retry_connection.close()
        raise LifecycleWorkerError("deletion_effect_retryable")
    finally:
        if connection is not None:
            connection.close()


def due_deletion_request_ids(
    connection: StructuredStoreConnection,
    *,
    limit: int,
    now: datetime | None = None,
) -> list[str]:
    if limit < 1 or limit > 1000:
        raise LifecycleError("invalid_deletion_worker_limit")
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        raise LifecycleError("invalid_deletion_worker_clock")
    stale_before = utc_timestamp(
        reference.astimezone(timezone.utc) - DELETION_WORKER_LEASE
    )
    rows = connection.execute(
        """
        SELECT deletion_request_id
        FROM deletion_requests
        WHERE state = 'requested'
           OR (
             state = 'retry'
             AND COALESCE(last_error_code, '') !=
               'public_purge_sla_exceeded'
           )
           OR (
             state IN ('revoking', 'purge_pending')
             AND updated_at <= ?
           )
        ORDER BY requested_at, deletion_request_id
        LIMIT ?
        """,
        (stale_before, limit),
    ).fetchall()
    return [str(row["deletion_request_id"]) for row in rows]
