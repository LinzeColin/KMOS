"""Executable reconciliation workers for the S05/P5.3 state contract."""

from __future__ import annotations

import hashlib
from typing import Any, Callable, Iterable, Mapping, Protocol

from .consistency_state import (
    EFFECT_KINDS,
    ClaimedOutboxEvent,
    ConsistencyRepository,
    ConsistencyStateError,
)
from .object_storage import InventoryObject
from .structured_store import StructuredStoreConnection

ConnectionFactory = Callable[[], StructuredStoreConnection]
FaultHook = Callable[[str], None]


class RetryableConsistencyEffect(RuntimeError):
    """The outcome may be retried or probed without losing source state."""


class PermanentConsistencyEffect(RuntimeError):
    """The effect cannot safely continue and must be explicitly isolated."""


class RecoverableOperationAdapter(Protocol):
    """Idempotent primary-effect adapter used by process/index/export."""

    outbox_effect_kind: str

    def probe(self, operation: Mapping[str, Any]) -> str:
        """Return exactly ``absent``, ``applied`` or ``mismatch``."""

    def apply_once(
        self,
        operation: Mapping[str, Any],
        *,
        dedupe_key: str,
    ) -> None:
        """Apply the effect idempotently using ``dedupe_key``."""

    def commit_primary(
        self,
        connection: StructuredStoreConnection,
        operation: Mapping[str, Any],
    ) -> None:
        """Idempotently commit any database projection in the current tx."""


class IdempotentOutboxConsumer(Protocol):
    def apply_once(self, event: ClaimedOutboxEvent) -> str:
        """Return a stable SHA-256 receipt and dedupe the external effect."""


def _primary_dedupe_key(operation_id: str) -> str:
    return hashlib.sha256(
        f"kmfa-primary-v1:{operation_id}".encode("utf-8")
    ).hexdigest()


def _fault(hook: FaultHook | None, point: str) -> None:
    if hook is not None:
        hook(point)


def recover_generic_operation(
    open_connection: ConnectionFactory,
    *,
    operation_id: str,
    adapter: RecoverableOperationAdapter,
    timestamp: str,
    fault_hook: FaultHook | None = None,
) -> str:
    """Converge one process/index/export operation or explicitly isolate it."""

    if adapter.outbox_effect_kind not in EFFECT_KINDS:
        raise ConsistencyStateError("invalid_effect_kind")
    for _ in range(8):
        connection = open_connection()
        try:
            row = ConsistencyRepository(connection).operation(operation_id)
            if row is None:
                raise ConsistencyStateError("consistency_operation_missing")
            operation = dict(row)
        finally:
            connection.close()
        if operation["operation_kind"] == "upload":
            raise ConsistencyStateError("upload_requires_object_reconciler")
        state = str(operation["state"])
        if state in {"converged", "isolated"}:
            return state

        if state == "intent_recorded":
            connection = open_connection()
            try:
                with connection.transaction():
                    ConsistencyRepository(connection).transition(
                        operation_id,
                        expected_state="intent_recorded",
                        to_state="effect_pending",
                        transition_code="effect_started",
                        timestamp=timestamp,
                    )
            finally:
                connection.close()
            _fault(fault_hook, "effect_pending")
            continue

        if state == "effect_pending":
            outcome = adapter.probe(operation)
            if outcome not in {"absent", "applied", "mismatch"}:
                raise ConsistencyStateError("invalid_effect_probe")
            if outcome == "absent":
                try:
                    adapter.apply_once(
                        operation,
                        dedupe_key=_primary_dedupe_key(operation_id),
                    )
                    _fault(fault_hook, "primary_effect_applied")
                except RetryableConsistencyEffect:
                    outcome = adapter.probe(operation)
                    if outcome == "absent":
                        connection = open_connection()
                        try:
                            with connection.transaction():
                                ConsistencyRepository(
                                    connection
                                ).record_attempt_failure(
                                    operation_id,
                                    expected_state="effect_pending",
                                    error_code="primary_effect_retryable",
                                    timestamp=timestamp,
                                )
                        finally:
                            connection.close()
                        return "retry"
                except PermanentConsistencyEffect:
                    outcome = "mismatch"
                else:
                    outcome = adapter.probe(operation)
            if outcome == "mismatch":
                connection = open_connection()
                try:
                    with connection.transaction():
                        ConsistencyRepository(connection).isolate(
                            operation_id,
                            expected_state="effect_pending",
                            error_code="primary_effect_mismatch",
                            timestamp=timestamp,
                        )
                finally:
                    connection.close()
                _fault(fault_hook, "isolated")
                return "isolated"
            if outcome != "applied":
                raise ConsistencyStateError("effect_did_not_converge")
            connection = open_connection()
            try:
                with connection.transaction():
                    ConsistencyRepository(connection).transition(
                        operation_id,
                        expected_state="effect_pending",
                        to_state="effect_applied",
                        transition_code="effect_verified",
                        timestamp=timestamp,
                        increment_attempt=True,
                    )
            finally:
                connection.close()
            _fault(fault_hook, "effect_applied")
            continue

        if state == "effect_applied":
            connection = open_connection()
            try:
                with connection.transaction():
                    ConsistencyRepository(connection).transition(
                        operation_id,
                        expected_state="effect_applied",
                        to_state="commit_pending",
                        transition_code="commit_started",
                        timestamp=timestamp,
                    )
            finally:
                connection.close()
            _fault(fault_hook, "commit_pending")
            continue

        if state == "commit_pending":
            connection = open_connection()
            try:
                with connection.transaction():
                    repository = ConsistencyRepository(connection)
                    current = repository.operation(operation_id)
                    if current is None:
                        raise ConsistencyStateError(
                            "consistency_operation_missing"
                        )
                    adapter.commit_primary(connection, current)
                    repository.ensure_outbox(
                        operation_id=operation_id,
                        effect_kind=adapter.outbox_effect_kind,
                        timestamp=timestamp,
                    )
                    repository.transition(
                        operation_id,
                        expected_state="commit_pending",
                        to_state="outbox_committed",
                        transition_code="primary_and_outbox_committed",
                        timestamp=timestamp,
                    )
            finally:
                connection.close()
            _fault(fault_hook, "outbox_committed")
            continue

        if state == "outbox_committed":
            connection = open_connection()
            try:
                with connection.transaction():
                    ConsistencyRepository(connection).transition(
                        operation_id,
                        expected_state="outbox_committed",
                        to_state="converged",
                        transition_code="operation_converged",
                        timestamp=timestamp,
                    )
            finally:
                connection.close()
            _fault(fault_hook, "converged")
            continue
        raise ConsistencyStateError("unknown_consistency_state")
    raise ConsistencyStateError("operation_reconciliation_exhausted")


def deliver_outbox_once(
    open_connection: ConnectionFactory,
    *,
    consumer: IdempotentOutboxConsumer,
    now: str,
    lease_until: str,
    retry_at: str,
    effect_kinds: Iterable[str] | None = None,
    max_attempts: int = 5,
    fault_hook: FaultHook | None = None,
) -> str:
    """Deliver one due event with lease recovery and consumer-side dedupe."""

    connection = open_connection()
    try:
        with connection.transaction():
            event = ConsistencyRepository(connection).claim_outbox(
                now=now,
                lease_until=lease_until,
                effect_kinds=effect_kinds,
            )
    finally:
        connection.close()
    if event is None:
        return "idle"
    _fault(fault_hook, "outbox_leased")

    connection = open_connection()
    try:
        receipt = ConsistencyRepository(connection).effect_receipt(
            event.dedupe_key
        )
    finally:
        connection.close()
    if receipt is None:
        try:
            receipt_hash = consumer.apply_once(event)
            _fault(fault_hook, "outbox_effect_applied")
        except RetryableConsistencyEffect:
            connection = open_connection()
            try:
                with connection.transaction():
                    repository = ConsistencyRepository(connection)
                    if event.attempt_count >= max_attempts:
                        repository.isolate_outbox(
                            event,
                            error_code="outbox_retry_exhausted",
                            timestamp=now,
                        )
                        return "isolated"
                    repository.retry_outbox(
                        event,
                        available_at=retry_at,
                        error_code="outbox_delivery_retryable",
                        timestamp=now,
                    )
            finally:
                connection.close()
            return "retry"
        except PermanentConsistencyEffect:
            connection = open_connection()
            try:
                with connection.transaction():
                    ConsistencyRepository(connection).isolate_outbox(
                        event,
                        error_code="outbox_delivery_permanent",
                        timestamp=now,
                    )
            finally:
                connection.close()
            return "isolated"
        connection = open_connection()
        try:
            with connection.transaction():
                ConsistencyRepository(connection).record_effect_receipt(
                    event,
                    receipt_hash=receipt_hash,
                    timestamp=now,
                )
        finally:
            connection.close()
        _fault(fault_hook, "outbox_receipt_recorded")

    connection = open_connection()
    try:
        with connection.transaction():
            ConsistencyRepository(connection).acknowledge_outbox(
                event,
                timestamp=now,
            )
    finally:
        connection.close()
    _fault(fault_hook, "outbox_delivered")
    return "delivered"


def reconcile_upload_operations(
    *,
    limit: int = 100,
    isolate_after_attempts: int = 5,
) -> dict[str, Any]:
    """Resume durable upload intents using configured DB/object adapters.

    This job never deletes objects. A missing staging file plus a missing
    object is retried, then explicitly isolated after the bounded attempt
    budget so it cannot remain an unexplained terminal state.
    """

    if limit < 1 or limit > 1000 or isolate_after_attempts < 1:
        raise ValueError("invalid reconciliation bounds")
    # Local import avoids making the HTTP adapter a dependency of the generic
    # process/index/export reconciliation engine above.
    from . import walking_skeleton as skeleton

    connection = skeleton._open_store()
    try:
        rows = connection.execute(
            """
            SELECT operation_id
            FROM consistency_operations
            WHERE operation_kind = 'upload'
              AND state NOT IN ('converged', 'isolated')
            ORDER BY updated_at, operation_id
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        connection.close()

    resumed = 0
    retried = 0
    isolated = 0
    for row in rows:
        operation_id = str(row["operation_id"])
        try:
            # Resolve from the durable operation backend, not the current
            # write-mode flag. An in-flight S3 operation must remain recoverable
            # after new writes roll back to the legacy filesystem (and vice
            # versa).
            skeleton._resume_upload_operation(operation_id, None)
            resumed += 1
        except skeleton.SkeletonError:
            current = skeleton._load_consistency_operation(operation_id)
            if str(current["state"]) == "isolated":
                isolated += 1
                continue
            if (
                str(current["state"]) == "effect_pending"
                and int(current["attempt_count"]) >= isolate_after_attempts
                and str(current["last_error_code"]) == "object_write_retryable"
            ):
                skeleton._isolate_upload(
                    operation_id,
                    expected_state="effect_pending",
                    error_code="upload_source_unavailable",
                )
                isolated += 1
            else:
                retried += 1

    connection = skeleton._open_store()
    try:
        report = ConsistencyRepository(connection).reconciliation_report()
    finally:
        connection.close()
    return {
        "schema_version": "kmfa.s05.p53.upload-reconciliation-job.v1",
        "selected_operation_count": len(rows),
        "resumed_operation_count": resumed,
        "retry_operation_count": retried,
        "isolated_operation_count": isolated,
        "raw_object_deletes": 0,
        "reconciliation": report,
    }


def quarantine_orphan_inventory(
    connection: StructuredStoreConnection,
    *,
    storage_backend: str,
    inventory: Iterable[InventoryObject],
    timestamp: str,
) -> dict[str, Any]:
    """Persistently isolate inventory objects unknown to DB rows and intents."""

    inventory_items = list(inventory)
    indexed = {
        str(row["storage_key"])
        for row in connection.execute(
            """
            SELECT storage_key
            FROM artifact_versions
            WHERE storage_backend = ?
            """,
            (storage_backend,),
        ).fetchall()
    }
    intended = {
        str(row["storage_key"])
        for row in connection.execute(
            """
            SELECT storage_key
            FROM consistency_operations
            WHERE operation_kind = 'upload'
              AND storage_backend = ?
              AND storage_key IS NOT NULL
            """,
            (storage_backend,),
        ).fetchall()
    }
    repository = ConsistencyRepository(connection)
    refs: list[str] = []
    for item in inventory_items:
        if item.storage_key in indexed or item.storage_key in intended:
            continue
        refs.append(
            repository.quarantine_object(
                operation_id=None,
                storage_backend=storage_backend,
                storage_key=item.storage_key,
                reason_code="orphan_object_unindexed",
                timestamp=timestamp,
            )
        )
    return {
        "schema_version": "kmfa.s05.p53.orphan-quarantine.v1",
        "inventory_count": len(inventory_items),
        "indexed_or_intended_count": len(indexed | intended),
        "new_or_seen_orphan_count": len(refs),
        "orphan_refs": sorted(refs),
        "raw_object_deletes": 0,
    }
