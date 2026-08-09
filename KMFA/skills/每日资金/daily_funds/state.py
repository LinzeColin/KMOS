"""OVH-local, non-authoritative runtime journal and redacted status surface."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
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


@dataclass(frozen=True)
class OcrProfileDecision:
    """Values-free result of a two-business-day OCR layout calibration."""

    ready_before: bool
    ready_after: bool
    distinct_business_days: int


class RuntimeState:
    """A small SQLite journal: cursors, locks, inbox, idempotency, outbox and values-free observer receipts only."""

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
                CREATE TABLE IF NOT EXISTS network_events (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  service TEXT NOT NULL,
                  operation TEXT NOT NULL,
                  outcome TEXT NOT NULL,
                  occurred_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS network_events_lookup
                  ON network_events(service, operation, outcome, occurred_at);
                CREATE TABLE IF NOT EXISTS parser_evidence (
                  attachment_sha256 TEXT NOT NULL,
                  family TEXT NOT NULL,
                  suffix TEXT NOT NULL,
                  declared_mime TEXT,
                  magic TEXT NOT NULL,
                  parser_version TEXT NOT NULL,
                  opened_at TEXT NOT NULL,
                  PRIMARY KEY(attachment_sha256, family)
                );
                CREATE TABLE IF NOT EXISTS capability_evidence (
                  attachment_sha256 TEXT NOT NULL,
                  family TEXT NOT NULL,
                  suffix TEXT NOT NULL,
                  declared_mime TEXT,
                  magic TEXT NOT NULL,
                  parser_version TEXT NOT NULL,
                  outcome TEXT NOT NULL,
                  code TEXT NOT NULL,
                  observed_at TEXT NOT NULL,
                  PRIMARY KEY(attachment_sha256, family, parser_version)
                );
                CREATE TABLE IF NOT EXISTS ocr_profile_observations (
                  family TEXT NOT NULL,
                  layout_fingerprint TEXT NOT NULL,
                  parser_version TEXT NOT NULL,
                  business_date TEXT NOT NULL,
                  observed_at TEXT NOT NULL,
                  PRIMARY KEY(family, layout_fingerprint, parser_version, business_date)
                );
                CREATE TABLE IF NOT EXISTS observer_days (
                  business_date TEXT PRIMARY KEY,
                  publication_id TEXT NOT NULL,
                  observed_at TEXT NOT NULL,
                  comparison_state TEXT NOT NULL,
                  coverage_state TEXT NOT NULL,
                  amount_state TEXT NOT NULL,
                  threshold_state TEXT NOT NULL,
                  retrieval_state TEXT NOT NULL,
                  duplicate_state TEXT NOT NULL,
                  backup_state TEXT NOT NULL,
                  restore_state TEXT NOT NULL,
                  latency_minutes INTEGER
                );
                CREATE INDEX IF NOT EXISTS observer_days_observed_at
                  ON observer_days(observed_at);
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
        # ``commit_cursor(None)`` deliberately retains the KV key as an empty
        # value.  Daily-funds stores only a DWS continuation cursor (which can
        # be opaque) here, never a raw message, attachment, or source payload.
        return self.get(key) or None

    def commit_cursor(self, cursor: str | None, key: str = "history_next_cursor") -> None:
        # The non-secret DWS continuation cursor is state, not a publication.
        # It is only advanced at the end of a fully persisted batch by the
        # poller.
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

    def reusable_raw_attachment_sha(self, message_id_hash: str, attachment_index: int) -> str | None:
        """Return one previously verified raw object for a repeated occurrence.

        The live poll intentionally overlaps its prior 30 minutes.  A media
        URL in an already-archived DingTalk message can expire before that
        overlap is fetched again, but a previous successful Git persistence is
        still only reusable when it has one unambiguous durable receipt.  Any
        malformed, conflicting, or non-terminal receipt falls back to the
        normal source-download path instead of guessing.
        """

        if (
            not isinstance(message_id_hash, str)
            or len(message_id_hash) != 64
            or any(character not in "0123456789abcdef" for character in message_id_hash)
            or not isinstance(attachment_index, int)
            or isinstance(attachment_index, bool)
            or attachment_index < 0
        ):
            return None
        with self.connection() as connection:
            rows = connection.execute(
                """SELECT attachment_sha256,state FROM inbox
                   WHERE message_id_hash=? AND occurrence_key LIKE ?""",
                (message_id_hash, f"{message_id_hash}:{attachment_index}:%"),
            ).fetchall()
        if len(rows) != 1:
            return None
        attachment_sha256 = str(rows[0]["attachment_sha256"] or "")
        state = str(rows[0]["state"] or "")
        if (
            len(attachment_sha256) != 64
            or any(character not in "0123456789abcdef" for character in attachment_sha256)
            or state not in {"GIT_PERSISTED", "ARCHIVED_CAPABILITY_RECORDED", "VALID_PUBLISHED"}
        ):
            return None
        return attachment_sha256

    def record_run(self, run_id: str, kind: str, state: str, code: str, *, finished: bool = False) -> None:
        now = iso_now()
        with self.connection() as connection:
            connection.execute(
                """INSERT INTO runs(run_id,kind,state,code,started_at,finished_at) VALUES(?,?,?,?,?,?)
                ON CONFLICT(run_id) DO UPDATE SET state=excluded.state,code=excluded.code,finished_at=excluded.finished_at""",
                (run_id, _safe_code(kind), _safe_code(state), _safe_code(code), now, now if finished else None),
            )

    def record_network_event(self, service: str, operation: str, outcome: str) -> None:
        """Record a values-free external-operation receipt for runtime audit.

        URLs, identifiers, payloads and command output never enter this table:
        the evidence is limited to a fixed service/operation/outcome triplet.
        """

        cutoff = (utc_now() - timedelta(days=35)).isoformat(timespec="seconds").replace("+00:00", "Z")
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO network_events(service,operation,outcome,occurred_at) VALUES(?,?,?,?)",
                (_safe_code(service), _safe_code(operation), _safe_code(outcome), iso_now()),
            )
            # This is derived operational telemetry, not source data.  Keep
            # enough history for the five-workday observer while preventing
            # the non-authoritative OVH SQLite journal from growing forever.
            connection.execute("DELETE FROM network_events WHERE occurred_at < ?", (cutoff,))

    def record_parser_evidence(
        self,
        *,
        attachment_sha256: str,
        family: str,
        suffix: str,
        declared_mime: str | None,
        magic: str,
        parser_version: str,
    ) -> None:
        """Record a real raw-readback parser-open receipt without source values.

        Callers invoke this only after the attachment has been re-opened from
        the private sparse clone and the parser has completed.  The SHA is the
        join key to the private raw manifest; no filename, group ID, account,
        message content or attachment bytes enter the local journal.
        """

        if len(attachment_sha256) != 64 or any(character not in "0123456789abcdef" for character in attachment_sha256):
            raise ValueError("invalid parser evidence hash")
        if not all(isinstance(value, str) and value for value in (family, suffix, magic, parser_version)):
            raise ValueError("invalid parser evidence")
        if declared_mime is not None and (not isinstance(declared_mime, str) or not declared_mime):
            raise ValueError("invalid parser evidence MIME")
        with self.connection() as connection:
            connection.execute(
                """INSERT INTO parser_evidence(
                       attachment_sha256,family,suffix,declared_mime,magic,parser_version,opened_at
                   ) VALUES(?,?,?,?,?,?,?)
                   ON CONFLICT(attachment_sha256,family) DO UPDATE SET
                       suffix=excluded.suffix,
                       declared_mime=excluded.declared_mime,
                       magic=excluded.magic,
                       parser_version=excluded.parser_version,
                       opened_at=excluded.opened_at""",
                (attachment_sha256, family, suffix, declared_mime, magic, parser_version, iso_now()),
            )

    def record_capability_evidence(
        self,
        *,
        attachment_sha256: str,
        family: str,
        suffix: str,
        declared_mime: str | None,
        magic: str,
        parser_version: str,
        outcome: str,
        code: str,
    ) -> None:
        """Persist a values-free real-attachment capability receipt.

        Unlike ``parser_evidence``, this records unsupported types as
        ``NEEDS_REVIEW`` after the worker has read their bytes back from the
        private Git authority.  The per-attachment SHA stays in the protected
        journal; projections use :meth:`capability_matrix`, which aggregates
        away that join key.
        """

        if len(attachment_sha256) != 64 or any(character not in "0123456789abcdef" for character in attachment_sha256):
            raise ValueError("invalid capability evidence hash")
        if not all(isinstance(value, str) and value and len(value) <= 128 for value in (family, suffix, magic, parser_version)):
            raise ValueError("invalid capability evidence")
        if any(ord(character) < 32 for value in (family, suffix, magic, parser_version) for character in value):
            raise ValueError("invalid capability evidence")
        if declared_mime is not None and (
            not isinstance(declared_mime, str)
            or not declared_mime
            or len(declared_mime) > 128
            or not declared_mime.isascii()
        ):
            raise ValueError("invalid capability evidence MIME")
        if outcome not in {"SUPPORTED", "NEEDS_REVIEW"}:
            raise ValueError("invalid capability outcome")
        safe_code = _safe_code(code)
        if safe_code == "UNKNOWN":
            raise ValueError("invalid capability evidence code")
        with self.connection() as connection:
            connection.execute(
                """INSERT INTO capability_evidence(
                       attachment_sha256,family,suffix,declared_mime,magic,parser_version,outcome,code,observed_at
                   ) VALUES(?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(attachment_sha256,family,parser_version) DO UPDATE SET
                       suffix=excluded.suffix,
                       declared_mime=excluded.declared_mime,
                       magic=excluded.magic,
                       outcome=excluded.outcome,
                       code=excluded.code,
                       observed_at=excluded.observed_at""",
                (attachment_sha256, family, suffix, declared_mime, magic, parser_version, outcome, safe_code, iso_now()),
            )

    def capability_matrix(self, *, parser_version: str | None = None) -> list[dict[str, Any]]:
        """Return a values-free aggregate for the protected KMFA status UI.

        When a parser version is supplied, it is an *evidence validity*
        filter, not a destructive migration: older receipts remain in the
        protected journal for audit but cannot assert support for changed
        parsing rules.
        """

        if parser_version is not None and (
            not isinstance(parser_version, str)
            or not parser_version
            or len(parser_version) > 128
            or any(ord(character) < 32 for character in parser_version)
        ):
            raise ValueError("invalid capability parser version")

        with self.connection() as connection:
            rows = connection.execute(
                """SELECT family,suffix,declared_mime,magic,parser_version,outcome,code,
                          COUNT(*) AS count,MAX(observed_at) AS last_observed_at
                   FROM capability_evidence
                   WHERE (? IS NULL OR parser_version = ?)
                   GROUP BY family,suffix,declared_mime,magic,parser_version,outcome,code
                   ORDER BY family,suffix,declared_mime,magic,parser_version,outcome,code""",
                (parser_version, parser_version),
            ).fetchall()
        return [
            {
                "family": str(row["family"]),
                "suffix": str(row["suffix"]),
                "declared_mime": None if row["declared_mime"] is None else str(row["declared_mime"]),
                "magic": _safe_code(row["magic"]),
                "parser_version": str(row["parser_version"]),
                "outcome": _safe_code(row["outcome"]),
                "code": _safe_code(row["code"]),
                "count": int(row["count"]),
                "last_observed_at": str(row["last_observed_at"]),
            }
            for row in rows
        ]

    def observe_ocr_layout(
        self,
        *,
        family: str,
        layout_fingerprint: str,
        parser_version: str,
        business_date: date,
    ) -> OcrProfileDecision:
        """Record one redacted layout observation and enforce the calibration gate.

        A deterministic OCR open alone is not a production template.  The
        first two distinct business dates merely establish that a layout has
        repeated.  Only a later attachment with the already-calibrated layout
        can enter the regular parse/reconciliation path; all earlier samples
        remain capability evidence, not publishable money facts.
        """

        if (
            not isinstance(family, str)
            or not family
            or len(family) > 128
            or any(ord(character) < 32 for character in family)
        ):
            raise ValueError("invalid OCR profile family")
        if (
            not isinstance(layout_fingerprint, str)
            or len(layout_fingerprint) != 64
            or any(character not in "0123456789abcdef" for character in layout_fingerprint)
        ):
            raise ValueError("invalid OCR layout fingerprint")
        if (
            not isinstance(parser_version, str)
            or not parser_version
            or len(parser_version) > 128
            or any(ord(character) < 32 for character in parser_version)
        ):
            raise ValueError("invalid OCR parser version")
        if not isinstance(business_date, date) or isinstance(business_date, datetime):
            raise ValueError("invalid OCR business date")
        business_date_text = business_date.isoformat()
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                before = connection.execute(
                    """SELECT COUNT(*) FROM ocr_profile_observations
                       WHERE family=? AND layout_fingerprint=? AND parser_version=?""",
                    (family, layout_fingerprint, parser_version),
                ).fetchone()[0]
                connection.execute(
                    """INSERT OR IGNORE INTO ocr_profile_observations(
                           family,layout_fingerprint,parser_version,business_date,observed_at
                       ) VALUES(?,?,?,?,?)""",
                    (family, layout_fingerprint, parser_version, business_date_text, iso_now()),
                )
                after = connection.execute(
                    """SELECT COUNT(*) FROM ocr_profile_observations
                       WHERE family=? AND layout_fingerprint=? AND parser_version=?""",
                    (family, layout_fingerprint, parser_version),
                ).fetchone()[0]
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise
        return OcrProfileDecision(
            ready_before=int(before) >= 2,
            ready_after=int(after) >= 2,
            distinct_business_days=int(after),
        )

    def network_ledger_summary(self) -> list[dict[str, Any]]:
        """Return aggregate, values-free network evidence for the protected UI."""

        with self.connection() as connection:
            rows = connection.execute(
                """SELECT service,operation,outcome,COUNT(*) AS count,MAX(occurred_at) AS last_occurred_at
                   FROM network_events
                   GROUP BY service,operation,outcome
                   ORDER BY service,operation,outcome"""
            ).fetchall()
        return [
            {
                "service": _safe_code(row["service"]),
                "operation": _safe_code(row["operation"]),
                "outcome": _safe_code(row["outcome"]),
                "count": int(row["count"]),
                "last_occurred_at": str(row["last_occurred_at"]),
            }
            for row in rows
        ]

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

    def observer_window(self) -> dict[str, str] | None:
        """Return the current deployment-bound shadow-observation window.

        The values are values-free: the marker is already a SHA-256 digest of
        a container-instance token, never a raw hostname, deployment ID or
        source revision.  A missing/corrupt window deliberately has no
        implicit default because that could make a carried-over five-day count
        look like evidence for a new deployment.
        """

        keys = (
            "observer_deployment_marker",
            "observer_baseline_business_date",
            "observer_started_at",
        )
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT key,value FROM kv WHERE key IN (?,?,?)", keys
            ).fetchall()
        values = {str(row["key"]): str(row["value"]) for row in rows}
        marker = values.get("observer_deployment_marker")
        baseline = values.get("observer_baseline_business_date")
        started_at = values.get("observer_started_at")
        if (
            not marker
            or len(marker) != 64
            or any(character not in "0123456789abcdef" for character in marker)
            or not baseline
            or not started_at
        ):
            return None
        try:
            date.fromisoformat(baseline)
            datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        except ValueError:
            return None
        return {
            "deployment_marker": marker,
            "baseline_business_date": baseline,
            "started_at": started_at,
        }

    def begin_observer_window(
        self,
        *,
        deployment_marker: str,
        baseline_business_date: str,
        started_at: str,
    ) -> None:
        """Reset shadow comparisons only for a new container deployment.

        A deployment's first validated publication is a baseline, not one of
        the five post-deploy business-day comparisons.  The reset and the
        marker update are one SQLite transaction, so a restart cannot retain
        old comparisons under a new deployment marker.
        """

        if (
            len(deployment_marker) != 64
            or any(character not in "0123456789abcdef" for character in deployment_marker)
        ):
            raise ValueError("invalid observer deployment marker")
        try:
            date.fromisoformat(baseline_business_date)
            datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("invalid observer window") from exc
        now = iso_now()
        rows = (
            ("observer_deployment_marker", deployment_marker),
            ("observer_baseline_business_date", baseline_business_date),
            ("observer_started_at", started_at),
        )
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM observer_days")
            connection.executemany(
                """INSERT INTO kv(key,value,updated_at) VALUES(?,?,?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at""",
                ((key, value, now) for key, value in rows),
            )
            connection.execute("COMMIT")

    def record_observer_day(
        self,
        *,
        business_date: str,
        publication_id: str,
        comparison_state: str,
        coverage_state: str,
        amount_state: str,
        threshold_state: str,
        retrieval_state: str,
        duplicate_state: str,
        backup_state: str,
        restore_state: str,
        latency_minutes: int | None,
        observed_at: str,
    ) -> None:
        """Upsert one real, verified business-date comparison without values.

        The unique key is the source-validated business date rather than a
        cron invocation.  Re-running the observer for the same publication
        date refreshes evidence but cannot fabricate progress toward five
        post-deploy business days.
        """

        try:
            date.fromisoformat(business_date)
        except ValueError as exc:
            raise ValueError("invalid observer business date") from exc
        if (
            len(publication_id) != 64
            or any(character not in "0123456789abcdef" for character in publication_id)
        ):
            raise ValueError("invalid observer publication")
        if latency_minutes is not None and (
            isinstance(latency_minutes, bool)
            or not isinstance(latency_minutes, int)
            or latency_minutes < 0
            or latency_minutes > 60 * 24 * 31
        ):
            raise ValueError("invalid observer latency")
        try:
            datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("invalid observer timestamp") from exc
        states = (
            comparison_state,
            coverage_state,
            amount_state,
            threshold_state,
            retrieval_state,
            duplicate_state,
            backup_state,
            restore_state,
        )
        if any(not isinstance(value, str) or not value for value in states):
            raise ValueError("invalid observer state")
        values = tuple(_safe_code(value) for value in states)
        with self.connection() as connection:
            connection.execute(
                """INSERT INTO observer_days(
                     business_date,publication_id,observed_at,comparison_state,
                     coverage_state,amount_state,threshold_state,retrieval_state,
                     duplicate_state,backup_state,restore_state,latency_minutes
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(business_date) DO UPDATE SET
                     publication_id=excluded.publication_id,
                     observed_at=excluded.observed_at,
                     comparison_state=excluded.comparison_state,
                     coverage_state=excluded.coverage_state,
                     amount_state=excluded.amount_state,
                     threshold_state=excluded.threshold_state,
                     retrieval_state=excluded.retrieval_state,
                     duplicate_state=excluded.duplicate_state,
                     backup_state=excluded.backup_state,
                     restore_state=excluded.restore_state,
                     latency_minutes=excluded.latency_minutes""",
                (business_date, publication_id, observed_at, *values, latency_minutes),
            )
            # The worker journal is rebuildable operational telemetry.  Keep
            # a bounded tail that comfortably covers the five-day observer
            # while preventing it becoming a second long-term evidence store.
            connection.execute(
                """DELETE FROM observer_days
                   WHERE business_date NOT IN (
                     SELECT business_date FROM observer_days
                     ORDER BY business_date DESC LIMIT 35
                   )"""
            )

    def observer_days(self, *, limit: int = 5) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 35:
            raise ValueError("invalid observer limit")
        with self.connection() as connection:
            rows = connection.execute(
                """SELECT business_date,observed_at,comparison_state,coverage_state,
                          amount_state,threshold_state,retrieval_state,duplicate_state,
                          backup_state,restore_state,latency_minutes
                   FROM observer_days
                   ORDER BY business_date DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        # Return chronological order: it is easier for the existing status
        # center to summarize, while the SQL query still bounds the newest N.
        return [
            {
                "business_date": str(row["business_date"]),
                "observed_at": str(row["observed_at"]),
                "comparison_state": _safe_code(row["comparison_state"]),
                "coverage_state": _safe_code(row["coverage_state"]),
                "amount_state": _safe_code(row["amount_state"]),
                "threshold_state": _safe_code(row["threshold_state"]),
                "retrieval_state": _safe_code(row["retrieval_state"]),
                "duplicate_state": _safe_code(row["duplicate_state"]),
                "backup_state": _safe_code(row["backup_state"]),
                "restore_state": _safe_code(row["restore_state"]),
                "latency_minutes": None if row["latency_minutes"] is None else int(row["latency_minutes"]),
            }
            for row in reversed(rows)
        ]


class StatusWriter:
    """The only runtime-to-KMFA status hand-off; it contains no raw source."""

    SCHEDULES = {
        "history_poll": "*/15 * * * * Asia/Shanghai",
        "auth_probe": "* * * * * Asia/Shanghai",
        "keepalive": "0 * * * * Asia/Shanghai",
        "backfill": "5,20,35,50 * * * * Asia/Shanghai",
        "observer": "30 3 * * * Asia/Shanghai",
        "r2_guard": "0 */6 * * * Asia/Shanghai",
        "cold_backup": "10 4 * * * Asia/Shanghai",
        "raw_archive_audit": "20 5 * * * Asia/Shanghai",
        "runtime_audit": "45 5 * * * Asia/Shanghai",
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
