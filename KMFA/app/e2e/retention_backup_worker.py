#!/usr/bin/env python3
"""Synthetic-only helper for the S05/P5.4 production-image Oracle."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from app import retention_lifecycle
from app.object_storage import ObjectStorageUnavailableError
from app.retention_lifecycle import (
    LifecycleRepository,
    LifecycleWorkerError,
    due_deletion_request_ids,
    process_deletion_request,
    utc_timestamp,
)
from app.structured_repository import (
    AcceptanceFixture,
    StructuredDataService,
)
from app.structured_store import open_structured_store


def _state_root() -> Path:
    explicit = os.environ.get("KMFA_WALKING_SKELETON_STATE_DIR", "").strip()
    if explicit:
        return Path(explicit)
    return Path(
        os.environ.get("KMFA_APP_STATE_DIR", "/var/lib/kmfa/state")
    ) / "walking-skeleton"


def _open_connection():
    root = _state_root()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    root.chmod(0o700)
    return open_structured_store(root / "walking_skeleton.sqlite3")


class FilePublicationEffects:
    """Small external-effect fixture with a durable, inspectable state file."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def revoke_and_purge(
        self,
        *,
        publication_id: str,
        subject_ref: str,
    ) -> None:
        if len(subject_ref) != 20:
            raise LifecycleWorkerError("publication_subject_invalid")
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        for field in ("active", "cached", "indexed"):
            values = payload.get(field)
            if not isinstance(values, list) or publication_id not in values:
                raise LifecycleWorkerError("publication_effect_missing")
            payload[field] = [
                value for value in values if value != publication_id
            ]
        descriptor, temporary_name = tempfile.mkstemp(
            dir=self.path.parent,
            prefix=".publication-effects-",
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                json.dump(payload, output, sort_keys=True)
                output.write("\n")
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self.path)
        finally:
            temporary.unlink(missing_ok=True)


class FailingDeleteStore:
    def delete_all_versions(self, **_: object) -> int:
        raise ObjectStorageUnavailableError("object_store_unavailable")


def _seed(workspace_id: str) -> dict[str, Any]:
    connection = _open_connection()
    try:
        snapshot = StructuredDataService(connection).apply_acceptance_fixture(
            AcceptanceFixture(
                workspace_id=workspace_id,
                score=91,
                financial_record_id="finance_p54_synthetic",
                financial_record_type="budget",
                financial_category="p54 synthetic",
                amount_minor=543_210,
                currency="CNY",
                effective_date="2026-07-24",
                source_ref="synthetic://s05-p54",
                task_id="task_p54_synthetic",
                task_title="Verify P5.4 isolated recovery",
                task_status="in_progress",
                task_sort_order=10,
                task_due_at="2026-08-01T00:00:00Z",
                timestamp=utc_timestamp(),
            )
        )
        return {
            "status": "pass",
            "score": snapshot["project"]["score"],
            "financial_record_count": len(snapshot["financial_records"]),
            "task_count": len(snapshot["tasks"]),
        }
    finally:
        connection.close()


def _hold(
    *,
    action: str,
    workspace_id: str,
    hold_id: str,
) -> dict[str, Any]:
    connection = _open_connection()
    try:
        with connection.transaction():
            repository = LifecycleRepository(connection)
            if action == "impose":
                repository.impose_legal_hold(
                    workspace_id=workspace_id,
                    reason_code="regulatory",
                    authority_ref="synthetic-p54-oracle-authority",
                    timestamp=utc_timestamp(),
                    hold_id=hold_id,
                )
            else:
                repository.release_legal_hold(
                    hold_id=hold_id,
                    timestamp=utc_timestamp(),
                )
        return {"status": "pass", "action": action}
    finally:
        connection.close()


def _publication(
    *,
    workspace_id: str,
    publication_id: str,
) -> dict[str, Any]:
    connection = _open_connection()
    try:
        with connection.transaction():
            LifecycleRepository(connection).register_publication(
                publication_id=publication_id,
                workspace_id=workspace_id,
                subject_identity="synthetic-p54-public-subject",
                timestamp=utc_timestamp(),
            )
        return {"status": "pass", "registered": 1}
    finally:
        connection.close()


def _process(
    *,
    deletion_request_id: str,
    effects_file: Path,
    fail_object_delete: bool,
) -> dict[str, Any]:
    original_factory = retention_lifecycle.lifecycle_store_for_backend
    if fail_object_delete:
        retention_lifecycle.lifecycle_store_for_backend = (
            lambda *_: FailingDeleteStore()
        )
    expected_retry = False
    try:
        process_deletion_request(
            open_connection=_open_connection,
            state_root=_state_root(),
            deletion_request_id=deletion_request_id,
            publication_effects=FilePublicationEffects(effects_file),
        )
    except LifecycleWorkerError:
        if not fail_object_delete:
            raise
        expected_retry = True
    finally:
        retention_lifecycle.lifecycle_store_for_backend = original_factory

    connection = _open_connection()
    try:
        request = connection.execute(
            """
            SELECT state, attempt_count, public_purged_at, public_purge_due_at
            FROM deletion_requests
            WHERE deletion_request_id = ?
            """,
            (deletion_request_id,),
        ).fetchone()
        if request is None:
            raise LifecycleWorkerError("deletion_request_not_found")
        purge_within_sla = False
        if request["public_purged_at"] is not None:
            purged = datetime.fromisoformat(
                str(request["public_purged_at"]).replace("Z", "+00:00")
            )
            due = datetime.fromisoformat(
                str(request["public_purge_due_at"]).replace("Z", "+00:00")
            )
            purge_within_sla = purged <= due
        if fail_object_delete and (
            not expected_retry or str(request["state"]) != "retry"
        ):
            raise LifecycleWorkerError("expected_retry_missing")
        return {
            "status": "pass",
            "request_state": str(request["state"]),
            "attempt_count": int(request["attempt_count"]),
            "public_purge_within_sla": purge_within_sla,
        }
    finally:
        connection.close()


def _summary(workspace_id: str) -> dict[str, Any]:
    connection = _open_connection()
    try:
        retention = connection.execute(
            """
            SELECT state
            FROM workspace_retention
            WHERE workspace_id = ?
            """,
            (workspace_id,),
        ).fetchone()
        score = connection.execute(
            """
            SELECT pm.score
            FROM project_metrics pm
            JOIN projects p ON p.project_id = pm.project_id
            WHERE p.workspace_id = ?
            """,
            (workspace_id,),
        ).fetchone()

        def count(table: str, where: str, parameters: tuple[Any, ...]) -> int:
            row = connection.execute(
                f"SELECT COUNT(*) AS count_value FROM {table} WHERE {where}",
                parameters,
            ).fetchone()
            return int(row["count_value"])

        project_count = count("projects", "workspace_id = ?", (workspace_id,))
        artifact_count = count(
            "artifacts",
            "workspace_id = ?",
            (workspace_id,),
        )
        financial_count = int(
            connection.execute(
                """
                SELECT COUNT(*) AS count_value
                FROM financial_records fr
                JOIN projects p ON p.project_id = fr.project_id
                WHERE p.workspace_id = ?
                """,
                (workspace_id,),
            ).fetchone()["count_value"]
        )
        task_count = int(
            connection.execute(
                """
                SELECT COUNT(*) AS count_value
                FROM workspace_tasks wt
                JOIN projects p ON p.project_id = wt.project_id
                WHERE p.workspace_id = ?
                """,
                (workspace_id,),
            ).fetchone()["count_value"]
        )
        completed_events = count(
            "lifecycle_events",
            "action = ? AND result_status = ?",
            ("workspace_deletion_completed", "deleted"),
        )
        passed_proofs = count(
            "restore_drill_proofs",
            "status = ?",
            ("passed",),
        )
        return {
            "status": "pass",
            "schema_version": connection.schema_version(),
            "retention_state": (
                None if retention is None else str(retention["state"])
            ),
            "project_count": project_count,
            "score": None if score is None else int(score["score"]),
            "financial_record_count": financial_count,
            "task_count": task_count,
            "artifact_count": artifact_count,
            "due_deletion_count": len(
                due_deletion_request_ids(connection, limit=100)
            ),
            "completed_deletion_event_count": completed_events,
            "passed_restore_proof_count": passed_proofs,
        }
    finally:
        connection.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    seed = subparsers.add_parser("seed")
    seed.add_argument("--workspace-id", required=True)
    hold = subparsers.add_parser("hold")
    hold.add_argument("--action", choices=("impose", "release"), required=True)
    hold.add_argument("--workspace-id", required=True)
    hold.add_argument("--hold-id", required=True)
    publication = subparsers.add_parser("publication")
    publication.add_argument("--workspace-id", required=True)
    publication.add_argument("--publication-id", required=True)
    process = subparsers.add_parser("process")
    process.add_argument("--deletion-request-id", required=True)
    process.add_argument("--effects-file", type=Path, required=True)
    process.add_argument("--fail-object-delete", action="store_true")
    summary = subparsers.add_parser("summary")
    summary.add_argument("--workspace-id", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.command == "seed":
        result = _seed(arguments.workspace_id)
    elif arguments.command == "hold":
        result = _hold(
            action=arguments.action,
            workspace_id=arguments.workspace_id,
            hold_id=arguments.hold_id,
        )
    elif arguments.command == "publication":
        result = _publication(
            workspace_id=arguments.workspace_id,
            publication_id=arguments.publication_id,
        )
    elif arguments.command == "process":
        result = _process(
            deletion_request_id=arguments.deletion_request_id,
            effects_file=arguments.effects_file,
            fail_object_delete=arguments.fail_object_delete,
        )
    else:
        result = _summary(arguments.workspace_id)
    print(json.dumps(result, sort_keys=True))
    return int(result["status"] != "pass")


if __name__ == "__main__":
    raise SystemExit(main())
