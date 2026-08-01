"""OVH-local, non-authoritative runtime journal and redacted status surface."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from .contracts import HUMAN_STATUSES

UTC = timezone.utc


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso_now() -> str:
    return utc_now().isoformat(timespec="seconds").replace("+00:00", "Z")


def _safe_code(value: object) -> str:
    text = str(value or "UNKNOWN").strip().upper()
    filtered = "".join(char for char in text if char.isascii() and (char.isupper() or char.isdigit() or char == "_"))
    return filtered[:80] or "UNKNOWN"


def atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@dataclass(frozen=True)
class RuntimeStatus:
    human_status: str
    machine_code: str
    effective_business_date: str | None
    last_verified_at: str | None
    publication_id: str | None
    updated_at: str
    schedules: dict[str, str]
    backup_state: str

    def public_json(self) -> dict[str, Any]:
        if self.human_status not in HUMAN_STATUSES:
            raise ValueError("invalid daily-funds human status")
        return {
            "schema_version": "kmfa.daily_funds.status.v1",
            "human_status": self.human_status,
            "machine_code": _safe_code(self.machine_code),
            "effective_business_date": self.effective_business_date,
            "last_verified_at": self.last_verified_at,
            "publication_id": self.publication_id,
            "updated_at": self.updated_at,
            "schedules": dict(sorted(self.schedules.items())),
            "backup_state": _safe_code(self.backup_state),
        }


class RuntimeState:
    """A small SQLite journal: cursors, locks, inbox, idempotency and outbox only."""

    def __init__(self, state_dir: str | Path):
        self.root = Path(state_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "daily_funds.sqlite3"
        self._initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path, timeout=15, isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self.connection() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA foreign_keys=ON;
                CREATE TABLE IF NOT EXISTS kv (
                  key TEXT PRIMARY KEY,
                  value TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS leases (
                  name TEXT PRIMARY KEY,
                  holder TEXT NOT NULL,
                  expires_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS inbox (
                  occurrence_key TEXT PRIMARY KEY,
                  message_id_hash TEXT NOT NULL,
                  attachment_sha256 TEXT,
                  state TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS outbox (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  event_code TEXT NOT NULL,
                  dedupe_key TEXT NOT NULL UNIQUE,
                  state TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                  run_id TEXT PRIMARY KEY,
                  kind TEXT NOT NULL,
                  state TEXT NOT NULL,
                  code TEXT NOT NULL,
                  started_at TEXT NOT NULL,
                  finished_at TEXT
                );
                """
            )

    def get(self, key: str) -> str | None:
        with self.connection() as connection:
            row = connection.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
            return None if row is None else str(row["value"])

    def put(self, key: str, value: str) -> None:
        with self.connection() as connection:
            connection.execute(
                """INSERT INTO kv(key,value,updated_at) VALUES(?,?,?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at""",
                (key, value, iso_now()),
            )

    def get_cursor(self, key: str = "history_next_cursor") -> str | None:
        return self.get(key)

    def commit_cursor(self, cursor: str | None, key: str = "history_next_cursor") -> None:
        # An opaque cursor is state, not a publication.  It is only advanced at
        # the end of a fully persisted batch by the poller.
        self.put(key, cursor or "")

    def acquire_lease(self, name: str, holder: str, *, ttl_seconds: int) -> bool:
        now = utc_now()
        expires = now + timedelta(seconds=ttl_seconds)
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT holder,expires_at FROM leases WHERE name=?", (name,)).fetchone()
            allowed = row is None or datetime.fromisoformat(str(row["expires_at"]).replace("Z", "+00:00")) <= now
            if allowed:
                connection.execute(
                    """INSERT INTO leases(name,holder,expires_at,updated_at) VALUES(?,?,?,?)
                    ON CONFLICT(name) DO UPDATE SET holder=excluded.holder,expires_at=excluded.expires_at,updated_at=excluded.updated_at""",
                    (name, holder, expires.isoformat().replace("+00:00", "Z"), iso_now()),
                )
            connection.execute("COMMIT")
            return allowed

    def release_lease(self, name: str, holder: str) -> None:
        with self.connection() as connection:
            connection.execute("DELETE FROM leases WHERE name=? AND holder=?", (name, holder))

    def note_inbox(self, occurrence_key: str, message_id_hash: str, attachment_sha256: str | None, state: str) -> bool:
        now = iso_now()
        with self.connection() as connection:
            try:
                connection.execute(
                    "INSERT INTO inbox(occurrence_key,message_id_hash,attachment_sha256,state,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                    (occurrence_key, message_id_hash, attachment_sha256, _safe_code(state), now, now),
                )
                return True
            except sqlite3.IntegrityError:
                connection.execute("UPDATE inbox SET updated_at=? WHERE occurrence_key=?", (now, occurrence_key))
                return False

    def mark_inbox(self, occurrence_key: str, state: str) -> None:
        with self.connection() as connection:
            connection.execute("UPDATE inbox SET state=?,updated_at=? WHERE occurrence_key=?", (_safe_code(state), iso_now(), occurrence_key))

    def record_run(self, run_id: str, kind: str, state: str, code: str, *, finished: bool = False) -> None:
        now = iso_now()
        with self.connection() as connection:
            connection.execute(
                """INSERT INTO runs(run_id,kind,state,code,started_at,finished_at) VALUES(?,?,?,?,?,?)
                ON CONFLICT(run_id) DO UPDATE SET state=excluded.state,code=excluded.code,finished_at=excluded.finished_at""",
                (run_id, _safe_code(kind), _safe_code(state), _safe_code(code), now, now if finished else None),
            )

    def queue_incident(self, code: str, *, cooldown_minutes: int = 360) -> bool:
        """Deduplicate noisy auth incidents without sending any message itself."""

        # Bucket in a cooldown-sized block.  The former hour-formatted key
        # accidentally opened six incidents during the frozen 360 minute
        # cooldown, violating the task-pack's anti-noise contract.
        dedupe_key = f"{_safe_code(code)}:{int(utc_now().timestamp() // (cooldown_minutes * 60))}"
        now = iso_now()
        with self.connection() as connection:
            try:
                connection.execute(
                    "INSERT INTO outbox(event_code,dedupe_key,state,created_at,updated_at) VALUES(?,?,?,?,?)",
                    (_safe_code(code), dedupe_key, "PENDING", now, now),
                )
                return True
            except sqlite3.IntegrityError:
                return False


class StatusWriter:
    """The only runtime-to-KMFA status hand-off; it contains no raw source."""

    SCHEDULES = {
        "history_poll": "*/15 * * * * Asia/Shanghai",
        "auth_probe": "* * * * * Asia/Shanghai",
        "keepalive": "0 * * * * Asia/Shanghai",
        "backfill": "15 2 * * * Asia/Shanghai",
        "observer": "30 3 * * * Asia/Shanghai",
        "cold_backup": "10 4 * * * Asia/Shanghai",
        "restore_drill": "0 5 1 * * Asia/Shanghai",
    }

    def __init__(self, publication_dir: str | Path):
        self.root = Path(publication_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "status.json"

    def write(
        self,
        human_status: str,
        machine_code: str,
        *,
        effective_business_date: str | None = None,
        last_verified_at: str | None = None,
        publication_id: str | None = None,
        backup_state: str = "UNKNOWN",
    ) -> dict[str, Any]:
        status = RuntimeStatus(
            human_status=human_status,
            machine_code=machine_code,
            effective_business_date=effective_business_date,
            last_verified_at=last_verified_at,
            publication_id=publication_id,
            updated_at=iso_now(),
            schedules=self.SCHEDULES,
            backup_state=backup_state,
        ).public_json()
        atomic_json_write(self.path, status)
        return status

    def read(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if payload.get("human_status") not in HUMAN_STATUSES:
            return None
        return payload
