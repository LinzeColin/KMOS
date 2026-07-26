"""Versioned KMFA structured-store adapter for SQLite recovery and PostgreSQL.

`legacy-sqlite` remains the default during the S05 expand phase so an unset or
rolled-back deployment keeps reading the existing v1.5 durable volume.
`postgresql-primary` is opt-in and requires a DSN supplied only through the
runtime environment.  Both backends expose the small DB-API surface used by the
walking skeleton and run the same ordered, checksum-locked schema migrations.

The adapter deliberately serializes explicit write transactions.  SQLite uses
``BEGIN IMMEDIATE``; PostgreSQL takes a transaction-scoped advisory lock.  This
preserves the capacity and session-budget invariants of the existing skeleton
until a later phase introduces narrower row-level concurrency.
"""

from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Sequence

STRUCTURED_DATABASE_MODE_ENV = "KMFA_STRUCTURED_DATABASE_MODE"
STRUCTURED_DATABASE_URL_ENV = "KMFA_STRUCTURED_DATABASE_URL"
SQLITE_MODE = "legacy-sqlite"
POSTGRESQL_MODE = "postgresql-primary"
SUPPORTED_MODES = frozenset({SQLITE_MODE, POSTGRESQL_MODE})
SCHEMA_VERSION = 5

_MIGRATIONS_ROOT = Path(__file__).resolve().parents[1] / "migrations"
_MIGRATION_NAME_RE = re.compile(r"^(?P<version>[0-9]{4})_[a-z0-9_]+\.sql$")
_MIGRATION_THREAD_LOCK = threading.Lock()
_INITIALIZED_SQLITE_FILES: set[tuple[str, int, int]] = set()
_INITIALIZED_POSTGRES_TARGETS: set[str] = set()
_POSTGRES_MIGRATION_LOCK = int.from_bytes(b"KMFA-MIG", byteorder="big")
_POSTGRES_WRITE_LOCK = int.from_bytes(b"KMFA-WRT", byteorder="big")


class StructuredStoreError(RuntimeError):
    """Static, secret-free storage failure surfaced to the application."""


class StructuredStoreConfigurationError(StructuredStoreError):
    """Runtime configuration is missing or fail-closed."""


class StructuredStoreIntegrityError(StructuredStoreError):
    """A database constraint rejected an operation."""


class StructuredStoreMigrationError(StructuredStoreError):
    """A migration is missing, changed after application, or failed."""


def _utc_timestamp() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def configured_mode() -> str:
    mode = os.environ.get(STRUCTURED_DATABASE_MODE_ENV, SQLITE_MODE).strip().lower()
    if mode not in SUPPORTED_MODES:
        raise StructuredStoreConfigurationError(
            "unsupported structured database mode"
        )
    return mode


def _migration_files(backend: str) -> list[tuple[int, str, Path, str]]:
    directory = _MIGRATIONS_ROOT / backend
    rows: list[tuple[int, str, Path, str]] = []
    for path in sorted(directory.glob("*.sql")):
        match = _MIGRATION_NAME_RE.fullmatch(path.name)
        if match is None:
            raise StructuredStoreMigrationError("invalid migration filename")
        payload = path.read_bytes()
        rows.append(
            (
                int(match.group("version")),
                path.name,
                path,
                hashlib.sha256(payload).hexdigest(),
            )
        )
    versions = [row[0] for row in rows]
    if versions != list(range(1, SCHEMA_VERSION + 1)):
        raise StructuredStoreMigrationError("incomplete migration chain")
    return rows


def _sqlite_stat_key(path: Path) -> tuple[str, int, int]:
    stat = path.stat()
    return (str(path), int(stat.st_dev), int(stat.st_ino))


def _sqlite_statements(script: str) -> Iterator[str]:
    statement = ""
    for line in script.splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            cleaned = statement.strip()
            if cleaned:
                yield cleaned
            statement = ""
    if statement.strip():
        raise StructuredStoreMigrationError("incomplete SQLite migration statement")


def _bootstrap_migration_table(connection: Any) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          version INTEGER PRIMARY KEY,
          name TEXT NOT NULL UNIQUE,
          sha256 TEXT NOT NULL,
          applied_at TEXT NOT NULL
        )
        """
    )


def _read_applied_migrations(connection: Any) -> dict[int, tuple[str, str]]:
    return {
        int(row["version"]): (str(row["name"]), str(row["sha256"]))
        for row in connection.execute(
            "SELECT version, name, sha256 FROM schema_migrations ORDER BY version"
        ).fetchall()
    }


def _validate_applied_migrations(
    applied: dict[int, tuple[str, str]],
    migrations: Sequence[tuple[int, str, Path, str]],
) -> None:
    known = {version: (name, digest) for version, name, _, digest in migrations}
    if set(applied) - set(known):
        raise StructuredStoreMigrationError("database schema is newer than runtime")
    for version, identity in applied.items():
        if known.get(version) != identity:
            raise StructuredStoreMigrationError("applied migration checksum mismatch")


def _migrate_sqlite(connection: sqlite3.Connection) -> None:
    migrations = _migration_files("sqlite")
    try:
        connection.execute("BEGIN IMMEDIATE")
        _bootstrap_migration_table(connection)
        applied = _read_applied_migrations(connection)
        _validate_applied_migrations(applied, migrations)
        for version, name, path, digest in migrations:
            if version in applied:
                continue
            for statement in _sqlite_statements(path.read_text(encoding="utf-8")):
                connection.execute(statement)
            connection.execute(
                """
                INSERT INTO schema_migrations(version, name, sha256, applied_at)
                VALUES (?, ?, ?, ?)
                """,
                (version, name, digest, _utc_timestamp()),
            )
        connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        connection.execute("COMMIT")
    except StructuredStoreError:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise
    except sqlite3.Error as error:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise StructuredStoreMigrationError("SQLite migration failed") from error


def _migrate_postgresql(connection: Any) -> None:
    migrations = _migration_files("postgresql")
    try:
        connection.execute("BEGIN")
        connection.execute(
            "SELECT pg_advisory_xact_lock(%s)",
            (_POSTGRES_MIGRATION_LOCK,),
        )
        _bootstrap_migration_table(connection)
        applied = _read_applied_migrations(connection)
        _validate_applied_migrations(applied, migrations)
        for version, name, path, digest in migrations:
            if version in applied:
                continue
            connection.execute(path.read_text(encoding="utf-8"))
            connection.execute(
                """
                INSERT INTO schema_migrations(version, name, sha256, applied_at)
                VALUES (%s, %s, %s, %s)
                """,
                (version, name, digest, _utc_timestamp()),
            )
        connection.execute("COMMIT")
    except StructuredStoreError:
        try:
            connection.execute("ROLLBACK")
        except Exception:
            pass
        raise
    except Exception as error:
        try:
            connection.execute("ROLLBACK")
        except Exception:
            pass
        raise StructuredStoreMigrationError("PostgreSQL migration failed") from error


class StructuredStoreConnection:
    """Backend-neutral subset of the Python DB-API connection contract."""

    def __init__(
        self,
        raw_connection: Any,
        *,
        mode: str,
        database_errors: tuple[type[BaseException], ...],
        integrity_errors: tuple[type[BaseException], ...],
    ) -> None:
        self._raw = raw_connection
        self.mode = mode
        self._database_errors = database_errors
        self._integrity_errors = integrity_errors
        self._explicit_transaction = False

    @property
    def backend_name(self) -> str:
        if self.mode == POSTGRESQL_MODE:
            return "postgresql-shared-service-adapter"
        return "sqlite-durable-volume-adapter"

    @property
    def in_transaction(self) -> bool:
        if self.mode == SQLITE_MODE:
            return bool(self._raw.in_transaction)
        return self._explicit_transaction

    def _sql(self, statement: str) -> str:
        if self.mode == POSTGRESQL_MODE:
            return statement.replace("?", "%s")
        return statement

    def execute(
        self,
        statement: str,
        parameters: Sequence[Any] | None = None,
    ) -> Any:
        normalized = statement.strip().rstrip(";").upper()
        try:
            if normalized in {"BEGIN", "BEGIN IMMEDIATE"}:
                if self.in_transaction:
                    raise StructuredStoreError("nested transaction is not supported")
                if self.mode == POSTGRESQL_MODE:
                    cursor = self._raw.execute("BEGIN")
                    self._explicit_transaction = True
                    self._raw.execute(
                        "SELECT pg_advisory_xact_lock(%s)",
                        (_POSTGRES_WRITE_LOCK,),
                    )
                    return cursor
                cursor = self._raw.execute("BEGIN IMMEDIATE")
                self._explicit_transaction = True
                return cursor
            if normalized == "COMMIT":
                cursor = self._raw.execute("COMMIT")
                self._explicit_transaction = False
                return cursor
            if normalized == "ROLLBACK":
                cursor = self._raw.execute("ROLLBACK")
                self._explicit_transaction = False
                return cursor
            return self._raw.execute(
                self._sql(statement),
                tuple(parameters or ()),
            )
        except self._integrity_errors as error:
            raise StructuredStoreIntegrityError(
                "structured store constraint rejected operation"
            ) from error
        except self._database_errors as error:
            raise StructuredStoreError("structured store operation failed") from error

    def executemany(
        self,
        statement: str,
        parameter_rows: Sequence[Sequence[Any]] | Iterator[Sequence[Any]],
    ) -> Any:
        try:
            if self.mode == SQLITE_MODE:
                return self._raw.executemany(statement, parameter_rows)
            cursor = self._raw.cursor()
            cursor.executemany(self._sql(statement), parameter_rows)
            return cursor
        except self._integrity_errors as error:
            raise StructuredStoreIntegrityError(
                "structured store constraint rejected operation"
            ) from error
        except self._database_errors as error:
            raise StructuredStoreError("structured store operation failed") from error

    def schema_version(self) -> int:
        row = self.execute(
            "SELECT COALESCE(MAX(version), 0) AS schema_version FROM schema_migrations"
        ).fetchone()
        return int(row["schema_version"])

    @contextmanager
    def transaction(self) -> Iterator["StructuredStoreConnection"]:
        self.execute("BEGIN IMMEDIATE")
        try:
            yield self
            self.execute("COMMIT")
        except BaseException:
            if self.in_transaction:
                self.execute("ROLLBACK")
            raise

    def close(self) -> None:
        self._raw.close()


def _open_sqlite(path: Path) -> StructuredStoreConnection:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(
            str(path),
            isolation_level=None,
            timeout=5,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("PRAGMA foreign_keys=ON")
        key = _sqlite_stat_key(path)
        with _MIGRATION_THREAD_LOCK:
            if key not in _INITIALIZED_SQLITE_FILES:
                connection.execute("PRAGMA journal_mode=WAL")
                _migrate_sqlite(connection)
                path.chmod(0o600)
                _INITIALIZED_SQLITE_FILES.add(key)
        connection.execute("PRAGMA synchronous=FULL")
        return StructuredStoreConnection(
            connection,
            mode=SQLITE_MODE,
            database_errors=(sqlite3.Error,),
            integrity_errors=(sqlite3.IntegrityError,),
        )
    except StructuredStoreError:
        if connection is not None:
            connection.close()
        raise
    except (OSError, sqlite3.Error) as error:
        if connection is not None:
            connection.close()
        raise StructuredStoreError("SQLite structured store unavailable") from error


def _open_postgresql(database_url: str) -> StructuredStoreConnection:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as error:
        raise StructuredStoreConfigurationError(
            "PostgreSQL driver is unavailable"
        ) from error

    target_fingerprint = hashlib.sha256(database_url.encode("utf-8")).hexdigest()
    connection = None
    try:
        connection = psycopg.connect(
            database_url,
            autocommit=True,
            connect_timeout=5,
            row_factory=dict_row,
            application_name="kmfa-public-app",
        )
        connection.execute("SET lock_timeout = '5s'")
        connection.execute("SET statement_timeout = '10s'")
        connection.execute("SET idle_in_transaction_session_timeout = '15s'")
        with _MIGRATION_THREAD_LOCK:
            if target_fingerprint not in _INITIALIZED_POSTGRES_TARGETS:
                _migrate_postgresql(connection)
                _INITIALIZED_POSTGRES_TARGETS.add(target_fingerprint)
        return StructuredStoreConnection(
            connection,
            mode=POSTGRESQL_MODE,
            database_errors=(psycopg.Error,),
            integrity_errors=(psycopg.IntegrityError,),
        )
    except StructuredStoreError:
        if connection is not None:
            connection.close()
        raise
    except Exception as error:
        if connection is not None:
            connection.close()
        raise StructuredStoreError("PostgreSQL structured store unavailable") from error


def open_structured_store(sqlite_path: Path) -> StructuredStoreConnection:
    mode = configured_mode()
    if mode == SQLITE_MODE:
        return _open_sqlite(sqlite_path.resolve())

    database_url = os.environ.get(STRUCTURED_DATABASE_URL_ENV, "").strip()
    if not database_url:
        raise StructuredStoreConfigurationError(
            "PostgreSQL structured database URL is required"
        )
    if not database_url.startswith(("postgresql://", "postgres://")):
        raise StructuredStoreConfigurationError(
            "PostgreSQL structured database URL has invalid scheme"
        )
    return _open_postgresql(database_url)
