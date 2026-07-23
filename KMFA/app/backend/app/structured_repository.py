"""Repository and transaction service for KMFA S05 structured state."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from .structured_store import StructuredStoreConnection, StructuredStoreError

FINANCIAL_RECORD_TYPES = frozenset(
    {"budget", "actual", "forecast", "adjustment"}
)
TASK_STATUSES = frozenset({"todo", "in_progress", "done", "cancelled"})
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


def project_id_for_workspace(workspace_id: str) -> str:
    return f"project_{workspace_id}"


def artifact_version_id(artifact_id: str, version_number: int) -> str:
    if version_number == 1:
        return f"artifact-version_{artifact_id}"
    return f"artifact-version_{artifact_id}_{version_number}"


class StructuredRepository:
    """SQL-only persistence layer; callers own the surrounding transaction."""

    def __init__(self, connection: StructuredStoreConnection) -> None:
        self.connection = connection

    def create_project_projection(
        self,
        *,
        workspace_id: str,
        name: str,
        progress: int,
        created_at: str,
        updated_at: str,
    ) -> str:
        project_id = project_id_for_workspace(workspace_id)
        self.connection.execute(
            """
            INSERT INTO projects(
              project_id, workspace_id, name, lifecycle_state, row_version,
              created_at, updated_at
            ) VALUES (?, ?, ?, 'active', 1, ?, ?)
            """,
            (project_id, workspace_id, name, created_at, updated_at),
        )
        self.connection.execute(
            """
            INSERT INTO project_metrics(
              project_id, progress, score, row_version, updated_at
            ) VALUES (?, ?, NULL, 1, ?)
            """,
            (project_id, progress, updated_at),
        )
        return project_id

    def ensure_project_projection(
        self,
        *,
        workspace_id: str,
        name: str,
        progress: int,
        created_at: str,
        updated_at: str,
    ) -> str:
        """Idempotently materialize an imported legacy workspace."""

        project_id = project_id_for_workspace(workspace_id)
        self.connection.execute(
            """
            INSERT INTO projects(
              project_id, workspace_id, name, lifecycle_state, row_version,
              created_at, updated_at
            ) VALUES (?, ?, ?, 'active', 1, ?, ?)
            ON CONFLICT(workspace_id) DO NOTHING
            """,
            (project_id, workspace_id, name, created_at, updated_at),
        )
        self.connection.execute(
            """
            INSERT INTO project_metrics(
              project_id, progress, score, row_version, updated_at
            ) VALUES (?, ?, NULL, 1, ?)
            ON CONFLICT(project_id) DO NOTHING
            """,
            (project_id, progress, updated_at),
        )
        row = self.connection.execute(
            """
            SELECT
              p.project_id, p.name, p.created_at, p.updated_at,
              m.progress
            FROM projects p
            JOIN project_metrics m ON m.project_id = p.project_id
            WHERE p.workspace_id = ?
            """,
            (workspace_id,),
        ).fetchone()
        expected = {
            "project_id": project_id,
            "name": name,
            "created_at": created_at,
            "updated_at": updated_at,
            "progress": progress,
        }
        if row is None or any(row[key] != value for key, value in expected.items()):
            raise StructuredStoreError("legacy project projection conflict")
        return project_id

    def save_project_projection(
        self,
        *,
        workspace_id: str,
        name: str,
        progress: int,
        updated_at: str,
    ) -> str:
        project_id = project_id_for_workspace(workspace_id)
        project_update = self.connection.execute(
            """
            UPDATE projects
            SET name = ?, row_version = row_version + 1, updated_at = ?
            WHERE project_id = ? AND lifecycle_state = 'active'
            """,
            (name, updated_at, project_id),
        )
        metrics_update = self.connection.execute(
            """
            UPDATE project_metrics
            SET progress = ?, row_version = row_version + 1, updated_at = ?
            WHERE project_id = ?
            """,
            (progress, updated_at, project_id),
        )
        if project_update.rowcount != 1 or metrics_update.rowcount != 1:
            raise StructuredStoreError("structured project projection is missing")
        return project_id

    def set_score(
        self,
        *,
        workspace_id: str,
        score: int | None,
        updated_at: str,
    ) -> None:
        updated = self.connection.execute(
            """
            UPDATE project_metrics
            SET score = ?, row_version = row_version + 1, updated_at = ?
            WHERE project_id = ?
            """,
            (score, updated_at, project_id_for_workspace(workspace_id)),
        )
        if updated.rowcount != 1:
            raise StructuredStoreError("structured project metrics are missing")

    def register_artifact_version(
        self,
        *,
        workspace_id: str,
        artifact_id: str,
        version_number: int,
        storage_backend: str,
        storage_key: str,
        original_name: str,
        reported_media_type: str,
        size_bytes: int,
        sha256: str,
        created_at: str,
    ) -> str:
        version_id = artifact_version_id(artifact_id, version_number)
        self.connection.execute(
            """
            INSERT INTO artifact_versions(
              artifact_version_id, artifact_id, project_id, version_number,
              storage_backend, storage_key, original_name, reported_media_type,
              size_bytes, sha256, lifecycle_state, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
            """,
            (
                version_id,
                artifact_id,
                project_id_for_workspace(workspace_id),
                version_number,
                storage_backend,
                storage_key,
                original_name,
                reported_media_type,
                size_bytes,
                sha256,
                created_at,
            ),
        )
        return version_id

    def ensure_artifact_version(
        self,
        *,
        workspace_id: str,
        artifact_id: str,
        storage_key: str,
        original_name: str,
        reported_media_type: str,
        size_bytes: int,
        sha256: str,
        created_at: str,
    ) -> str:
        version_id = artifact_version_id(artifact_id, 1)
        self.connection.execute(
            """
            INSERT INTO artifact_versions(
              artifact_version_id, artifact_id, project_id, version_number,
              storage_backend, storage_key, original_name, reported_media_type,
              size_bytes, sha256, lifecycle_state, created_at
            ) VALUES (
              ?, ?, ?, 1, 'legacy-private-filesystem', ?, ?, ?, ?, ?, 'active', ?
            )
            ON CONFLICT(artifact_id, version_number) DO NOTHING
            """,
            (
                version_id,
                artifact_id,
                project_id_for_workspace(workspace_id),
                storage_key,
                original_name,
                reported_media_type,
                size_bytes,
                sha256,
                created_at,
            ),
        )
        row = self.connection.execute(
            """
            SELECT
              artifact_version_id, project_id, storage_key, original_name,
              reported_media_type, size_bytes, sha256, created_at
            FROM artifact_versions
            WHERE artifact_id = ? AND version_number = 1
            """,
            (artifact_id,),
        ).fetchone()
        expected = {
            "artifact_version_id": version_id,
            "project_id": project_id_for_workspace(workspace_id),
            "storage_key": storage_key,
            "original_name": original_name,
            "reported_media_type": reported_media_type,
            "size_bytes": size_bytes,
            "sha256": sha256,
            "created_at": created_at,
        }
        if row is None or any(row[key] != value for key, value in expected.items()):
            raise StructuredStoreError("legacy artifact projection conflict")
        return version_id

    def put_financial_record(
        self,
        *,
        financial_record_id: str,
        workspace_id: str,
        record_type: str,
        category: str,
        amount_minor: int,
        currency: str,
        effective_date: str,
        source_ref: str | None,
        timestamp: str,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO financial_records(
              financial_record_id, project_id, record_type, category,
              amount_minor, currency, effective_date, source_ref, row_version,
              created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(financial_record_id) DO UPDATE SET
              record_type = excluded.record_type,
              category = excluded.category,
              amount_minor = excluded.amount_minor,
              currency = excluded.currency,
              effective_date = excluded.effective_date,
              source_ref = excluded.source_ref,
              row_version = financial_records.row_version + 1,
              updated_at = excluded.updated_at
            """,
            (
                financial_record_id,
                project_id_for_workspace(workspace_id),
                record_type,
                category,
                amount_minor,
                currency,
                effective_date,
                source_ref,
                timestamp,
                timestamp,
            ),
        )

    def put_task(
        self,
        *,
        task_id: str,
        workspace_id: str,
        title: str,
        status: str,
        sort_order: int,
        due_at: str | None,
        timestamp: str,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO workspace_tasks(
              task_id, project_id, title, status, sort_order, due_at,
              row_version, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(task_id) DO UPDATE SET
              title = excluded.title,
              status = excluded.status,
              sort_order = excluded.sort_order,
              due_at = excluded.due_at,
              row_version = workspace_tasks.row_version + 1,
              updated_at = excluded.updated_at
            """,
            (
                task_id,
                project_id_for_workspace(workspace_id),
                title,
                status,
                sort_order,
                due_at,
                timestamp,
                timestamp,
            ),
        )

    def workspace_projection(self, workspace_id: str) -> Any | None:
        return self.connection.execute(
            """
            SELECT
              p.project_id,
              p.workspace_id,
              p.name AS project_name,
              p.lifecycle_state,
              p.created_at,
              p.updated_at,
              m.progress,
              m.score
            FROM projects p
            JOIN project_metrics m ON m.project_id = p.project_id
            WHERE p.workspace_id = ?
            """,
            (workspace_id,),
        ).fetchone()

    def latest_artifact_version(self, workspace_id: str) -> Any | None:
        return self.connection.execute(
            """
            SELECT
              av.artifact_id,
              av.artifact_version_id,
              av.version_number,
              av.storage_backend,
              av.storage_key,
              av.original_name,
              av.reported_media_type,
              av.size_bytes,
              av.sha256,
              av.lifecycle_state,
              av.created_at
            FROM artifact_versions av
            JOIN projects p ON p.project_id = av.project_id
            WHERE p.workspace_id = ? AND av.lifecycle_state = 'active'
            ORDER BY av.created_at DESC, av.version_number DESC,
                     av.artifact_version_id DESC
            LIMIT 1
            """,
            (workspace_id,),
        ).fetchone()

    def artifact_object_index(self, *, storage_backend: str) -> list[Any]:
        """Return the non-secret object index required by inventory reconciliation."""

        return self.connection.execute(
            """
            SELECT
              av.artifact_version_id,
              av.artifact_id,
              av.version_number,
              av.storage_backend,
              av.storage_key,
              av.size_bytes,
              av.sha256,
              av.lifecycle_state
            FROM artifact_versions av
            WHERE av.storage_backend = ? AND av.lifecycle_state = 'active'
            ORDER BY av.storage_key, av.artifact_version_id
            """,
            (storage_backend,),
        ).fetchall()

    def workspace_snapshot(self, workspace_id: str) -> dict[str, Any]:
        project = self.workspace_projection(workspace_id)
        if project is None:
            raise StructuredStoreError("structured project projection is missing")
        project_id = str(project["project_id"])
        finances = self.connection.execute(
            """
            SELECT
              financial_record_id, record_type, category, amount_minor,
              currency, effective_date, source_ref, row_version, created_at,
              updated_at
            FROM financial_records
            WHERE project_id = ?
            ORDER BY effective_date, financial_record_id
            """,
            (project_id,),
        ).fetchall()
        artifacts = self.connection.execute(
            """
            SELECT
              artifact_version_id, artifact_id, version_number,
              storage_backend, storage_key, original_name,
              reported_media_type, size_bytes, sha256, lifecycle_state,
              created_at
            FROM artifact_versions
            WHERE project_id = ?
            ORDER BY artifact_id, version_number
            """,
            (project_id,),
        ).fetchall()
        tasks = self.connection.execute(
            """
            SELECT
              task_id, title, status, sort_order, due_at, row_version,
              created_at, updated_at
            FROM workspace_tasks
            WHERE project_id = ?
            ORDER BY sort_order, task_id
            """,
            (project_id,),
        ).fetchall()
        audit_count_row = self.connection.execute(
            """
            SELECT COUNT(*) AS count_value
            FROM audit_events
            WHERE workspace_id = ?
            """,
            (workspace_id,),
        ).fetchone()
        return {
            "project": dict(project),
            "financial_records": [dict(row) for row in finances],
            "artifact_versions": [dict(row) for row in artifacts],
            "tasks": [dict(row) for row in tasks],
            "audit_event_count": int(audit_count_row["count_value"]),
        }

    def workspace_snapshot_hash(self, workspace_id: str) -> str:
        encoded = json.dumps(
            self.workspace_snapshot(workspace_id),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def workspace_business_state_hash(self, workspace_id: str) -> str:
        """Hash durable business rows while allowing expected audit appends."""

        snapshot = self.workspace_snapshot(workspace_id)
        snapshot.pop("audit_event_count")
        encoded = json.dumps(
            snapshot,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class AcceptanceFixture:
    workspace_id: str
    score: int
    financial_record_id: str
    financial_record_type: str
    financial_category: str
    amount_minor: int
    currency: str
    effective_date: str
    source_ref: str | None
    task_id: str
    task_title: str
    task_status: str
    task_sort_order: int
    task_due_at: str | None
    timestamp: str


class StructuredDataService:
    """Validated transaction boundary above :class:`StructuredRepository`."""

    def __init__(self, connection: StructuredStoreConnection) -> None:
        self.connection = connection
        self.repository = StructuredRepository(connection)

    @staticmethod
    def _validate_fixture(fixture: AcceptanceFixture) -> None:
        if type(fixture.score) is not int or not 0 <= fixture.score <= 100:
            raise ValueError("score must be an integer from 0 through 100")
        if fixture.financial_record_type not in FINANCIAL_RECORD_TYPES:
            raise ValueError("unsupported financial record type")
        if not fixture.financial_category.strip():
            raise ValueError("financial category is required")
        if type(fixture.amount_minor) is not int or fixture.amount_minor < 0:
            raise ValueError("amount_minor must be a non-negative integer")
        if CURRENCY_RE.fullmatch(fixture.currency) is None:
            raise ValueError("currency must be an uppercase ISO-style code")
        try:
            date.fromisoformat(fixture.effective_date)
        except ValueError as error:
            raise ValueError("effective_date must be an ISO date") from error
        if fixture.task_status not in TASK_STATUSES:
            raise ValueError("unsupported task status")
        if not fixture.task_title.strip():
            raise ValueError("task title is required")
        if type(fixture.task_sort_order) is not int or fixture.task_sort_order < 0:
            raise ValueError("task_sort_order must be a non-negative integer")

    def apply_acceptance_fixture(
        self,
        fixture: AcceptanceFixture,
    ) -> dict[str, Any]:
        self._validate_fixture(fixture)
        with self.connection.transaction():
            self.repository.set_score(
                workspace_id=fixture.workspace_id,
                score=fixture.score,
                updated_at=fixture.timestamp,
            )
            self.repository.put_financial_record(
                financial_record_id=fixture.financial_record_id,
                workspace_id=fixture.workspace_id,
                record_type=fixture.financial_record_type,
                category=fixture.financial_category,
                amount_minor=fixture.amount_minor,
                currency=fixture.currency,
                effective_date=fixture.effective_date,
                source_ref=fixture.source_ref,
                timestamp=fixture.timestamp,
            )
            self.repository.put_task(
                task_id=fixture.task_id,
                workspace_id=fixture.workspace_id,
                title=fixture.task_title,
                status=fixture.task_status,
                sort_order=fixture.task_sort_order,
                due_at=fixture.task_due_at,
                timestamp=fixture.timestamp,
            )
        return self.repository.workspace_snapshot(fixture.workspace_id)
