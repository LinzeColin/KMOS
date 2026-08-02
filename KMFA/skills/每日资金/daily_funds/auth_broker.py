"""One-time, Cloudflare-Access-mediated DWS device authorization broker.

This module is intentionally narrower than a remote shell: the KMFA private
app can only request, observe, or cancel *one* DWS device authorization for
the daily-funds container's own DWS volume.  It cannot pass a command, a
profile, a group ID, a token, or any raw financial input across the control
volume.
"""

from __future__ import annotations

import json
import re
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from .config import DailyFundsConfig
from .ingestion import DwsDevicePrompt, DwsHistoryClient, IngestionError
from .state import RuntimeState, atomic_json_write, iso_now

UTC = timezone.utc

REQUEST_SCHEMA = "kmfa.daily_funds.dws_auth_request.v1"
SESSION_SCHEMA = "kmfa.daily_funds.dws_auth_session.v1"
REQUEST_FILE = "dws_auth_request.json"
SESSION_FILE = "dws_auth_session.json"
ACTOR = "kmfa_private_owner_ui"
LIVE_STATES = frozenset({"REQUESTED", "AWAITING_APPROVAL", "CANCELLING"})
TERMINAL_STATES = frozenset({"SUCCEEDED", "FAILED", "EXPIRED", "CANCELLED"})
ALL_STATES = LIVE_STATES | TERMINAL_STATES
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class AuthRequest:
    request_id: str
    action: str
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


class DailyFundsAuthBroker:
    """Serve only explicit owner-UI device-auth requests from the control volume."""

    def __init__(self, config: DailyFundsConfig | None = None, *, poll_seconds: float = 0.5):
        self.config = config or DailyFundsConfig.from_env()
        self.state = RuntimeState(self.config.state_dir)
        self.poll_seconds = max(0.1, min(float(poll_seconds), 5.0))
        self._guard = threading.Lock()
        self._active_request_id: str | None = None
        self._active_cancel: threading.Event | None = None
        self._active_thread: threading.Thread | None = None
        self._active_holder: str | None = None

    @property
    def _control_root(self) -> Path:
        self.config.control_dir.mkdir(parents=True, exist_ok=True)
        return self.config.control_dir.resolve()

    def _path(self, name: str) -> Path:
        if name not in {REQUEST_FILE, SESSION_FILE}:
            raise ValueError("invalid auth control filename")
        root = self._control_root
        target = (root / name).resolve()
        if target.parent != root:
            raise ValueError("invalid auth control path")
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
    def _request_from_payload(payload: Mapping[str, Any], *, now: datetime) -> AuthRequest | None:
        if set(payload) != {"schema_version", "request_id", "action", "actor", "requested_at", "expires_at"}:
            return None
        request_id = payload.get("request_id")
        action = payload.get("action")
        requested_at = _parse_timestamp(payload.get("requested_at"))
        expires_at = _parse_timestamp(payload.get("expires_at"))
        if (
            payload.get("schema_version") != REQUEST_SCHEMA
            or not isinstance(request_id, str)
            or _HEX64_RE.fullmatch(request_id) is None
            or action not in {"START", "CANCEL"}
            or payload.get("actor") != ACTOR
            or requested_at is None
            or expires_at is None
            or requested_at > now + timedelta(minutes=2)
            or requested_at < now - timedelta(hours=1)
            or expires_at <= requested_at
            or (expires_at - requested_at).total_seconds() > 660
        ):
            return None
        return AuthRequest(
            request_id=request_id,
            action=str(action),
            requested_at=requested_at,
            expires_at=expires_at,
        )

    def _write_session(
        self,
        request: AuthRequest,
        *,
        state: str,
        machine_code: str,
        prompt: DwsDevicePrompt | None = None,
    ) -> None:
        if state not in ALL_STATES:
            raise ValueError("invalid auth session state")
        if state == "AWAITING_APPROVAL" and prompt is None:
            raise ValueError("device prompt required")
        if state != "AWAITING_APPROVAL" and prompt is not None:
            raise ValueError("device prompt forbidden")
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
                # These are short-lived device-flow values, never durable
                # status fields.  Terminal records deliberately erase both.
                "authorization_url": prompt.authorization_url if prompt else None,
                "user_code": prompt.user_code if prompt else None,
            },
        )

    def _delete_request_if_matching(self, request_id: str) -> None:
        payload = self._read_object(REQUEST_FILE)
        if payload is not None and payload.get("request_id") == request_id:
            try:
                self._path(REQUEST_FILE).unlink()
            except FileNotFoundError:
                pass

    def _is_active(self, request_id: str) -> bool:
        with self._guard:
            return self._active_request_id == request_id and self._active_thread is not None

    def _begin(self, request: AuthRequest) -> None:
        if self._is_active(request.request_id):
            return
        holder = uuid.uuid4().hex
        if not self.state.acquire_lease("dws_bootstrap_lock", holder, ttl_seconds=780):
            self._write_session(request, state="REQUESTED", machine_code="DWS_BOOTSTRAP_LOCK_HELD")
            return
        cancel = threading.Event()
        thread = threading.Thread(
            target=self._run_device_auth,
            args=(request, cancel, holder),
            name="daily-funds-dws-auth",
            daemon=True,
        )
        with self._guard:
            self._active_request_id = request.request_id
            self._active_cancel = cancel
            self._active_thread = thread
            self._active_holder = holder
        self._write_session(request, state="REQUESTED", machine_code="DWS_AUTH_BOOTSTRAP_STARTING")
        thread.start()

    def _run_device_auth(self, request: AuthRequest, cancel: threading.Event, holder: str) -> None:
        client = DwsHistoryClient(self.config, event_sink=self.state.record_network_event)

        def cancelled_or_expired() -> bool:
            return cancel.is_set() or datetime.now(UTC) >= request.expires_at

        def receive_prompt(prompt: DwsDevicePrompt) -> None:
            if cancelled_or_expired():
                raise IngestionError("DWS_AUTH_BOOTSTRAP_CANCELLED")
            self._write_session(request, state="AWAITING_APPROVAL", machine_code="DWS_AUTH_WAITING_OWNER", prompt=prompt)

        try:
            outcome = client.bootstrap_device_auth_with_prompt(
                receive_prompt,
                cancel_requested=cancelled_or_expired,
                max_wait_seconds=660,
            )
            if datetime.now(UTC) >= request.expires_at:
                self._write_session(request, state="EXPIRED", machine_code="DWS_AUTH_BOOTSTRAP_EXPIRED")
            elif cancel.is_set():
                self._write_session(request, state="CANCELLED", machine_code="DWS_AUTH_BOOTSTRAP_CANCELLED")
            else:
                code = "DWS_AUTH_ALREADY_READY" if outcome == "ALREADY_READY" else "DWS_BOOTSTRAP_READY"
                self._write_session(request, state="SUCCEEDED", machine_code=code)
        except IngestionError as exc:
            code = _safe_machine_code(exc.code)
            if datetime.now(UTC) >= request.expires_at or code == "DWS_AUTH_BOOTSTRAP_EXPIRED":
                self._write_session(request, state="EXPIRED", machine_code="DWS_AUTH_BOOTSTRAP_EXPIRED")
            elif cancel.is_set() or code == "DWS_AUTH_BOOTSTRAP_CANCELLED":
                self._write_session(request, state="CANCELLED", machine_code="DWS_AUTH_BOOTSTRAP_CANCELLED")
            else:
                self.state.queue_incident(code)
                self._write_session(request, state="FAILED", machine_code=code)
        finally:
            self.state.release_lease("dws_bootstrap_lock", holder)
            self._delete_request_if_matching(request.request_id)
            with self._guard:
                if self._active_request_id == request.request_id:
                    self._active_request_id = None
                    self._active_cancel = None
                    self._active_thread = None
                    self._active_holder = None

    def run_once(self) -> None:
        """Advance at most one fixed-format request; never execute input text."""

        now = datetime.now(UTC)
        payload = self._read_object(REQUEST_FILE)
        if payload is None:
            return
        request = self._request_from_payload(payload, now=now)
        if request is None:
            # The App writes only the strict schema.  A malformed shared-volume
            # payload is ignored and removed instead of becoming an execution
            # primitive or a reflected diagnostic.
            try:
                self._path(REQUEST_FILE).unlink()
            except FileNotFoundError:
                pass
            return
        if request.expires_at <= now:
            with self._guard:
                cancel = self._active_cancel if self._active_request_id == request.request_id else None
            if cancel is not None:
                cancel.set()
            self._write_session(request, state="EXPIRED", machine_code="DWS_AUTH_BOOTSTRAP_EXPIRED")
            if cancel is None:
                self._delete_request_if_matching(request.request_id)
            return
        if request.action == "CANCEL":
            with self._guard:
                cancel = self._active_cancel if self._active_request_id == request.request_id else None
            if cancel is None:
                self._write_session(request, state="CANCELLED", machine_code="DWS_AUTH_BOOTSTRAP_CANCELLED")
                self._delete_request_if_matching(request.request_id)
            else:
                cancel.set()
                self._write_session(request, state="CANCELLING", machine_code="DWS_AUTH_BOOTSTRAP_CANCELLING")
            return
        self._begin(request)

    def serve_forever(self) -> None:
        """Run a private control loop without emitting any terminal output."""

        while True:
            self.run_once()
            time.sleep(self.poll_seconds)
