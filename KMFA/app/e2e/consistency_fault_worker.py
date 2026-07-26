#!/usr/bin/env python3
"""In-image synthetic worker used by the S05/P5.3 fault Oracle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from app import walking_skeleton as skeleton
from app.consistency_reconciliation import (
    RetryableConsistencyEffect,
    deliver_outbox_once,
    quarantine_orphan_inventory,
    recover_generic_operation,
)
from app.consistency_state import (
    ClaimedOutboxEvent,
    ConsistencyRepository,
    UploadIntent,
    upload_request_fingerprint,
)
from app.object_storage import (
    ObjectStorageConflictError,
    content_md5_base64,
)
from app.retention_lifecycle import LifecycleRepository
from app.structured_repository import StructuredRepository

T0 = "2026-07-24T00:00:00Z"
FUTURE = "9999-12-31T23:59:59Z"


def _sink_path() -> Path:
    explicit = os.environ.get("KMFA_CONSISTENCY_ORACLE_SINK", "").strip()
    if not explicit:
        raise RuntimeError("synthetic sink path is required")
    path = Path(explicit)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    return path


def _sink() -> sqlite3.Connection:
    connection = sqlite3.connect(_sink_path())
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=FULL;
        CREATE TABLE IF NOT EXISTS effects (
          dedupe_key TEXT PRIMARY KEY,
          effect_kind TEXT NOT NULL,
          request_fingerprint TEXT NOT NULL,
          receipt_hash TEXT NOT NULL,
          applied_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS attempts (
          seq INTEGER PRIMARY KEY AUTOINCREMENT,
          dedupe_key TEXT NOT NULL,
          effect_kind TEXT NOT NULL,
          attempted_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS markers (
          marker_key TEXT PRIMARY KEY,
          created_at TEXT NOT NULL
        );
        """
    )
    return connection


def _receipt_hash(
    dedupe_key: str,
    effect_kind: str,
    request_fingerprint: str,
) -> str:
    return hashlib.sha256(
        f"{dedupe_key}:{effect_kind}:{request_fingerprint}".encode()
    ).hexdigest()


def _apply_sink_once(
    *,
    dedupe_key: str,
    effect_kind: str,
    request_fingerprint: str,
    timeout_marker: str | None = None,
) -> str:
    receipt_hash = _receipt_hash(
        dedupe_key,
        effect_kind,
        request_fingerprint,
    )
    connection = _sink()
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """
            INSERT INTO attempts(dedupe_key, effect_kind, attempted_at)
            VALUES (?, ?, ?)
            """,
            (dedupe_key, effect_kind, T0),
        )
        connection.execute(
            """
            INSERT INTO effects(
              dedupe_key, effect_kind, request_fingerprint,
              receipt_hash, applied_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(dedupe_key) DO NOTHING
            """,
            (
                dedupe_key,
                effect_kind,
                request_fingerprint,
                receipt_hash,
                T0,
            ),
        )
        stored = connection.execute(
            """
            SELECT effect_kind, request_fingerprint, receipt_hash
            FROM effects
            WHERE dedupe_key = ?
            """,
            (dedupe_key,),
        ).fetchone()
        if stored is None or dict(stored) != {
            "effect_kind": effect_kind,
            "request_fingerprint": request_fingerprint,
            "receipt_hash": receipt_hash,
        }:
            raise RuntimeError("synthetic effect identity conflict")
        should_timeout = False
        if timeout_marker:
            inserted = connection.execute(
                """
                INSERT INTO markers(marker_key, created_at)
                VALUES (?, ?)
                ON CONFLICT(marker_key) DO NOTHING
                """,
                (timeout_marker, T0),
            )
            should_timeout = inserted.rowcount == 1
        connection.execute("COMMIT")
    except BaseException:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()
    if should_timeout:
        raise RetryableConsistencyEffect("synthetic timeout after apply")
    return receipt_hash


def _workspace_id(scenario: str) -> str:
    return "ws_" + hashlib.sha256(scenario.encode()).hexdigest()[:22]


def _ensure_workspace(workspace_id: str, scenario: str) -> None:
    connection = skeleton._open_store()
    try:
        with connection.transaction():
            timestamp = T0
            recovery_hash = hashlib.sha256(
                f"recovery:{scenario}".encode()
            ).hexdigest()
            connection.execute(
                """
                INSERT INTO workspaces(
                  workspace_id, recovery_hash, project_name, progress,
                  created_at, updated_at
                ) VALUES (?, ?, ?, 0, ?, ?)
                ON CONFLICT(workspace_id) DO NOTHING
                """,
                (
                    workspace_id,
                    recovery_hash,
                    f"Synthetic {scenario}",
                    timestamp,
                    timestamp,
                ),
            )
            StructuredRepository(connection).ensure_project_projection(
                workspace_id=workspace_id,
                name=f"Synthetic {scenario}",
                progress=0,
                created_at=timestamp,
                updated_at=timestamp,
            )
            LifecycleRepository(connection).ensure_workspace_retention(
                workspace_id=workspace_id,
                created_at=timestamp,
                updated_at=timestamp,
            )
    finally:
        connection.close()


class _GenericAdapter:
    def __init__(
        self,
        operation_kind: str,
        scenario: str,
        *,
        timeout_once: bool = False,
        mismatch: bool = False,
    ) -> None:
        self.outbox_effect_kind = operation_kind
        self.operation_kind = operation_kind
        self.scenario = scenario
        self.timeout_once = timeout_once
        self.mismatch = mismatch

    @staticmethod
    def _dedupe(operation: Mapping[str, Any]) -> str:
        return hashlib.sha256(
            f"kmfa-primary-v1:{operation['operation_id']}".encode()
        ).hexdigest()

    def probe(self, operation: Mapping[str, Any]) -> str:
        if self.mismatch:
            return "mismatch"
        connection = _sink()
        try:
            row = connection.execute(
                """
                SELECT effect_kind, request_fingerprint
                FROM effects
                WHERE dedupe_key = ?
                """,
                (self._dedupe(operation),),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            return "absent"
        if (
            str(row["effect_kind"]) == f"primary-{self.operation_kind}"
            and str(row["request_fingerprint"])
            == str(operation["request_fingerprint"])
        ):
            return "applied"
        return "mismatch"

    def apply_once(
        self,
        operation: Mapping[str, Any],
        *,
        dedupe_key: str,
    ) -> None:
        _apply_sink_once(
            dedupe_key=dedupe_key,
            effect_kind=f"primary-{self.operation_kind}",
            request_fingerprint=str(operation["request_fingerprint"]),
            timeout_marker=(
                f"primary-timeout:{self.scenario}"
                if self.timeout_once
                else None
            ),
        )

    def commit_primary(self, connection, operation: Mapping[str, Any]) -> None:
        task_id = f"task_oracle_{operation['operation_id']}"
        timestamp = T0
        StructuredRepository(connection).put_task(
            task_id=task_id,
            workspace_id=str(operation["workspace_id"]),
            title=f"Synthetic {self.operation_kind} projection",
            status="done",
            sort_order=0,
            due_at=None,
            timestamp=timestamp,
        )


class _OutboxConsumer:
    def __init__(self, scenario: str, *, timeout_once: bool = False) -> None:
        self.scenario = scenario
        self.timeout_once = timeout_once

    def apply_once(self, event: ClaimedOutboxEvent) -> str:
        return _apply_sink_once(
            dedupe_key=f"outbox:{event.dedupe_key}",
            effect_kind=f"outbox-{event.effect_kind}",
            request_fingerprint=event.operation_id,
            timeout_marker=(
                f"outbox-timeout:{self.scenario}"
                if self.timeout_once
                else None
            ),
        )


def _fault_hook(expected: str | None):
    def hook(point: str) -> None:
        if expected and point == expected:
            os._exit(86)

    return hook


def _ensure_generic_operation(
    *,
    scenario: str,
    operation_kind: str,
) -> str:
    workspace_id = _workspace_id(scenario)
    _ensure_workspace(workspace_id, scenario)
    operation_id = f"operation_{operation_kind}_{scenario}"
    fingerprint = hashlib.sha256(
        f"{operation_kind}:{scenario}".encode()
    ).hexdigest()
    connection = skeleton._open_store()
    try:
        with connection.transaction():
            ConsistencyRepository(connection).create_generic_operation(
                operation_id=operation_id,
                workspace_id=workspace_id,
                operation_kind=operation_kind,
                idempotency_key=f"idempotency-{operation_kind}-{scenario}-v1",
                request_fingerprint=fingerprint,
                timestamp=T0,
            )
    finally:
        connection.close()
    return operation_id


def _run_generic(args: argparse.Namespace) -> dict[str, Any]:
    operation_id = _ensure_generic_operation(
        scenario=args.scenario,
        operation_kind=args.operation_kind,
    )
    result = recover_generic_operation(
        skeleton._open_store,
        operation_id=operation_id,
        adapter=_GenericAdapter(
            args.operation_kind,
            args.scenario,
            timeout_once=args.timeout_once,
            mismatch=args.mismatch,
        ),
        timestamp=T0,
        fault_hook=_fault_hook(args.fault),
    )
    return {
        "mode": "generic",
        "operation_ref": hashlib.sha256(operation_id.encode()).hexdigest()[:20],
        "result": result,
    }


def _ensure_upload_operation(scenario: str) -> str:
    workspace_id = _workspace_id(scenario)
    _ensure_workspace(workspace_id, scenario)
    operation_id = f"operation_upload_{scenario}"
    artifact_id = f"artifact_{hashlib.sha256(scenario.encode()).hexdigest()[:24]}"
    version_id = f"artifact-version_{artifact_id}"
    body = f"synthetic-upload:{scenario}".encode() * 31
    sha256 = hashlib.sha256(body).hexdigest()
    object_store = skeleton.configured_write_store(skeleton._state_root())
    storage_key = object_store.build_storage_key(
        workspace_id=workspace_id,
        artifact_id=artifact_id,
        artifact_version_id=version_id,
        version_number=1,
        sha256=sha256,
    )
    staged_name = f"workflow-{operation_id}.part"
    fingerprint = upload_request_fingerprint(
        workspace_id=workspace_id,
        original_name="synthetic-upload.bin",
        reported_media_type="application/octet-stream",
        size_bytes=len(body),
        content_sha256=sha256,
    )
    intent = UploadIntent(
        workspace_id=workspace_id,
        idempotency_key=f"idempotency-upload-{scenario}-v1",
        request_fingerprint=fingerprint,
        artifact_id=artifact_id,
        artifact_version_id=version_id,
        storage_backend=object_store.storage_backend,
        storage_key=storage_key,
        staged_object_name=staged_name,
        original_name="synthetic-upload.bin",
        reported_media_type="application/octet-stream",
        size_bytes=len(body),
        content_sha256=sha256,
    )
    connection = skeleton._open_store()
    try:
        with connection.transaction():
            ConsistencyRepository(connection).create_or_load_upload(
                intent,
                operation_id=operation_id,
                timestamp=T0,
            )
    finally:
        connection.close()
    operation = skeleton._load_consistency_operation(operation_id)
    staged_path = skeleton._tmp_dir() / staged_name
    if (
        str(operation["state"]) in {"intent_recorded", "effect_pending"}
        and not staged_path.exists()
    ):
        staged_path.write_bytes(body)
        staged_path.chmod(0o600)
    return operation_id


def _run_upload(args: argparse.Namespace) -> dict[str, Any]:
    operation_id = _ensure_upload_operation(args.scenario)
    object_store = skeleton.configured_write_store(skeleton._state_root())
    skeleton._resume_upload_operation(
        operation_id,
        object_store,
        fault_hook=_fault_hook(args.fault),
    )
    operation = skeleton._load_consistency_operation(operation_id)
    return {
        "mode": "upload",
        "operation_ref": hashlib.sha256(operation_id.encode()).hexdigest()[:20],
        "result": operation["state"],
    }


def _run_outbox(args: argparse.Namespace) -> dict[str, Any]:
    operation_id = _ensure_generic_operation(
        scenario=args.scenario,
        operation_kind=args.operation_kind,
    )
    recover_generic_operation(
        skeleton._open_store,
        operation_id=operation_id,
        adapter=_GenericAdapter(args.operation_kind, args.scenario),
        timestamp=T0,
    )
    result = deliver_outbox_once(
        skeleton._open_store,
        consumer=_OutboxConsumer(
            args.scenario,
            timeout_once=args.timeout_once,
        ),
        now=FUTURE,
        lease_until=FUTURE,
        retry_at=T0,
        effect_kinds={args.operation_kind},
        fault_hook=_fault_hook(args.fault),
    )
    return {
        "mode": "outbox",
        "operation_ref": hashlib.sha256(operation_id.encode()).hexdigest()[:20],
        "result": result,
    }


def _drain_outbox(args: argparse.Namespace) -> dict[str, Any]:
    result = deliver_outbox_once(
        skeleton._open_store,
        consumer=_OutboxConsumer("bounded-drain"),
        now=FUTURE,
        lease_until=FUTURE,
        retry_at=T0,
        effect_kinds=None,
        fault_hook=_fault_hook(args.fault),
    )
    return {"mode": "drain", "result": result}


def _run_orphan(args: argparse.Namespace) -> dict[str, Any]:
    object_store = skeleton.configured_write_store(skeleton._state_root())
    body = b"synthetic-orphan-object"
    sha256 = hashlib.sha256(body).hexdigest()
    artifact_id = "artifact_orphan_synthetic"
    version_id = "artifact-version_artifact_orphan_synthetic"
    storage_key = object_store.build_storage_key(
        workspace_id="ws_" + ("o" * 22),
        artifact_id=artifact_id,
        artifact_version_id=version_id,
        version_number=1,
        sha256=sha256,
    )
    source = skeleton._tmp_dir() / "oracle-orphan-source.part"
    source.write_bytes(body)
    md5 = hashlib.md5(body, usedforsecurity=False)
    try:
        try:
            object_store.put_file(
                source,
                storage_key=storage_key,
                size_bytes=len(body),
                sha256=sha256,
                content_md5=content_md5_base64(md5),
                artifact_id=artifact_id,
                artifact_version_id=version_id,
            )
        except ObjectStorageConflictError:
            object_store.verify_existing(
                storage_key=storage_key,
                expected_size=len(body),
                expected_sha256=sha256,
                artifact_id=artifact_id,
                artifact_version_id=version_id,
            )
    finally:
        source.unlink(missing_ok=True)
    inventory = object_store.inventory()
    connection = skeleton._open_store()
    try:
        with connection.transaction():
            report = quarantine_orphan_inventory(
                connection,
                storage_backend=object_store.storage_backend,
                inventory=inventory,
                timestamp=T0,
            )
    finally:
        connection.close()
    object_store.verify_existing(
        storage_key=storage_key,
        expected_size=len(body),
        expected_sha256=sha256,
        artifact_id=artifact_id,
        artifact_version_id=version_id,
    )
    return {
        "mode": "orphan",
        "result": "isolated",
        "quarantined": report["new_or_seen_orphan_count"],
        "raw_object_deletes": report["raw_object_deletes"],
    }


def _final_report() -> dict[str, Any]:
    connection = skeleton._open_store()
    try:
        repository = ConsistencyRepository(connection)
        reconciliation = repository.reconciliation_report()
        traces = connection.execute(
            """
            SELECT operation_id, COUNT(*) AS transition_count
            FROM consistency_trace
            GROUP BY operation_id
            ORDER BY operation_id
            """
        ).fetchall()
    finally:
        connection.close()
    sink = _sink()
    try:
        effect_count = int(
            sink.execute("SELECT COUNT(*) FROM effects").fetchone()[0]
        )
        duplicate_effects = int(
            sink.execute(
                """
                SELECT COUNT(*)
                FROM (
                  SELECT dedupe_key, COUNT(*) AS row_count
                  FROM effects
                  GROUP BY dedupe_key
                  HAVING COUNT(*) > 1
                )
                """
            ).fetchone()[0]
        )
        attempt_count = int(
            sink.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
        )
    finally:
        sink.close()
    return {
        "mode": "report",
        "reconciliation": reconciliation,
        "trace_count": sum(int(row["transition_count"]) for row in traces),
        "traced_operation_count": len(traces),
        "external_effect_count": effect_count,
        "external_effect_attempt_count": attempt_count,
        "duplicate_external_side_effects": duplicate_effects,
        "raw_object_deletes": 0,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices={
            "generic",
            "upload",
            "outbox",
            "drain",
            "orphan",
            "report",
        },
        required=True,
    )
    parser.add_argument("--scenario", default="report")
    parser.add_argument(
        "--operation-kind",
        choices={"process", "index", "export"},
        default="process",
    )
    parser.add_argument("--fault")
    parser.add_argument("--timeout-once", action="store_true")
    parser.add_argument("--mismatch", action="store_true")
    args = parser.parse_args(argv)
    if args.mode == "generic":
        result = _run_generic(args)
    elif args.mode == "upload":
        result = _run_upload(args)
    elif args.mode == "outbox":
        result = _run_outbox(args)
    elif args.mode == "drain":
        result = _drain_outbox(args)
    elif args.mode == "orphan":
        result = _run_orphan(args)
    else:
        result = _final_report()
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
