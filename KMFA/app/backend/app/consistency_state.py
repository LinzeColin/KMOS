"""Recoverable cross-system workflow state for KMFA S05/P5.3.

The database records intent before a non-transactional side effect, records the
observed result, then commits domain rows and an outbox event together.  A
retry may therefore inspect and resume every partial state without deleting a
raw object.  Outbox delivery is at-least-once; consumers must apply the
provided ``dedupe_key`` atomically with their own side effect.

Only hashes of caller-provided idempotency keys are persisted.  Reconciliation
reports use opaque operation/object references and fixed error codes so they
can be retained as public-safe test evidence.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .structured_store import StructuredStoreConnection, StructuredStoreError

OPERATION_KINDS = frozenset({"upload", "process", "index", "export"})
EFFECT_KINDS = frozenset((*OPERATION_KINDS, "notify"))
TERMINAL_OPERATION_STATES = frozenset({"converged", "isolated"})
TERMINAL_OUTBOX_STATES = frozenset({"delivered", "isolated"})
OPERATION_STATES = frozenset(
    {
        "intent_recorded",
        "effect_pending",
        "effect_applied",
        "commit_pending",
        "outbox_committed",
        *TERMINAL_OPERATION_STATES,
    }
)
OUTBOX_STATES = frozenset(
    {"pending", "leased", "retry", *TERMINAL_OUTBOX_STATES}
)
ALLOWED_TRANSITIONS = {
    "intent_recorded": frozenset({"effect_pending", "isolated"}),
    "effect_pending": frozenset({"effect_applied", "isolated"}),
    "effect_applied": frozenset({"commit_pending", "isolated"}),
    "commit_pending": frozenset({"outbox_committed", "isolated"}),
    "outbox_committed": frozenset({"converged", "isolated"}),
    "converged": frozenset(),
    "isolated": frozenset(),
}
IDEMPOTENCY_KEY_RE = re.compile(r"^[A-Za-z0-9._~-]{16,128}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ERROR_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{2,80}$")
INTERNAL_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,180}$")


class ConsistencyStateError(StructuredStoreError):
    """A fixed, non-sensitive consistency contract failure."""


class ConsistencyConflictError(ConsistencyStateError):
    """An idempotency key was reused for a different request."""


class ConsistencyTransitionError(ConsistencyStateError):
    """A caller attempted a transition outside the sealed state graph."""


@dataclass(frozen=True)
class UploadIntent:
    workspace_id: str
    idempotency_key: str
    request_fingerprint: str
    artifact_id: str
    artifact_version_id: str
    storage_backend: str
    storage_key: str
    staged_object_name: str
    original_name: str
    reported_media_type: str
    size_bytes: int
    content_sha256: str
    artifact_version_number: int = 1


@dataclass(frozen=True)
class OperationIdentity:
    operation_id: str
    created: bool


@dataclass(frozen=True)
class ClaimedOutboxEvent:
    outbox_event_id: str
    operation_id: str
    effect_kind: str
    dedupe_key: str
    attempt_count: int


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(18)}"


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def opaque_operation_ref(operation_id: str) -> str:
    return _sha256_text(operation_id)[:20]


def opaque_object_ref(storage_key: str) -> str:
    return _sha256_text(storage_key)[:20]


def idempotency_key_hash(value: str) -> str:
    if IDEMPOTENCY_KEY_RE.fullmatch(value) is None:
        raise ConsistencyStateError("invalid_idempotency_key")
    return _sha256_text(value)


def upload_request_fingerprint(
    *,
    workspace_id: str,
    original_name: str,
    reported_media_type: str,
    size_bytes: int,
    content_sha256: str,
) -> str:
    if not SHA256_RE.fullmatch(content_sha256) or size_bytes < 0:
        raise ConsistencyStateError("invalid_request_fingerprint")
    encoded = json.dumps(
        {
            "content_sha256": content_sha256,
            "operation_kind": "upload",
            "original_name": original_name,
            "reported_media_type": reported_media_type,
            "size_bytes": size_bytes,
            "workspace_id": workspace_id,
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return _sha256_text(encoded)


def _validate_hash(value: str, *, code: str) -> None:
    if SHA256_RE.fullmatch(value) is None:
        raise ConsistencyStateError(code)


def _validate_error_code(value: str | None) -> None:
    if value is not None and ERROR_CODE_RE.fullmatch(value) is None:
        raise ConsistencyStateError("invalid_consistency_error_code")


def _row_matches(row: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    return all(row[key] == value for key, value in expected.items())


class ConsistencyRepository:
    """SQL persistence for operations, outbox delivery and reconciliation."""

    def __init__(self, connection: StructuredStoreConnection) -> None:
        self.connection = connection

    def operation(self, operation_id: str) -> Any | None:
        return self.connection.execute(
            """
            SELECT *
            FROM consistency_operations
            WHERE operation_id = ?
            """,
            (operation_id,),
        ).fetchone()

    def operation_for_idempotency(
        self,
        *,
        workspace_id: str,
        operation_kind: str,
        idempotency_key_hash_value: str,
    ) -> Any | None:
        return self.connection.execute(
            """
            SELECT *
            FROM consistency_operations
            WHERE workspace_id = ?
              AND operation_kind = ?
              AND idempotency_key_hash = ?
            """,
            (workspace_id, operation_kind, idempotency_key_hash_value),
        ).fetchone()

    def _append_trace(
        self,
        *,
        operation_id: str,
        from_state: str | None,
        to_state: str,
        transition_code: str,
        timestamp: str,
        error_code: str | None = None,
    ) -> None:
        _validate_error_code(error_code)
        self.connection.execute(
            """
            INSERT INTO consistency_trace(
              trace_event_id, operation_id, from_state, to_state,
              transition_code, error_code, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _new_id("trace"),
                operation_id,
                from_state,
                to_state,
                transition_code,
                error_code,
                timestamp,
            ),
        )

    def create_or_load_upload(
        self,
        intent: UploadIntent,
        *,
        operation_id: str,
        timestamp: str,
    ) -> OperationIdentity:
        key_hash = idempotency_key_hash(intent.idempotency_key)
        _validate_hash(
            intent.request_fingerprint,
            code="invalid_request_fingerprint",
        )
        _validate_hash(intent.content_sha256, code="invalid_content_sha256")
        if (
            not operation_id
            or INTERNAL_NAME_RE.fullmatch(intent.staged_object_name) is None
            or intent.size_bytes < 0
            or intent.artifact_version_number < 1
        ):
            raise ConsistencyStateError("invalid_upload_intent")

        existing = self.operation_for_idempotency(
            workspace_id=intent.workspace_id,
            operation_kind="upload",
            idempotency_key_hash_value=key_hash,
        )
        if existing is not None:
            self._verify_upload_replay(existing, intent, key_hash)
            return OperationIdentity(str(existing["operation_id"]), False)

        inserted = self.connection.execute(
            """
            INSERT INTO consistency_operations(
              operation_id, workspace_id, operation_kind,
              idempotency_key_hash, request_fingerprint, artifact_id,
              artifact_version_id, storage_backend, storage_key,
              staged_object_name, original_name, reported_media_type,
              size_bytes, content_sha256, artifact_version_number,
              state, attempt_count,
              next_attempt_at, last_error_code, row_version, created_at,
              updated_at
            ) VALUES (
              ?, ?, 'upload', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
              'intent_recorded', 0, NULL, NULL, 1, ?, ?
            )
            ON CONFLICT(workspace_id, operation_kind, idempotency_key_hash)
            DO NOTHING
            """,
            (
                operation_id,
                intent.workspace_id,
                key_hash,
                intent.request_fingerprint,
                intent.artifact_id,
                intent.artifact_version_id,
                intent.storage_backend,
                intent.storage_key,
                intent.staged_object_name,
                intent.original_name,
                intent.reported_media_type,
                intent.size_bytes,
                intent.content_sha256,
                intent.artifact_version_number,
                timestamp,
                timestamp,
            ),
        )
        stored = self.operation_for_idempotency(
            workspace_id=intent.workspace_id,
            operation_kind="upload",
            idempotency_key_hash_value=key_hash,
        )
        if stored is None:
            raise ConsistencyStateError("consistency_intent_not_persisted")
        self._verify_upload_replay(stored, intent, key_hash)
        created = inserted.rowcount == 1
        if created:
            self._append_trace(
                operation_id=operation_id,
                from_state=None,
                to_state="intent_recorded",
                transition_code="intent_persisted",
                timestamp=timestamp,
            )
        return OperationIdentity(str(stored["operation_id"]), created)

    @staticmethod
    def _verify_upload_replay(
        row: Mapping[str, Any],
        intent: UploadIntent,
        key_hash: str,
    ) -> None:
        expected = {
            "workspace_id": intent.workspace_id,
            "operation_kind": "upload",
            "idempotency_key_hash": key_hash,
            "request_fingerprint": intent.request_fingerprint,
            "artifact_id": intent.artifact_id,
            "artifact_version_id": intent.artifact_version_id,
            "artifact_version_number": intent.artifact_version_number,
            "storage_backend": intent.storage_backend,
            "storage_key": intent.storage_key,
            "staged_object_name": intent.staged_object_name,
            "original_name": intent.original_name,
            "reported_media_type": intent.reported_media_type,
            "size_bytes": intent.size_bytes,
            "content_sha256": intent.content_sha256,
        }
        # A replay resolves identity from the stored operation. Callers may have
        # generated throw-away IDs/keys before learning that the key exists, so
        # only request identity is compared here; persisted side-effect identity
        # remains authoritative.
        replay_expected = {
            key: value
            for key, value in expected.items()
            if key
            in {
                "workspace_id",
                "operation_kind",
                "idempotency_key_hash",
                "request_fingerprint",
                "original_name",
                "reported_media_type",
                "size_bytes",
                "content_sha256",
            }
        }
        if not _row_matches(row, replay_expected):
            raise ConsistencyConflictError("idempotency_key_conflict")

    def create_generic_operation(
        self,
        *,
        operation_id: str,
        workspace_id: str,
        operation_kind: str,
        idempotency_key: str,
        request_fingerprint: str,
        timestamp: str,
    ) -> OperationIdentity:
        if operation_kind not in OPERATION_KINDS or operation_kind == "upload":
            raise ConsistencyStateError("invalid_operation_kind")
        key_hash = idempotency_key_hash(idempotency_key)
        _validate_hash(request_fingerprint, code="invalid_request_fingerprint")
        inserted = self.connection.execute(
            """
            INSERT INTO consistency_operations(
              operation_id, workspace_id, operation_kind,
              idempotency_key_hash, request_fingerprint, state,
              attempt_count, row_version, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'intent_recorded', 0, 1, ?, ?)
            ON CONFLICT(workspace_id, operation_kind, idempotency_key_hash)
            DO NOTHING
            """,
            (
                operation_id,
                workspace_id,
                operation_kind,
                key_hash,
                request_fingerprint,
                timestamp,
                timestamp,
            ),
        )
        stored = self.operation_for_idempotency(
            workspace_id=workspace_id,
            operation_kind=operation_kind,
            idempotency_key_hash_value=key_hash,
        )
        if stored is None:
            raise ConsistencyStateError("consistency_intent_not_persisted")
        if str(stored["request_fingerprint"]) != request_fingerprint:
            raise ConsistencyConflictError("idempotency_key_conflict")
        created = inserted.rowcount == 1
        if created:
            self._append_trace(
                operation_id=operation_id,
                from_state=None,
                to_state="intent_recorded",
                transition_code="intent_persisted",
                timestamp=timestamp,
            )
        return OperationIdentity(str(stored["operation_id"]), created)

    def transition(
        self,
        operation_id: str,
        *,
        expected_state: str,
        to_state: str,
        transition_code: str,
        timestamp: str,
        error_code: str | None = None,
        increment_attempt: bool = False,
        next_attempt_at: str | None = None,
    ) -> Any:
        if expected_state not in OPERATION_STATES or to_state not in OPERATION_STATES:
            raise ConsistencyTransitionError("unknown_consistency_state")
        if to_state not in ALLOWED_TRANSITIONS[expected_state]:
            raise ConsistencyTransitionError("invalid_consistency_transition")
        _validate_error_code(error_code)
        updated = self.connection.execute(
            """
            UPDATE consistency_operations
            SET
              state = ?,
              attempt_count = attempt_count + ?,
              next_attempt_at = ?,
              last_error_code = ?,
              row_version = row_version + 1,
              updated_at = ?
            WHERE operation_id = ? AND state = ?
            """,
            (
                to_state,
                1 if increment_attempt else 0,
                next_attempt_at,
                error_code,
                timestamp,
                operation_id,
                expected_state,
            ),
        )
        if updated.rowcount != 1:
            current = self.operation(operation_id)
            if current is not None and str(current["state"]) == to_state:
                return current
            raise ConsistencyTransitionError("consistency_state_conflict")
        self._append_trace(
            operation_id=operation_id,
            from_state=expected_state,
            to_state=to_state,
            transition_code=transition_code,
            timestamp=timestamp,
            error_code=error_code,
        )
        current = self.operation(operation_id)
        if current is None:
            raise ConsistencyStateError("consistency_operation_missing")
        return current

    def record_attempt_failure(
        self,
        operation_id: str,
        *,
        expected_state: str,
        error_code: str,
        timestamp: str,
        next_attempt_at: str | None = None,
    ) -> Any:
        """Record a retryable failure without inventing a state transition."""

        if expected_state not in OPERATION_STATES:
            raise ConsistencyTransitionError("unknown_consistency_state")
        _validate_error_code(error_code)
        updated = self.connection.execute(
            """
            UPDATE consistency_operations
            SET
              attempt_count = attempt_count + 1,
              next_attempt_at = ?,
              last_error_code = ?,
              row_version = row_version + 1,
              updated_at = ?
            WHERE operation_id = ? AND state = ?
            """,
            (
                next_attempt_at,
                error_code,
                timestamp,
                operation_id,
                expected_state,
            ),
        )
        if updated.rowcount != 1:
            raise ConsistencyTransitionError("consistency_state_conflict")
        self._append_trace(
            operation_id=operation_id,
            from_state=expected_state,
            to_state=expected_state,
            transition_code="retry_scheduled",
            timestamp=timestamp,
            error_code=error_code,
        )
        current = self.operation(operation_id)
        if current is None:
            raise ConsistencyStateError("consistency_operation_missing")
        return current

    def isolate(
        self,
        operation_id: str,
        *,
        expected_state: str,
        error_code: str,
        timestamp: str,
    ) -> Any:
        return self.transition(
            operation_id,
            expected_state=expected_state,
            to_state="isolated",
            transition_code="operation_isolated",
            timestamp=timestamp,
            error_code=error_code,
        )

    def ensure_outbox(
        self,
        *,
        operation_id: str,
        effect_kind: str,
        timestamp: str,
    ) -> Any:
        if effect_kind not in EFFECT_KINDS:
            raise ConsistencyStateError("invalid_effect_kind")
        dedupe_key = _sha256_text(
            f"kmfa-consistency-v1:{operation_id}:{effect_kind}"
        )
        event_id = _new_id("outbox")
        self.connection.execute(
            """
            INSERT INTO consistency_outbox(
              outbox_event_id, operation_id, effect_kind, dedupe_key,
              state, attempt_count, available_at, lease_until,
              last_error_code, created_at, updated_at
            ) VALUES (
              ?, ?, ?, ?, 'pending', 0, ?, NULL, NULL, ?, ?
            )
            ON CONFLICT(operation_id, effect_kind) DO NOTHING
            """,
            (
                event_id,
                operation_id,
                effect_kind,
                dedupe_key,
                timestamp,
                timestamp,
                timestamp,
            ),
        )
        stored = self.connection.execute(
            """
            SELECT *
            FROM consistency_outbox
            WHERE operation_id = ? AND effect_kind = ?
            """,
            (operation_id, effect_kind),
        ).fetchone()
        if (
            stored is None
            or str(stored["dedupe_key"]) != dedupe_key
            or str(stored["state"]) not in OUTBOX_STATES
        ):
            raise ConsistencyStateError("outbox_persistence_conflict")
        return stored

    def claim_outbox(
        self,
        *,
        now: str,
        lease_until: str,
        effect_kinds: Iterable[str] | None = None,
    ) -> ClaimedOutboxEvent | None:
        selected = tuple(sorted(set(effect_kinds or EFFECT_KINDS)))
        if not selected or any(kind not in EFFECT_KINDS for kind in selected):
            raise ConsistencyStateError("invalid_effect_kind")
        placeholders = ", ".join("?" for _ in selected)
        row = self.connection.execute(
            f"""
            SELECT *
            FROM consistency_outbox
            WHERE effect_kind IN ({placeholders})
              AND (
                (state IN ('pending', 'retry') AND available_at <= ?)
                OR (state = 'leased' AND lease_until <= ?)
              )
            ORDER BY available_at, outbox_event_id
            LIMIT 1
            """,
            (*selected, now, now),
        ).fetchone()
        if row is None:
            return None
        updated = self.connection.execute(
            """
            UPDATE consistency_outbox
            SET state = 'leased',
                attempt_count = attempt_count + 1,
                lease_until = ?,
                last_error_code = NULL,
                updated_at = ?
            WHERE outbox_event_id = ?
              AND (
                (state IN ('pending', 'retry') AND available_at <= ?)
                OR (state = 'leased' AND lease_until <= ?)
              )
            """,
            (
                lease_until,
                now,
                row["outbox_event_id"],
                now,
                now,
            ),
        )
        if updated.rowcount != 1:
            return None
        claimed = self.connection.execute(
            """
            SELECT *
            FROM consistency_outbox
            WHERE outbox_event_id = ?
            """,
            (row["outbox_event_id"],),
        ).fetchone()
        if claimed is None:
            raise ConsistencyStateError("outbox_claim_missing")
        return ClaimedOutboxEvent(
            outbox_event_id=str(claimed["outbox_event_id"]),
            operation_id=str(claimed["operation_id"]),
            effect_kind=str(claimed["effect_kind"]),
            dedupe_key=str(claimed["dedupe_key"]),
            attempt_count=int(claimed["attempt_count"]),
        )

    def effect_receipt(self, dedupe_key: str) -> Any | None:
        return self.connection.execute(
            """
            SELECT *
            FROM consistency_effect_receipts
            WHERE dedupe_key = ?
            """,
            (dedupe_key,),
        ).fetchone()

    def record_effect_receipt(
        self,
        event: ClaimedOutboxEvent,
        *,
        receipt_hash: str,
        timestamp: str,
    ) -> None:
        _validate_hash(receipt_hash, code="invalid_effect_receipt")
        self.connection.execute(
            """
            INSERT INTO consistency_effect_receipts(
              dedupe_key, operation_id, effect_kind, receipt_hash, applied_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(dedupe_key) DO NOTHING
            """,
            (
                event.dedupe_key,
                event.operation_id,
                event.effect_kind,
                receipt_hash,
                timestamp,
            ),
        )
        stored = self.effect_receipt(event.dedupe_key)
        expected = {
            "operation_id": event.operation_id,
            "effect_kind": event.effect_kind,
            "receipt_hash": receipt_hash,
        }
        if stored is None or not _row_matches(stored, expected):
            raise ConsistencyConflictError("effect_receipt_conflict")

    def acknowledge_outbox(
        self,
        event: ClaimedOutboxEvent,
        *,
        timestamp: str,
    ) -> None:
        if self.effect_receipt(event.dedupe_key) is None:
            raise ConsistencyStateError("effect_receipt_required")
        updated = self.connection.execute(
            """
            UPDATE consistency_outbox
            SET state = 'delivered',
                lease_until = NULL,
                last_error_code = NULL,
                updated_at = ?
            WHERE outbox_event_id = ?
              AND dedupe_key = ?
              AND state = 'leased'
            """,
            (timestamp, event.outbox_event_id, event.dedupe_key),
        )
        if updated.rowcount != 1:
            row = self.connection.execute(
                """
                SELECT state
                FROM consistency_outbox
                WHERE outbox_event_id = ? AND dedupe_key = ?
                """,
                (event.outbox_event_id, event.dedupe_key),
            ).fetchone()
            if row is None or str(row["state"]) != "delivered":
                raise ConsistencyTransitionError("outbox_state_conflict")

    def retry_outbox(
        self,
        event: ClaimedOutboxEvent,
        *,
        available_at: str,
        error_code: str,
        timestamp: str,
    ) -> None:
        _validate_error_code(error_code)
        updated = self.connection.execute(
            """
            UPDATE consistency_outbox
            SET state = 'retry',
                available_at = ?,
                lease_until = NULL,
                last_error_code = ?,
                updated_at = ?
            WHERE outbox_event_id = ?
              AND state = 'leased'
              AND attempt_count = ?
            """,
            (
                available_at,
                error_code,
                timestamp,
                event.outbox_event_id,
                event.attempt_count,
            ),
        )
        if updated.rowcount != 1:
            raise ConsistencyTransitionError("outbox_state_conflict")

    def isolate_outbox(
        self,
        event: ClaimedOutboxEvent,
        *,
        error_code: str,
        timestamp: str,
    ) -> None:
        _validate_error_code(error_code)
        updated = self.connection.execute(
            """
            UPDATE consistency_outbox
            SET state = 'isolated',
                lease_until = NULL,
                last_error_code = ?,
                updated_at = ?
            WHERE outbox_event_id = ?
              AND state = 'leased'
              AND attempt_count = ?
            """,
            (
                error_code,
                timestamp,
                event.outbox_event_id,
                event.attempt_count,
            ),
        )
        if updated.rowcount != 1:
            raise ConsistencyTransitionError("outbox_state_conflict")

    def quarantine_object(
        self,
        *,
        operation_id: str | None,
        storage_backend: str,
        storage_key: str,
        reason_code: str,
        timestamp: str,
    ) -> str:
        _validate_error_code(reason_code)
        object_ref = opaque_object_ref(storage_key)
        quarantine_id = _new_id("quarantine")
        self.connection.execute(
            """
            INSERT INTO object_quarantine(
              quarantine_id, operation_id, storage_backend, storage_key,
              object_ref, reason_code, state, first_seen_at, last_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'isolated', ?, ?)
            ON CONFLICT(storage_backend, storage_key, reason_code)
            DO UPDATE SET
              last_seen_at = excluded.last_seen_at
            """,
            (
                quarantine_id,
                operation_id,
                storage_backend,
                storage_key,
                object_ref,
                reason_code,
                timestamp,
                timestamp,
            ),
        )
        return object_ref

    def trace(self, operation_id: str) -> list[Any]:
        return self.connection.execute(
            """
            SELECT
              from_state, to_state, transition_code, error_code, created_at
            FROM consistency_trace
            WHERE operation_id = ?
            ORDER BY seq
            """,
            (operation_id,),
        ).fetchall()

    def reconciliation_report(self) -> dict[str, Any]:
        operations = self.connection.execute(
            """
            SELECT operation_id, operation_kind, state, last_error_code
            FROM consistency_operations
            ORDER BY operation_id
            """
        ).fetchall()
        outbox = self.connection.execute(
            """
            SELECT
              outbox_event_id, operation_id, effect_kind, state,
              last_error_code
            FROM consistency_outbox
            ORDER BY outbox_event_id
            """
        ).fetchall()
        trace_rows = self.connection.execute(
            """
            SELECT
              operation_id, from_state, to_state, transition_code
            FROM consistency_trace
            ORDER BY operation_id, seq
            """
        ).fetchall()
        traces_by_operation: dict[str, list[Any]] = {}
        for trace_row in trace_rows:
            traces_by_operation.setdefault(
                str(trace_row["operation_id"]), []
            ).append(trace_row)
        operation_counts = Counter(str(row["state"]) for row in operations)
        outbox_counts = Counter(str(row["state"]) for row in outbox)
        unexplained_operations = [
            row
            for row in operations
            if (
                str(row["state"]) == "isolated"
                and not row["last_error_code"]
            )
            or str(row["state"]) not in OPERATION_STATES
        ]
        unexplained_outbox = [
            row
            for row in outbox
            if (
                str(row["state"]) == "isolated"
                and not row["last_error_code"]
            )
            or str(row["state"]) not in OUTBOX_STATES
        ]
        delivered_without_receipt = int(
            self.connection.execute(
                """
                SELECT COUNT(*) AS count_value
                FROM consistency_outbox o
                LEFT JOIN consistency_effect_receipts r
                  ON r.dedupe_key = o.dedupe_key
                WHERE o.state = 'delivered' AND r.dedupe_key IS NULL
                """
            ).fetchone()["count_value"]
        )
        converged_without_outbox = int(
            self.connection.execute(
                """
                SELECT COUNT(*) AS count_value
                FROM consistency_operations operation
                LEFT JOIN consistency_outbox outbox
                  ON outbox.operation_id = operation.operation_id
                WHERE operation.state = 'converged'
                  AND outbox.outbox_event_id IS NULL
                """
            ).fetchone()["count_value"]
        )
        invalid_trace_refs: list[str] = []
        invalid_terminal_trace_count = 0
        for operation in operations:
            operation_id = str(operation["operation_id"])
            operation_traces = traces_by_operation.get(operation_id, [])
            current_state: str | None = None
            valid = bool(operation_traces)
            for index, trace_row in enumerate(operation_traces):
                from_state = trace_row["from_state"]
                to_state = str(trace_row["to_state"])
                transition_code = str(trace_row["transition_code"])
                if index == 0:
                    if from_state is not None or to_state != "intent_recorded":
                        valid = False
                    current_state = to_state
                    continue
                if from_state != current_state:
                    valid = False
                if to_state == current_state:
                    if transition_code != "retry_scheduled":
                        valid = False
                elif (
                    current_state not in ALLOWED_TRANSITIONS
                    or to_state not in ALLOWED_TRANSITIONS[current_state]
                ):
                    valid = False
                current_state = to_state
            if current_state != str(operation["state"]):
                valid = False
            if not valid:
                invalid_trace_refs.append(opaque_operation_ref(operation_id))
                if str(operation["state"]) in TERMINAL_OPERATION_STATES:
                    invalid_terminal_trace_count += 1
        duplicate_receipts = int(
            self.connection.execute(
                """
                SELECT COUNT(*) AS count_value
                FROM (
                  SELECT operation_id, effect_kind, COUNT(*) AS row_count
                  FROM consistency_effect_receipts
                  GROUP BY operation_id, effect_kind
                  HAVING COUNT(*) > 1
                ) duplicate_groups
                """
            ).fetchone()["count_value"]
        )
        quarantine_count = int(
            self.connection.execute(
                """
                SELECT COUNT(*) AS count_value
                FROM object_quarantine
                WHERE state = 'isolated'
                """
            ).fetchone()["count_value"]
        )
        terminal_operations = sum(
            count
            for state, count in operation_counts.items()
            if state in TERMINAL_OPERATION_STATES
        )
        terminal_outbox = sum(
            count
            for state, count in outbox_counts.items()
            if state in TERMINAL_OUTBOX_STATES
        )
        return {
            "schema_version": "kmfa.s05.p53.consistency-reconciliation.v1",
            "operation_count": len(operations),
            "operation_state_counts": dict(sorted(operation_counts.items())),
            "terminal_operation_count": terminal_operations,
            "partial_operation_count": len(operations) - terminal_operations,
            "outbox_event_count": len(outbox),
            "outbox_state_counts": dict(sorted(outbox_counts.items())),
            "terminal_outbox_count": terminal_outbox,
            "partial_outbox_count": len(outbox) - terminal_outbox,
            "quarantined_object_count": quarantine_count,
            "unexplained_terminal_states": (
                len(unexplained_operations)
                + len(unexplained_outbox)
                + delivered_without_receipt
                + converged_without_outbox
                + invalid_terminal_trace_count
            ),
            "delivered_without_receipt": delivered_without_receipt,
            "converged_without_outbox": converged_without_outbox,
            "invalid_operation_trace_count": len(invalid_trace_refs),
            "invalid_operation_trace_refs": sorted(invalid_trace_refs),
            "duplicate_effect_receipts": duplicate_receipts,
            "operation_refs": [
                opaque_operation_ref(str(row["operation_id"]))
                for row in operations
            ],
        }
