"""One-shot, values-free DWS history probe for the isolated cloud slice.

This is deliberately a diagnostic control plane, not a second collector and
not a remote shell.  The private KMFA app may enqueue exactly one fixed probe;
the request contains no command, source identifier, cursor, time range, or
financial input.  The broker first uses only the slice's configured DWS
identity against a fixed recent window.  If that page is recordless, it may
retry the *same exact-group history interface* without time bounds and return
only a small enum-only receipt.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from .config import ConfigError, DailyFundsConfig
from .ingestion import DwsHistoryClient, IngestionError
from .state import RuntimeState, atomic_json_write, iso_now

UTC = timezone.utc

REQUEST_SCHEMA = "kmfa.daily_funds.dws_history_probe_request.v1"
SESSION_SCHEMA = "kmfa.daily_funds.dws_history_probe_session.v1"
REQUEST_FILE = "dws_history_probe_request.json"
SESSION_FILE = "dws_history_probe_session.json"
ACTOR = "kmfa_private_owner_ui"
LIVE_STATES = frozenset({"REQUESTED", "RUNNING"})
TERMINAL_STATES = frozenset({"COMPLETED", "FAILED", "EXPIRED"})
ALL_STATES = LIVE_STATES | TERMINAL_STATES
CONTINUATION_STATES = frozenset({
    "NOT_STARTED",
    "FIRST_PAGE_TERMINAL",
    "SECOND_PAGE_TERMINAL",
    "SECOND_PAGE_CONTINUES",
    "GROUP_HISTORY_FALLBACK_FIRST_PAGE_TERMINAL",
    "GROUP_HISTORY_FALLBACK_SECOND_PAGE_TERMINAL",
    "GROUP_HISTORY_FALLBACK_SECOND_PAGE_CONTINUES",
})
CURSOR_TRANSCRIPTS = {
    "NOT_STARTED": "NOT_STARTED",
    "FIRST_PAGE_TERMINAL": "FIRST_PAGE_TERMINAL",
    "SECOND_PAGE_TERMINAL": "OPAQUE_CURSOR_REUSED_SECOND_PAGE_TERMINAL",
    "SECOND_PAGE_CONTINUES": "OPAQUE_CURSOR_REUSED_SECOND_PAGE_CONTINUES",
    "GROUP_HISTORY_FALLBACK_FIRST_PAGE_TERMINAL": "GROUP_HISTORY_FALLBACK_FIRST_PAGE_TERMINAL",
    "GROUP_HISTORY_FALLBACK_SECOND_PAGE_TERMINAL": "GROUP_HISTORY_FALLBACK_OPAQUE_CURSOR_REUSED_SECOND_PAGE_TERMINAL",
    "GROUP_HISTORY_FALLBACK_SECOND_PAGE_CONTINUES": "GROUP_HISTORY_FALLBACK_OPAQUE_CURSOR_REUSED_SECOND_PAGE_CONTINUES",
}
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class HistoryProbeRequest:
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


def _safe_machine_code(value: object) -> str:
    token = "".join(
        character
        for character in str(value or "UNKNOWN").strip().upper()
        if character.isascii() and (character.isupper() or character.isdigit() or character == "_")
    )
    return token[:80] or "UNKNOWN"


class DailyFundsHistoryProbeBroker:
    """Execute only the fixed, Access-gated, values-free history probe."""

    def __init__(self, config: DailyFundsConfig | None = None, *, poll_seconds: float = 0.5):
        self.config = config or DailyFundsConfig.from_env()
        self.state = RuntimeState(self.config.state_dir)
        self.poll_seconds = max(0.1, min(float(poll_seconds), 5.0))

    @property
    def _control_root(self) -> Path:
        self.config.control_dir.mkdir(parents=True, exist_ok=True)
        return self.config.control_dir.resolve()

    def _path(self, name: str) -> Path:
        if name not in {REQUEST_FILE, SESSION_FILE}:
            raise ValueError("invalid history probe control filename")
        root = self._control_root
        target = (root / name).resolve()
        if target.parent != root:
            raise ValueError("invalid history probe control path")
        return target

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
    def _request_from_payload(payload: Mapping[str, Any], *, now: datetime) -> HistoryProbeRequest | None:
        if set(payload) != {"schema_version", "request_id", "action", "actor", "requested_at", "expires_at"}:
            return None
        request_id = payload.get("request_id")
        requested_at = _parse_timestamp(payload.get("requested_at"))
        expires_at = _parse_timestamp(payload.get("expires_at"))
        if (
            payload.get("schema_version") != REQUEST_SCHEMA
            or not isinstance(request_id, str)
            or _HEX64_RE.fullmatch(request_id) is None
            or payload.get("action") != "PROBE"
            or payload.get("actor") != ACTOR
            or requested_at is None
            or expires_at is None
            or requested_at > now + timedelta(minutes=2)
            or requested_at < now - timedelta(hours=1)
            or expires_at <= requested_at
            or (expires_at - requested_at).total_seconds() > 660
        ):
            return None
        return HistoryProbeRequest(
            request_id=request_id,
            requested_at=requested_at,
            expires_at=expires_at,
        )

    def _write_session(
        self,
        request: HistoryProbeRequest,
        *,
        state: str,
        machine_code: str,
        continuation_state: str,
    ) -> None:
        if state not in ALL_STATES:
            raise ValueError("invalid history probe state")
        if continuation_state not in CONTINUATION_STATES:
            raise ValueError("invalid history probe continuation state")
        atomic_json_write(
            self._path(SESSION_FILE),
            {
                "schema_version": SESSION_SCHEMA,
                "request_id": request.request_id,
                "state": state,
                "machine_code": _safe_machine_code(machine_code),
                "created_at": _timestamp(request.requested_at),
                "updated_at": iso_now(),
                "expires_at": _timestamp(request.expires_at),
                "continuation_state": continuation_state,
                # This proves only the control-flow fact that page one's
                # opaque cursor was used for page two.  The cursor itself is
                # never persisted, logged, or returned through the API.
                "cursor_transcript": CURSOR_TRANSCRIPTS[continuation_state],
            },
        )

    def _delete_request_if_matching(self, request_id: str) -> None:
        payload = self._read_object(REQUEST_FILE)
        if payload is not None and payload.get("request_id") == request_id:
            try:
                self._path(REQUEST_FILE).unlink()
            except FileNotFoundError:
                pass

    def _record_probe_network_event(self, _service: str, operation: str, outcome: str) -> None:
        """Keep one-off diagnostics out of the scheduled-collector receipts."""

        self.state.record_network_event("DWS_HISTORY_PROBE", operation, outcome)

    def _run_probe(self, request: HistoryProbeRequest) -> None:
        """Probe the current window, then a same-source fallback if necessary.

        A page that has ``hasMore=false`` but no explicit records list is not
        proof of an empty current day.  It must not be made into a zero result
        or a cursor advance.  The only diagnostic retry is the documented
        group-only form of the same opaque-cursor history interface; its
        contents and cursor remain entirely in process memory.
        """

        self.config.validate(include_storage=False)
        now = datetime.now(UTC)
        if now >= request.expires_at:
            self._write_session(
                request,
                state="EXPIRED",
                machine_code="DWS_HISTORY_PROBE_EXPIRED",
                continuation_state="NOT_STARTED",
            )
            return
        self._write_session(
            request,
            state="RUNNING",
            machine_code="DWS_HISTORY_PROBE_RUNNING",
            continuation_state="NOT_STARTED",
        )
        client = DwsHistoryClient(self.config, event_sink=self._record_probe_network_event)
        start = now - timedelta(hours=24)
        fallback_used = False
        try:
            first = client.search(start, now, None)
        except IngestionError as exc:
            if exc.code != "DWS_PAGE_RECORDS_MISSING":
                raise
            # DWS v1.0.52 permits ``search-advanced`` with the configured
            # conversation alone.  Do not substitute the boundary-based
            # message-list API or a remote sender filter.
            fallback_used = True
            first = client.search(None, None, None)
        if not first.has_more:
            self._write_session(
                request,
                state="COMPLETED",
                machine_code="DWS_HISTORY_PROBE_COMPLETED",
                continuation_state=(
                    "GROUP_HISTORY_FALLBACK_FIRST_PAGE_TERMINAL"
                    if fallback_used else "FIRST_PAGE_TERMINAL"
                ),
            )
            return
        if not first.next_cursor:
            raise IngestionError("DWS_HISTORY_PROBE_CURSOR_MISSING")
        if datetime.now(UTC) >= request.expires_at:
            self._write_session(
                request,
                state="EXPIRED",
                machine_code="DWS_HISTORY_PROBE_EXPIRED",
                continuation_state="NOT_STARTED",
            )
            return
        second = client.search(None, None, first.next_cursor) if fallback_used else client.search(start, now, first.next_cursor)
        if fallback_used:
            continuation_state = (
                "GROUP_HISTORY_FALLBACK_SECOND_PAGE_CONTINUES"
                if second.has_more else "GROUP_HISTORY_FALLBACK_SECOND_PAGE_TERMINAL"
            )
        else:
            continuation_state = "SECOND_PAGE_CONTINUES" if second.has_more else "SECOND_PAGE_TERMINAL"
        self._write_session(
            request,
            state="COMPLETED",
            machine_code="DWS_HISTORY_PROBE_COMPLETED",
            continuation_state=continuation_state,
        )

    def run_once(self) -> None:
        """Advance one strict request; malformed volume data is never executed."""

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
        if request.expires_at <= now:
            self._write_session(
                request,
                state="EXPIRED",
                machine_code="DWS_HISTORY_PROBE_EXPIRED",
                continuation_state="NOT_STARTED",
            )
            self._delete_request_if_matching(request.request_id)
            return

        holder = uuid.uuid4().hex
        if not self.state.acquire_lease("dws_history_probe_lock", holder, ttl_seconds=600):
            self._write_session(
                request,
                state="REQUESTED",
                machine_code="DWS_HISTORY_PROBE_LOCK_HELD",
                continuation_state="NOT_STARTED",
            )
            return
        try:
            self._run_probe(request)
        except ConfigError:
            self._write_session(
                request,
                state="FAILED",
                machine_code="CONFIG_INVALID",
                continuation_state="NOT_STARTED",
            )
        except IngestionError as exc:
            state = "EXPIRED" if datetime.now(UTC) >= request.expires_at else "FAILED"
            self._write_session(
                request,
                state=state,
                machine_code="DWS_HISTORY_PROBE_EXPIRED" if state == "EXPIRED" else _safe_machine_code(exc.code),
                continuation_state="NOT_STARTED",
            )
        except Exception:
            self._write_session(
                request,
                state="FAILED",
                machine_code="DWS_HISTORY_PROBE_UNHANDLED",
                continuation_state="NOT_STARTED",
            )
        finally:
            self.state.release_lease("dws_history_probe_lock", holder)
            self._delete_request_if_matching(request.request_id)

    def serve_forever(self) -> None:
        """Run the fixed control loop without a terminal transcript."""

        while True:
            self.run_once()
            time.sleep(self.poll_seconds)
