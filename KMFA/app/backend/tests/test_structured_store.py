"""S05/P5.1 structured database migration and repository contracts."""

from __future__ import annotations

import sqlite3
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from app import walking_skeleton as skeleton
from app import structured_store
from app.legacy_sqlite_import import read_legacy_snapshot
from app.structured_repository import (
    AcceptanceFixture,
    StructuredDataService,
    StructuredRepository,
)
from app.structured_store import (
    POSTGRESQL_MODE,
    SCHEMA_VERSION,
    StructuredStoreConfigurationError,
    StructuredStoreIntegrityError,
    StructuredStoreMigrationError,
    open_structured_store,
)


@pytest.fixture
def sqlite_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    state = tmp_path / "state"
    monkeypatch.delenv("KMFA_STRUCTURED_DATABASE_MODE", raising=False)
    monkeypatch.delenv("KMFA_STRUCTURED_DATABASE_URL", raising=False)
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(state))
    return state


def _fixture(workspace_id: str, *, score: int = 88) -> AcceptanceFixture:
    return AcceptanceFixture(
        workspace_id=workspace_id,
        score=score,
        financial_record_id="finance_synthetic_001",
        financial_record_type="budget",
        financial_category="synthetic acceptance fixture",
        amount_minor=123_456,
        currency="CNY",
        effective_date="2026-07-23",
        source_ref="synthetic://s05-p51",
        task_id="task_synthetic_001",
        task_title="Verify shared structured persistence",
        task_status="in_progress",
        task_sort_order=10,
        task_due_at="2026-07-30T00:00:00Z",
        timestamp="2026-07-23T00:00:00Z",
    )


def test_default_sqlite_migrates_to_version_four_with_required_tables(
    sqlite_state: Path,
):
    connection = skeleton._open_store()
    try:
        tables = {
            str(row["name"])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert connection.schema_version() == SCHEMA_VERSION == 4
        assert {
            "projects",
            "project_metrics",
            "financial_records",
            "artifact_versions",
            "workspace_tasks",
            "consistency_operations",
            "consistency_outbox",
            "consistency_effect_receipts",
            "consistency_trace",
            "object_quarantine",
            "restore_drill_proofs",
            "workspace_retention",
            "legal_holds",
            "deletion_requests",
            "deletion_object_targets",
            "publication_bindings",
            "lifecycle_events",
            "schema_migrations",
        } <= tables
        migrations = connection.execute(
            "SELECT version, name, length(sha256) AS digest_length "
            "FROM schema_migrations ORDER BY version"
        ).fetchall()
        assert [dict(row) for row in migrations] == [
            {
                "version": 1,
                "name": "0001_legacy_walking_skeleton.sql",
                "digest_length": 64,
            },
            {
                "version": 2,
                "name": "0002_structured_data.sql",
                "digest_length": 64,
            },
            {
                "version": 3,
                "name": "0003_consistency_state.sql",
                "digest_length": 64,
            },
            {
                "version": 4,
                "name": "0004_retention_backup_restore.sql",
                "digest_length": 64,
            },
        ]
    finally:
        connection.close()


def test_legacy_v1_database_is_expand_migrated_and_backfilled(
    sqlite_state: Path,
):
    sqlite_state.mkdir(parents=True)
    database = sqlite_state / "walking_skeleton.sqlite3"
    legacy_schema = (
        Path(skeleton.__file__).resolve().parents[1]
        / "migrations"
        / "sqlite"
        / "0001_legacy_walking_skeleton.sql"
    ).read_text(encoding="utf-8")
    raw = sqlite3.connect(database)
    raw.executescript(legacy_schema)
    raw.execute(
        """
        INSERT INTO workspaces(
          workspace_id, recovery_hash, project_name, progress, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "ws_" + "a" * 22,
            "b" * 64,
            "Legacy synthetic project",
            42,
            "2026-07-20T00:00:00Z",
            "2026-07-21T00:00:00Z",
        ),
    )
    raw.execute(
        """
        INSERT INTO artifacts(
          artifact_id, workspace_id, object_name, original_name,
          reported_media_type, size_bytes, sha256, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "artifact_legacy_synthetic",
            "ws_" + "a" * 22,
            "legacy-synthetic.blob",
            "legacy.fixture",
            "application/octet-stream",
            17,
            "c" * 64,
            "2026-07-21T00:00:00Z",
        ),
    )
    raw.execute("PRAGMA user_version=1")
    raw.commit()
    raw.close()

    connection = skeleton._open_store()
    try:
        repository = StructuredRepository(connection)
        projection = repository.workspace_projection("ws_" + "a" * 22)
        artifact = repository.latest_artifact_version("ws_" + "a" * 22)
        assert connection.schema_version() == SCHEMA_VERSION == 4
        assert projection["project_name"] == "Legacy synthetic project"
        assert projection["progress"] == 42
        assert projection["score"] is None
        assert artifact["artifact_id"] == "artifact_legacy_synthetic"
        assert artifact["version_number"] == 1
        assert artifact["sha256"] == "c" * 64
        retention = connection.execute(
            """
            SELECT state, created_at, active_deletion_request_id, deleted_at
            FROM workspace_retention
            WHERE workspace_id = ?
            """,
            ("ws_" + "a" * 22,),
        ).fetchone()
        assert dict(retention) == {
            "state": "active",
            "created_at": "2026-07-20T00:00:00Z",
            "active_deletion_request_id": None,
            "deleted_at": None,
        }
    finally:
        connection.close()


def test_applied_migration_checksum_drift_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    copied_migrations = tmp_path / "migrations"
    shutil.copytree(
        Path(structured_store.__file__).resolve().parents[1] / "migrations",
        copied_migrations,
    )
    monkeypatch.setattr(structured_store, "_MIGRATIONS_ROOT", copied_migrations)
    monkeypatch.delenv("KMFA_STRUCTURED_DATABASE_MODE", raising=False)
    database = tmp_path / "checksum.sqlite3"
    connection = open_structured_store(database)
    connection.close()

    migration = copied_migrations / "sqlite" / "0002_structured_data.sql"
    migration.write_text(
        migration.read_text(encoding="utf-8") + "\n-- synthetic drift\n",
        encoding="utf-8",
    )
    structured_store._INITIALIZED_SQLITE_FILES.clear()
    with pytest.raises(StructuredStoreMigrationError):
        open_structured_store(database)


def test_service_fixture_survives_reopen_and_browser_independent_recovery(
    sqlite_state: Path,
):
    created = skeleton._create_workspace("S05 structured synthetic project")
    workspace_id = created["workspace"]["workspace_id"]
    connection = skeleton._open_store()
    try:
        service = StructuredDataService(connection)
        snapshot_before = service.apply_acceptance_fixture(_fixture(workspace_id))
        hash_before = service.repository.workspace_snapshot_hash(workspace_id)
    finally:
        connection.close()

    # A new connection represents an application restart/node replacement.
    reopened = skeleton._open_store()
    try:
        repository = StructuredRepository(reopened)
        snapshot_after = repository.workspace_snapshot(workspace_id)
        hash_after = repository.workspace_snapshot_hash(workspace_id)
    finally:
        reopened.close()

    # Recovery uses the server-side capability after all browser state is gone.
    recovered = skeleton._recover_workspace(created["recovery_code"])
    assert recovered["workspace"]["workspace_id"] == workspace_id
    assert snapshot_before == snapshot_after
    assert hash_before == hash_after
    assert snapshot_after["project"]["score"] == 88
    assert len(snapshot_after["financial_records"]) == 1
    assert len(snapshot_after["tasks"]) == 1


def test_read_only_migration_snapshot_includes_v2_structured_rows(
    sqlite_state: Path,
):
    created = skeleton._create_workspace("Structured source synthetic")
    workspace_id = created["workspace"]["workspace_id"]
    connection = skeleton._open_store()
    try:
        StructuredDataService(connection).apply_acceptance_fixture(
            _fixture(workspace_id, score=73)
        )
    finally:
        connection.close()
    database = sqlite_state / "walking_skeleton.sqlite3"
    before = database.read_bytes()
    snapshot = read_legacy_snapshot(database)
    after = database.read_bytes()
    assert before == after
    assert snapshot["project_metrics"][0]["score"] == 73
    assert len(snapshot["financial_records"]) == 1
    assert len(snapshot["workspace_tasks"]) == 1


def test_constraint_failure_rolls_back_entire_transaction(sqlite_state: Path):
    created = skeleton._create_workspace("Atomic rollback synthetic")
    workspace_id = created["workspace"]["workspace_id"]
    connection = skeleton._open_store()
    try:
        repository = StructuredRepository(connection)
        with pytest.raises(StructuredStoreIntegrityError):
            with connection.transaction():
                repository.set_score(
                    workspace_id=workspace_id,
                    score=91,
                    updated_at="2026-07-23T00:00:00Z",
                )
                connection.execute(
                    """
                    INSERT INTO financial_records(
                      financial_record_id, project_id, record_type, category,
                      amount_minor, currency, effective_date, row_version,
                      created_at, updated_at
                    ) VALUES (?, ?, 'actual', 'invalid synthetic', -1, 'CNY',
                              '2026-07-23', 1, ?, ?)
                    """,
                    (
                        "finance_invalid",
                        "project_" + workspace_id,
                        "2026-07-23T00:00:00Z",
                        "2026-07-23T00:00:00Z",
                    ),
                )
        snapshot = repository.workspace_snapshot(workspace_id)
        assert snapshot["project"]["score"] is None
        assert snapshot["financial_records"] == []
    finally:
        connection.close()


def test_concurrent_writers_are_serialized_without_loss_or_duplicates(
    sqlite_state: Path,
):
    created = skeleton._create_workspace("Concurrent structured synthetic")
    workspace_id = created["workspace"]["workspace_id"]

    def write_task(index: int) -> None:
        connection = skeleton._open_store()
        try:
            with connection.transaction():
                StructuredRepository(connection).put_task(
                    task_id=f"task_concurrent_{index:02d}",
                    workspace_id=workspace_id,
                    title=f"Synthetic task {index}",
                    status="todo",
                    sort_order=index,
                    due_at=None,
                    timestamp="2026-07-23T00:00:00Z",
                )
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(write_task, range(24)))

    connection = skeleton._open_store()
    try:
        tasks = StructuredRepository(connection).workspace_snapshot(workspace_id)[
            "tasks"
        ]
        assert len(tasks) == 24
        assert len({row["task_id"] for row in tasks}) == 24
        assert [row["sort_order"] for row in tasks] == list(range(24))
    finally:
        connection.close()


def test_postgresql_mode_requires_env_only_dsn_and_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("KMFA_STRUCTURED_DATABASE_MODE", POSTGRESQL_MODE)
    monkeypatch.delenv("KMFA_STRUCTURED_DATABASE_URL", raising=False)
    with pytest.raises(StructuredStoreConfigurationError) as missing:
        open_structured_store(tmp_path / "unused.sqlite3")
    assert "URL is required" in str(missing.value)

    monkeypatch.setenv(
        "KMFA_STRUCTURED_DATABASE_URL",
        "file:///must-not-be-used?password=synthetic-secret-canary",
    )
    with pytest.raises(StructuredStoreConfigurationError) as invalid:
        open_structured_store(tmp_path / "unused.sqlite3")
    assert "synthetic-secret-canary" not in str(invalid.value)
