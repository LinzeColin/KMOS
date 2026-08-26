"""Fixed, values-free recovery broker for the isolated daily-funds worker.

The owner-facing control plane can request one and only one recovery sequence:
audit the private raw archive, repair exact historical coverage, then replay
only verified account/transaction pairs.  It deliberately accepts neither a
command nor any source, date, financial, storage, or credential input.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from .config import ConfigError, DailyFundsConfig
from .runtime import DailyFundsRuntime
from .state import atomic_json_write, iso_now

UTC = timezone.utc

REQUEST_SCHEMA = "kmfa.daily_funds.recovery_request.v1"
SESSION_SCHEMA = "kmfa.daily_funds.recovery_session.v1"
REQUEST_FILE = "daily_funds_recovery_request.json"
SESSION_FILE = "daily_funds_recovery_session.json"
ACTOR = "kmfa_private_owner_ui"
STEPS = ("RAW_ARCHIVE_AUDIT", "RAW_COVERAGE_REPAIR", "RAW_FACT_REPLAY")
LIVE_STATES = frozenset({"REQUESTED", "RUNNING", "WAITING"})
TERMINAL_STATES = frozenset({"SUCCEEDED", "FAILED", "EXPIRED"})
ALL_STATES = LIVE_STATES | TERMINAL_STATES
MACHINE_CODES = frozenset({
    "DAILY_FUNDS_RECOVERY_NOT_REQUESTED",
    "DAILY_FUNDS_RECOVERY_QUEUED",
    "DAILY_FUNDS_RECOVERY_RUNNING",
    "DAILY_FUNDS_RECOVERY_WAITING_FOR_LOCK",
    "DAILY_FUNDS_RECOVERY_PUBLISHED",
    "DAILY_FUNDS_RECOVERY_PUBLISHED_NEEDS_REVIEW",
    "DAILY_FUNDS_RECOVERY_AUDIT_FAILED",
    "DAILY_FUNDS_RECOVERY_AUDIT_TRANSPORT_UNAVAILABLE",
    "DAILY_FUNDS_RECOVERY_AUDIT_SOURCE_MISSING",
    "DAILY_FUNDS_RECOVERY_AUDIT_CENSUS_LIMIT",
    "DAILY_FUNDS_RECOVERY_AUDIT_INTEGRITY_NEEDS_REVIEW",
    "DAILY_FUNDS_RECOVERY_COVERAGE_FAILED",
    "DAILY_FUNDS_RECOVERY_NO_COMPLETE_PAIR",
    "DAILY_FUNDS_RECOVERY_REPLAY_FAILED",
    "DAILY_FUNDS_RECOVERY_CONFIG_INVALID",
    "DAILY_FUNDS_RECOVERY_EXPIRED",
    "DAILY_FUNDS_RECOVERY_UNHANDLED",
})
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
# The recovery worker owns a fixed, server-side transaction after the control
# request is accepted.  Its lifetime must cover a complete private archive
# audit and remains independent from the short-lived Access credential used to
# enqueue it.
RECOVERY_MAX_SECONDS = 6 * 60 * 60


class RecoveryProcessLockHeld(Exception):
    """The one recovery worker already owns the automatically released lock."""


@dataclass(frozen=True)
class DailyFundsRecoveryRequest:
    request_id: str
    requested_at: datetime
    expires_at: datetime


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _completed_steps(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, list) or any(not isinstance(step, str) for step in value):
        return None
    completed = tuple(value)
    return completed if completed == STEPS[:len(completed)] else None


class DailyFundsRecoveryBroker:
    """Execute the fixed recovery chain through a strict shared-volume request."""

    def __init__(self, config: DailyFundsConfig | None = None, *, poll_seconds: float = 0.5):
        self.config = config or DailyFundsConfig.from_env()
        self.poll_seconds = max(0.1, min(float(poll_seconds), 5.0))

    @property
    def _control_root(self) -> Path:
        self.config.control_dir.mkdir(parents=True, exist_ok=True)
        return self.config.control_dir.resolve()

    def _path(self, name: str) -> Path:
        if name not in {REQUEST_FILE, SESSION_FILE}:
            raise ValueError("invalid recovery control filename")
        root = self._control_root
        target = (root / name).resolve()
        if target.parent != root:
            raise ValueError("invalid recovery control path")
        return target

    @contextmanager
    def _recovery_process_lock(self):
        """Serialize recovery in the worker-only state volume.

        A private archive audit can run for hours.  Its coordination lock must
        disappear with a replaced daily-funds container, so a new deployment
        can resume the fixed request without waiting for a stale durable lease.
        """

        self.config.state_dir.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            self.config.state_dir / "daily_funds_recovery.lock",
            os.O_CREAT | os.O_RDWR,
            0o600,
        )
        locked = False
        try:
            os.fchmod(descriptor, 0o600)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RecoveryProcessLockHeld from exc
            locked = True
            yield
        finally:
            try:
                if locked:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)

    def _read_object(self, name: str) -> dict[str, Any] | None:
        target = self._path(name)
        if target.is_symlink() or not target.is_file():
            return None
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return dict(payload) if isinstance(payload, Mapping) else None

    @staticmethod
    def _request_from_payload(payload: Mapping[str, Any], *, now: datetime) -> DailyFundsRecoveryRequest | None:
        if set(payload) != {"schema_version", "request_id", "action", "actor", "requested_at", "expires_at"}:
            return None
        request_id = payload.get("request_id")
        requested_at = _parse_timestamp(payload.get("requested_at"))
        expires_at = _parse_timestamp(payload.get("expires_at"))
        if (
            payload.get("schema_version") != REQUEST_SCHEMA
            or not isinstance(request_id, str)
            or _HEX64_RE.fullmatch(request_id) is None
            or payload.get("action") != "RECOVER"
            or payload.get("actor") != ACTOR
            or requested_at is None
            or expires_at is None
            or requested_at > now + timedelta(minutes=2)
            or requested_at < now - timedelta(seconds=RECOVERY_MAX_SECONDS)
            or expires_at <= requested_at
            or (expires_at - requested_at).total_seconds() > RECOVERY_MAX_SECONDS
        ):
            return None
        return DailyFundsRecoveryRequest(
            request_id=request_id,
            requested_at=requested_at,
            expires_at=expires_at,
        )

    def _read_session(self, request: DailyFundsRecoveryRequest) -> tuple[str, ...]:
        payload = self._read_object(SESSION_FILE)
        if not isinstance(payload, Mapping) or set(payload) != {
            "schema_version", "request_id", "state", "machine_code", "created_at", "updated_at", "expires_at",
            "completed_steps", "active_step",
        }:
            return ()
        completed = _completed_steps(payload.get("completed_steps"))
        if completed is None:
            return ()
        created_at = _parse_timestamp(payload.get("created_at"))
        expires_at = _parse_timestamp(payload.get("expires_at"))
        active_step = payload.get("active_step")
        next_step = "NONE" if len(completed) == len(STEPS) else STEPS[len(completed)]
        if (
            payload.get("schema_version") != SESSION_SCHEMA
            or payload.get("request_id") != request.request_id
            or payload.get("state") not in ALL_STATES
            or payload.get("machine_code") not in MACHINE_CODES
            or created_at != request.requested_at
            or expires_at != request.expires_at
            or _parse_timestamp(payload.get("updated_at")) is None
            or active_step != next_step
        ):
            return ()
        return completed

    def _write_session(
        self,
        request: DailyFundsRecoveryRequest,
        *,
        state: str,
        machine_code: str,
        completed_steps: tuple[str, ...],
        active_step: str,
    ) -> None:
        expected_step = "NONE" if len(completed_steps) == len(STEPS) else STEPS[len(completed_steps)]
        if (
            state not in ALL_STATES
            or machine_code not in MACHINE_CODES
            or completed_steps != STEPS[:len(completed_steps)]
            or active_step != expected_step
        ):
            raise ValueError("invalid recovery session")
        atomic_json_write(
            self._path(SESSION_FILE),
            {
                "schema_version": SESSION_SCHEMA,
                "request_id": request.request_id,
                "state": state,
                "machine_code": machine_code,
                "created_at": _timestamp(request.requested_at),
                "updated_at": iso_now(),
                "expires_at": _timestamp(request.expires_at),
                "completed_steps": list(completed_steps),
                "active_step": active_step,
            },
        )

    def _delete_request_if_matching(self, request_id: str) -> None:
        payload = self._read_object(REQUEST_FILE)
        if payload is not None and payload.get("request_id") == request_id:
            try:
                self._path(REQUEST_FILE).unlink()
            except FileNotFoundError:
                pass

    @staticmethod
    def _next_step(completed: tuple[str, ...]) -> str:
        return "NONE" if len(completed) == len(STEPS) else STEPS[len(completed)]

    @staticmethod
    def _result_code(result: object) -> str | None:
        if not isinstance(result, Mapping):
            return None
        code = result.get("code") or result.get("machine_code")
        return code if isinstance(code, str) else None

    @staticmethod
    def _is_ok(result: object, expected_codes: set[str]) -> bool:
        return (
            isinstance(result, Mapping)
            and result.get("ok") is True
            and DailyFundsRecoveryBroker._result_code(result) in expected_codes
        )

    @staticmethod
    def _is_lock_held(result: object) -> bool:
        code = DailyFundsRecoveryBroker._result_code(result)
        return code is not None and code.endswith("_LOCK_HELD")

    @staticmethod
    def _failure_code(step: str, result: object) -> str:
        code = DailyFundsRecoveryBroker._result_code(result)
        if code == "CONFIG_INVALID":
            return "DAILY_FUNDS_RECOVERY_CONFIG_INVALID"
        if step == "RAW_ARCHIVE_AUDIT":
            return {
                "RAW_ARCHIVE_AUDIT_TRANSPORT_UNAVAILABLE": "DAILY_FUNDS_RECOVERY_AUDIT_TRANSPORT_UNAVAILABLE",
                "RAW_ARCHIVE_AUDIT_SOURCE_MISSING": "DAILY_FUNDS_RECOVERY_AUDIT_SOURCE_MISSING",
                "RAW_ARCHIVE_AUDIT_CENSUS_LIMIT": "DAILY_FUNDS_RECOVERY_AUDIT_CENSUS_LIMIT",
                "RAW_ARCHIVE_AUDIT_INTEGRITY_NEEDS_REVIEW": "DAILY_FUNDS_RECOVERY_AUDIT_INTEGRITY_NEEDS_REVIEW",
            }.get(code, "DAILY_FUNDS_RECOVERY_AUDIT_FAILED")
        if step == "RAW_COVERAGE_REPAIR":
            return "DAILY_FUNDS_RECOVERY_COVERAGE_FAILED"
        if code == "RAW_FACT_REPLAY_NO_COMPLETE_PAIR":
            return "DAILY_FUNDS_RECOVERY_NO_COMPLETE_PAIR"
        return "DAILY_FUNDS_RECOVERY_REPLAY_FAILED"

    @staticmethod
    def _run_step(runtime: DailyFundsRuntime, step: str) -> object:
        if step == "RAW_ARCHIVE_AUDIT":
            return runtime.raw_archive_metadata_audit()
        if step == "RAW_COVERAGE_REPAIR":
            return runtime.raw_coverage_repair(now=datetime.now(UTC))
        if step == "RAW_FACT_REPLAY":
            return runtime.raw_fact_replay(now=datetime.now(UTC))
        raise ValueError("invalid recovery step")

    @staticmethod
    def _success_codes(step: str) -> set[str]:
        return {
            "RAW_ARCHIVE_AUDIT": {"RAW_ARCHIVE_AUDITED", "RAW_ARCHIVE_AUDIT_NEEDS_REVIEW"},
            "RAW_COVERAGE_REPAIR": {"RAW_COVERAGE_REPAIRED", "RAW_COVERAGE_VERIFIED"},
            "RAW_FACT_REPLAY": {"RAW_FACT_REPLAY_PUBLISHED", "RAW_FACT_REPLAY_PUBLISHED_NEEDS_REVIEW"},
        }[step]

    def run_once(self) -> None:
        """Advance one fixed recovery request; malformed input is discarded."""

        now = datetime.now(UTC)
        payload = self._read_object(REQUEST_FILE)
        if payload is None:
            return
        request = self._request_from_payload(payload, now=now)
        if request is None:
            try:
                self._path(REQUEST_FILE).unlink()
            except FileNotFoundError:
                pass
            return
        completed = self._read_session(request)
        if request.expires_at <= now:
            self._write_session(
                request,
                state="EXPIRED",
                machine_code="DAILY_FUNDS_RECOVERY_EXPIRED",
                completed_steps=completed,
                active_step=self._next_step(completed),
            )
            self._delete_request_if_matching(request.request_id)
            return

        terminal = False
        try:
            with self._recovery_process_lock():
                runtime = DailyFundsRuntime(self.config)
                replay_result: object = None
                for step in STEPS[len(completed):]:
                    if datetime.now(UTC) >= request.expires_at:
                        self._write_session(
                            request,
                            state="EXPIRED",
                            machine_code="DAILY_FUNDS_RECOVERY_EXPIRED",
                            completed_steps=completed,
                            active_step=step,
                        )
                        terminal = True
                        return
                    self._write_session(
                        request,
                        state="RUNNING",
                        machine_code="DAILY_FUNDS_RECOVERY_RUNNING",
                        completed_steps=completed,
                        active_step=step,
                    )
                    result = self._run_step(runtime, step)
                    if step == "RAW_FACT_REPLAY":
                        replay_result = result
                    if self._is_lock_held(result):
                        self._write_session(
                            request,
                            state="WAITING",
                            machine_code="DAILY_FUNDS_RECOVERY_WAITING_FOR_LOCK",
                            completed_steps=completed,
                            active_step=step,
                        )
                        return
                    if not self._is_ok(result, self._success_codes(step)):
                        self._write_session(
                            request,
                            state="FAILED",
                            machine_code=self._failure_code(step, result),
                            completed_steps=completed,
                            active_step=step,
                        )
                        terminal = True
                        return
                    completed = (*completed, step)
                final_code = (
                    "DAILY_FUNDS_RECOVERY_PUBLISHED_NEEDS_REVIEW"
                    if self._result_code(replay_result) == "RAW_FACT_REPLAY_PUBLISHED_NEEDS_REVIEW"
                    else "DAILY_FUNDS_RECOVERY_PUBLISHED"
                )
                self._write_session(
                    request,
                    state="SUCCEEDED",
                    machine_code=final_code,
                    completed_steps=completed,
                    active_step="NONE",
                )
                terminal = True
        except RecoveryProcessLockHeld:
            self._write_session(
                request,
                state="WAITING",
                machine_code="DAILY_FUNDS_RECOVERY_WAITING_FOR_LOCK",
                completed_steps=completed,
                active_step=self._next_step(completed),
            )
        except ConfigError:
            self._write_session(
                request,
                state="FAILED",
                machine_code="DAILY_FUNDS_RECOVERY_CONFIG_INVALID",
                completed_steps=completed,
                active_step=self._next_step(completed),
            )
            terminal = True
        except Exception:
            self._write_session(
                request,
                state="FAILED",
                machine_code="DAILY_FUNDS_RECOVERY_UNHANDLED",
                completed_steps=completed,
                active_step=self._next_step(completed),
            )
            terminal = True
        finally:
            if terminal:
                self._delete_request_if_matching(request.request_id)

    def serve_forever(self) -> None:
        """Run the fixed recovery control loop without emitting a transcript."""

        while True:
            self.run_once()
            time.sleep(self.poll_seconds)


def has_live_recovery_request(
    config: DailyFundsConfig,
    *,
    now: datetime | None = None,
) -> bool:
    """Return whether a valid unexpired recovery request owns the startup audit.

    Recovery begins with a complete raw-archive metadata audit before later
    reopening formal candidates. One valid live request therefore reserves the
    archive-audit lock for the recovery broker and keeps a rolling deployment
    from starting a competing reader on the same worker volume.
    """

    moment = now or datetime.now(UTC)
    broker = DailyFundsRecoveryBroker(config)
    payload = broker._read_object(REQUEST_FILE)
    if payload is None:
        return False
    request = broker._request_from_payload(payload, now=moment)
    return request is not None and request.expires_at > moment
