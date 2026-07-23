"""S04/P4.4 bounded anonymous abuse control.

The public product must not replace abuse prevention with an account wall.  This
module therefore applies four independent, persistent budgets (IP, device,
workspace and global), holds operation concurrency leases for the complete ASGI
response, and offers a one-use proof-of-work challenge when only an actor-local
budget is exhausted.  Global and concurrency budgets are never challenge
bypassable.

Operational state is deliberately separate from the walking-skeleton business
database.  It stores only keyed hashes and bounded aggregates: no raw IP,
device cookie, workspace ID, session, filename or recovery capability.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import json
import logging
import os
import re
import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

API_PREFIX = "/public-api/walking-skeleton/v1"
POLICY_VERSION = "p44-v1"
POLICY_MODE_ENV = "KMFA_ABUSE_POLICY_MODE"
ENFORCED_MODE = "enforced"
EMERGENCY_MODE = "emergency-expensive-only"
TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
DEVICE_COOKIE_NAME = "__Host-kmfa_device"
DEVICE_COOKIE_MAX_AGE = 30 * 24 * 60 * 60
DEVICE_RE = re.compile(r"^kmfa-d1-[A-Za-z0-9_-]{22}$")
WORKSPACE_PATH_RE = re.compile(r"^/workspaces/([^/]+)(?:/|$)")
PROOF_HEADER = "x-kmfa-challenge-proof"
MAX_PROOF_HEADER_BYTES = 2048
CHALLENGE_DIFFICULTY_BITS = 11
CHALLENGE_TTL_SECONDS = 90
EVENT_RETENTION_SECONDS = 24 * 60 * 60
ALERT_WINDOW_SECONDS = 5 * 60
EVENT_BUCKETS = 16
ABUSE_SCHEMA_VERSION = 1

logger = logging.getLogger("kmfa.abuse")
ops_router = APIRouter(tags=["private-operations"])


@dataclass(frozen=True)
class LimitWindow:
    seconds: int
    per_ip: int
    per_device: int
    per_workspace: int | None
    global_limit: int


@dataclass(frozen=True)
class OperationPolicy:
    name: str
    windows: tuple[LimitWindow, ...]
    concurrency: int
    lease_seconds: int
    challenge: bool = True


# These are early-rollout budgets, not measured production demand.  They are
# intentionally explicit and versioned so Stage Review can tune them from real
# capacity evidence without changing endpoint behavior.
POLICIES: dict[str, OperationPolicy] = {
    "identity": OperationPolicy(
        name="identity",
        windows=(
            LimitWindow(10, 24, 6, None, 64),
            LimitWindow(3600, 120, 24, None, 600),
        ),
        concurrency=8,
        lease_seconds=30,
    ),
    "recovery": OperationPolicy(
        name="recovery",
        windows=(
            LimitWindow(10, 24, 6, None, 64),
            LimitWindow(3600, 240, 60, None, 600),
        ),
        concurrency=12,
        lease_seconds=30,
    ),
    "mutation": OperationPolicy(
        name="mutation",
        windows=(
            LimitWindow(10, 96, 24, 32, 128),
            LimitWindow(3600, 1800, 600, 1200, 2400),
        ),
        concurrency=24,
        lease_seconds=30,
    ),
    "upload": OperationPolicy(
        name="upload",
        windows=(
            LimitWindow(10, 24, 6, 6, 12),
            LimitWindow(3600, 128, 32, 32, 256),
        ),
        concurrency=2,
        lease_seconds=120,
    ),
    "export": OperationPolicy(
        name="export",
        windows=(
            LimitWindow(10, 48, 8, 6, 16),
            LimitWindow(3600, 600, 240, 240, 1200),
        ),
        concurrency=4,
        lease_seconds=120,
    ),
    "read": OperationPolicy(
        name="read",
        windows=(
            LimitWindow(10, 320, 80, 120, 512),
            LimitWindow(3600, 9000, 3000, 5000, 12_000),
        ),
        concurrency=64,
        lease_seconds=30,
        challenge=False,
    ),
    "unknown": OperationPolicy(
        name="unknown",
        windows=(
            LimitWindow(10, 48, 12, None, 64),
            LimitWindow(3600, 360, 120, None, 600),
        ),
        concurrency=16,
        lease_seconds=15,
    ),
}


@dataclass(frozen=True)
class RequestSignals:
    ip_tag: str
    device_tag: str
    actor_tag: str
    workspace_tag: str | None


@dataclass(frozen=True)
class ValidProof:
    proof_hash: str
    expires_at: int


@dataclass(frozen=True)
class Admission:
    allowed: bool
    operation: str
    decision: str
    reason: str
    status_code: int
    detail: str
    retry_after: int
    remaining: int
    reset_after: int
    lease_id: str | None = None
    challenge: dict[str, Any] | None = None
    alert_new: bool = False


def _now() -> float:
    return time.time()


def _walking_enabled() -> bool:
    return (
        os.environ.get("KMFA_WALKING_SKELETON_ENABLED", "0").strip().lower()
        in TRUE_VALUES
    )


def policy_mode() -> str:
    value = os.environ.get(POLICY_MODE_ENV, ENFORCED_MODE).strip().lower()
    if value in {ENFORCED_MODE, EMERGENCY_MODE}:
        return value
    return "invalid"


def _state_root() -> Path:
    explicit = os.environ.get("KMFA_WALKING_SKELETON_STATE_DIR", "").strip()
    if explicit:
        return Path(explicit)
    app_state = Path(os.environ.get("KMFA_APP_STATE_DIR", "/var/lib/kmfa/state"))
    return app_state / "walking-skeleton"


def _control_root() -> Path:
    return _state_root() / "abuse-control"


def _db_path() -> Path:
    return _control_root() / "abuse_control.sqlite3"


def _key_path() -> Path:
    return _control_root() / "challenge.key"


def _ensure_control_root() -> None:
    root = _control_root()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    root.chmod(0o700)


def _load_or_create_key() -> bytes:
    _ensure_control_root()
    path = _key_path()
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        pass
    else:
        try:
            payload = secrets.token_bytes(32)
            os.write(descriptor, payload)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    payload = path.read_bytes()
    if len(payload) != 32:
        raise RuntimeError("invalid abuse-control key")
    path.chmod(0o600)
    return payload


def _open_store() -> sqlite3.Connection:
    _ensure_control_root()
    connection = sqlite3.connect(
        str(_db_path()),
        isolation_level=None,
        timeout=5,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=FULL")
    connection.execute("PRAGMA busy_timeout=5000")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS rate_counters (
          policy_version TEXT NOT NULL,
          operation TEXT NOT NULL,
          window_seconds INTEGER NOT NULL,
          window_start INTEGER NOT NULL,
          scope_kind TEXT NOT NULL,
          scope_tag TEXT NOT NULL,
          count INTEGER NOT NULL CHECK(count >= 0),
          expires_at INTEGER NOT NULL,
          PRIMARY KEY(
            policy_version, operation, window_seconds, window_start,
            scope_kind, scope_tag
          )
        );
        CREATE INDEX IF NOT EXISTS rate_counters_expiry
          ON rate_counters(expires_at);

        CREATE TABLE IF NOT EXISTS concurrency_leases (
          lease_id TEXT PRIMARY KEY,
          policy_version TEXT NOT NULL,
          operation TEXT NOT NULL,
          context_tag TEXT NOT NULL,
          created_at INTEGER NOT NULL,
          expires_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS concurrency_leases_expiry
          ON concurrency_leases(expires_at);

        CREATE TABLE IF NOT EXISTS challenge_uses (
          proof_hash TEXT PRIMARY KEY,
          expires_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS challenge_uses_expiry
          ON challenge_uses(expires_at);

        CREATE TABLE IF NOT EXISTS decision_metrics (
          policy_version TEXT NOT NULL,
          operation TEXT NOT NULL,
          decision TEXT NOT NULL,
          reason TEXT NOT NULL,
          count INTEGER NOT NULL CHECK(count >= 0),
          last_at INTEGER NOT NULL,
          PRIMARY KEY(policy_version, operation, decision, reason)
        );

        CREATE TABLE IF NOT EXISTS decision_windows (
          policy_version TEXT NOT NULL,
          window_start INTEGER NOT NULL,
          operation TEXT NOT NULL,
          decision TEXT NOT NULL,
          reason TEXT NOT NULL,
          actor_bucket INTEGER NOT NULL,
          count INTEGER NOT NULL CHECK(count >= 0),
          first_at INTEGER NOT NULL,
          last_at INTEGER NOT NULL,
          PRIMARY KEY(
            policy_version, window_start, operation, decision, reason,
            actor_bucket
          )
        );
        CREATE INDEX IF NOT EXISTS decision_windows_time
          ON decision_windows(window_start);

        CREATE TABLE IF NOT EXISTS capacity_alerts (
          policy_version TEXT NOT NULL,
          window_start INTEGER NOT NULL,
          operation TEXT NOT NULL,
          reason TEXT NOT NULL,
          created_at INTEGER NOT NULL,
          PRIMARY KEY(policy_version, window_start, operation, reason)
        );
        CREATE INDEX IF NOT EXISTS capacity_alerts_time
          ON capacity_alerts(window_start);
        """
    )
    connection.execute(f"PRAGMA user_version={ABUSE_SCHEMA_VERSION}")
    _db_path().chmod(0o600)
    return connection


def _tag(key: bytes, kind: str, value: str) -> str:
    return hmac.new(
        key,
        f"{kind}\0{value}".encode("utf-8", errors="replace"),
        hashlib.sha256,
    ).hexdigest()


def _client_ip(scope: Scope, headers: Headers) -> str:
    # Production origin access is edge-only. Cloudflare overwrites this header;
    # direct-origin requests are separately fail-closed by the S03 boundary.
    forwarded = headers.get("cf-connecting-ip", "").strip()
    candidates = [forwarded]
    client = scope.get("client")
    if isinstance(client, tuple) and client:
        candidates.append(str(client[0]))
    for candidate in candidates:
        try:
            return ipaddress.ip_address(candidate).compressed
        except ValueError:
            continue
    return "unavailable"


def _device_cookie(headers: Headers) -> tuple[str, bool]:
    cookie_header = headers.get("cookie", "")[:8192]
    prefix = f"{DEVICE_COOKIE_NAME}="
    for item in cookie_header.split(";"):
        item = item.strip()
        if item.startswith(prefix):
            value = item.removeprefix(prefix).strip()
            if DEVICE_RE.fullmatch(value):
                return value, False
            break
    return f"kmfa-d1-{secrets.token_urlsafe(16)}", True


def _device_set_cookie(value: str) -> str:
    assert DEVICE_RE.fullmatch(value)
    return (
        f"{DEVICE_COOKIE_NAME}={value}; Path=/; Max-Age={DEVICE_COOKIE_MAX_AGE}; "
        "Secure; HttpOnly; SameSite=Strict"
    )


def _request_signals(
    key: bytes,
    scope: Scope,
    headers: Headers,
    device: str,
    workspace_value: str | None,
) -> RequestSignals:
    ip_tag = _tag(key, "ip", _client_ip(scope, headers))
    device_tag = _tag(key, "device", device)
    workspace_tag = (
        _tag(key, "workspace", workspace_value) if workspace_value else None
    )
    actor_tag = _tag(key, "actor", f"{ip_tag}:{device_tag}")
    return RequestSignals(
        ip_tag=ip_tag,
        device_tag=device_tag,
        actor_tag=actor_tag,
        workspace_tag=workspace_tag,
    )


def _classify(method: str, path: str) -> tuple[str | None, str | None]:
    if not (path == API_PREFIX or path.startswith(f"{API_PREFIX}/")):
        return None, None
    relative = path.removeprefix(API_PREFIX) or "/"
    workspace_match = WORKSPACE_PATH_RE.match(relative)
    workspace_value = workspace_match.group(1) if workspace_match else None
    method = method.upper()

    if method in {"HEAD", "OPTIONS"} or (method == "GET" and relative == "/status"):
        return None, workspace_value
    if method == "POST" and relative == "/workspaces":
        return "identity", None
    if method == "POST" and relative in {
        "/recoveries",
        "/sessions",
        "/recovery-files/import",
    }:
        return "recovery", None
    if method == "PUT" and relative.endswith("/artifact"):
        return "upload", workspace_value
    if method == "POST" and (
        relative.endswith("/artifact/download")
        or relative.endswith("/recovery-file")
    ):
        return "export", workspace_value
    if method == "GET" and workspace_value:
        return "read", workspace_value
    if method in {"POST", "PUT", "PATCH", "DELETE"} and (
        workspace_value or relative == "/sessions/current"
    ):
        return "mutation", workspace_value
    return "unknown", workspace_value


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    if not value or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("invalid base64url")
    return base64.urlsafe_b64decode(value + ("=" * (-len(value) % 4)))


def _challenge_context(signals: RequestSignals) -> str:
    return signals.workspace_tag or "none"


def _make_challenge(
    key: bytes,
    operation: str,
    signals: RequestSignals,
    now: int,
) -> dict[str, Any]:
    payload = {
        "a": signals.actor_tag,
        "c": _challenge_context(signals),
        "e": now + CHALLENGE_TTL_SECONDS,
        "n": _b64encode(secrets.token_bytes(12)),
        "o": operation,
        "p": POLICY_VERSION,
        "v": 1,
    }
    encoded = _b64encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    signature = _b64encode(
        hmac.new(key, encoded.encode("ascii"), hashlib.sha256).digest()
    )
    token = f"{encoded}.{signature}"
    return {
        "algorithm": "sha256-leading-zero-bits",
        "token": token,
        "difficulty_bits": CHALLENGE_DIFFICULTY_BITS,
        "expires_in_seconds": CHALLENGE_TTL_SECONDS,
        "proof_header": "X-KMFA-Challenge-Proof",
        "proof_format": "<token>:<decimal nonce>",
    }


def _leading_zero_bits(value: bytes) -> int:
    count = 0
    for byte in value:
        if byte == 0:
            count += 8
            continue
        count += 8 - byte.bit_length()
        break
    return count


def _validate_proof(
    key: bytes,
    proof: str,
    operation: str,
    signals: RequestSignals,
    now: int,
) -> ValidProof:
    if not proof or len(proof.encode("utf-8")) > MAX_PROOF_HEADER_BYTES:
        raise ValueError("invalid challenge proof")
    token, separator, counter_text = proof.rpartition(":")
    if not separator or not counter_text.isdecimal() or len(counter_text) > 12:
        raise ValueError("invalid challenge counter")
    counter = int(counter_text)
    if counter < 0 or counter > 2**32 - 1:
        raise ValueError("invalid challenge counter")
    encoded, separator, signature = token.partition(".")
    if not separator:
        raise ValueError("invalid challenge token")
    expected_signature = hmac.new(
        key,
        encoded.encode("ascii"),
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(expected_signature, _b64decode(signature)):
        raise ValueError("invalid challenge signature")
    payload = json.loads(_b64decode(encoded))
    if (
        type(payload) is not dict
        or set(payload) != {"a", "c", "e", "n", "o", "p", "v"}
        or payload["v"] != 1
        or payload["p"] != POLICY_VERSION
        or payload["o"] != operation
        or payload["a"] != signals.actor_tag
        or payload["c"] != _challenge_context(signals)
        or type(payload["e"]) is not int
        or payload["e"] < now
        or payload["e"] > now + CHALLENGE_TTL_SECONDS + 5
        or type(payload["n"]) is not str
    ):
        raise ValueError("challenge binding mismatch")
    digest = hashlib.sha256(f"{token}:{counter}".encode("ascii")).digest()
    if _leading_zero_bits(digest) < CHALLENGE_DIFFICULTY_BITS:
        raise ValueError("challenge work insufficient")
    return ValidProof(
        proof_hash=hashlib.sha256(proof.encode("ascii")).hexdigest(),
        expires_at=int(payload["e"]),
    )


def _scope_limits(
    window: LimitWindow,
    signals: RequestSignals,
) -> tuple[tuple[str, str, int], ...]:
    values: list[tuple[str, str, int]] = [
        ("global", "global", window.global_limit),
        ("ip", signals.ip_tag, window.per_ip),
        ("device", signals.device_tag, window.per_device),
    ]
    if signals.workspace_tag and window.per_workspace is not None:
        values.append(
            ("workspace", signals.workspace_tag, window.per_workspace)
        )
    return tuple(values)


def _counter_value(
    connection: sqlite3.Connection,
    operation: str,
    window: LimitWindow,
    window_start: int,
    scope_kind: str,
    scope_tag: str,
) -> int:
    row = connection.execute(
        """
        SELECT count FROM rate_counters
        WHERE policy_version = ? AND operation = ? AND window_seconds = ?
          AND window_start = ? AND scope_kind = ? AND scope_tag = ?
        """,
        (
            POLICY_VERSION,
            operation,
            window.seconds,
            window_start,
            scope_kind,
            scope_tag,
        ),
    ).fetchone()
    return int(row["count"]) if row is not None else 0


def _increment_counter(
    connection: sqlite3.Connection,
    operation: str,
    window: LimitWindow,
    window_start: int,
    scope_kind: str,
    scope_tag: str,
) -> None:
    connection.execute(
        """
        INSERT INTO rate_counters(
          policy_version, operation, window_seconds, window_start,
          scope_kind, scope_tag, count, expires_at
        ) VALUES (?, ?, ?, ?, ?, ?, 1, ?)
        ON CONFLICT(
          policy_version, operation, window_seconds, window_start,
          scope_kind, scope_tag
        ) DO UPDATE SET count = count + 1
        """,
        (
            POLICY_VERSION,
            operation,
            window.seconds,
            window_start,
            scope_kind,
            scope_tag,
            window_start + (window.seconds * 2),
        ),
    )


def _record_decision(
    connection: sqlite3.Connection,
    *,
    now: int,
    operation: str,
    decision: str,
    reason: str,
    actor_tag: str,
) -> bool:
    connection.execute(
        """
        INSERT INTO decision_metrics(
          policy_version, operation, decision, reason, count, last_at
        ) VALUES (?, ?, ?, ?, 1, ?)
        ON CONFLICT(policy_version, operation, decision, reason)
        DO UPDATE SET count = count + 1, last_at = excluded.last_at
        """,
        (POLICY_VERSION, operation, decision, reason, now),
    )
    bucket = int(actor_tag[:8], 16) % EVENT_BUCKETS
    event_window = (now // ALERT_WINDOW_SECONDS) * ALERT_WINDOW_SECONDS
    connection.execute(
        """
        INSERT INTO decision_windows(
          policy_version, window_start, operation, decision, reason,
          actor_bucket, count, first_at, last_at
        ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
        ON CONFLICT(
          policy_version, window_start, operation, decision, reason,
          actor_bucket
        ) DO UPDATE SET count = count + 1, last_at = excluded.last_at
        """,
        (
            POLICY_VERSION,
            event_window,
            operation,
            decision,
            reason,
            bucket,
            now,
            now,
        ),
    )
    if decision != "capacity-blocked":
        return False
    cursor = connection.execute(
        """
        INSERT OR IGNORE INTO capacity_alerts(
          policy_version, window_start, operation, reason, created_at
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (POLICY_VERSION, event_window, operation, reason, now),
    )
    return cursor.rowcount == 1


def _cleanup(connection: sqlite3.Connection, now: int) -> None:
    connection.execute("DELETE FROM rate_counters WHERE expires_at <= ?", (now,))
    connection.execute(
        "DELETE FROM concurrency_leases WHERE expires_at <= ?",
        (now,),
    )
    connection.execute("DELETE FROM challenge_uses WHERE expires_at <= ?", (now,))
    cutoff = now - EVENT_RETENTION_SECONDS
    connection.execute(
        "DELETE FROM decision_windows WHERE window_start < ?",
        (cutoff,),
    )
    connection.execute(
        "DELETE FROM capacity_alerts WHERE window_start < ?",
        (cutoff,),
    )


def _denied(
    *,
    operation: str,
    decision: str,
    reason: str,
    status_code: int,
    detail: str,
    retry_after: int,
    reset_after: int,
    challenge: dict[str, Any] | None = None,
    alert_new: bool = False,
) -> Admission:
    return Admission(
        allowed=False,
        operation=operation,
        decision=decision,
        reason=reason,
        status_code=status_code,
        detail=detail,
        retry_after=max(1, retry_after),
        remaining=0,
        reset_after=max(1, reset_after),
        challenge=challenge,
        alert_new=alert_new,
    )


def admit_request(
    *,
    operation: str,
    signals: RequestSignals,
    proof_header: str | None,
    now_value: float | None = None,
) -> Admission:
    """Atomically admit one guarded operation and reserve its concurrency slot."""

    policy = POLICIES[operation]
    now = int(_now() if now_value is None else now_value)
    key = _load_or_create_key()
    valid_proof: ValidProof | None = None
    if proof_header:
        try:
            valid_proof = _validate_proof(
                key,
                proof_header,
                operation,
                signals,
                now,
            )
        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            with _open_store() as connection:
                connection.execute("BEGIN IMMEDIATE")
                try:
                    _cleanup(connection, now)
                    _record_decision(
                        connection,
                        now=now,
                        operation=operation,
                        decision="challenge-blocked",
                        reason="invalid-proof",
                        actor_tag=signals.actor_tag,
                    )
                    connection.execute("COMMIT")
                except Exception:
                    connection.execute("ROLLBACK")
                    raise
            return _denied(
                operation=operation,
                decision="challenge-blocked",
                reason="invalid-proof",
                status_code=403,
                detail="risk_challenge_invalid",
                retry_after=1,
                reset_after=1,
            )

    with _open_store() as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            _cleanup(connection, now)
            if valid_proof is not None:
                used = connection.execute(
                    "SELECT 1 FROM challenge_uses WHERE proof_hash = ?",
                    (valid_proof.proof_hash,),
                ).fetchone()
                if used is not None:
                    _record_decision(
                        connection,
                        now=now,
                        operation=operation,
                        decision="challenge-blocked",
                        reason="replayed-proof",
                        actor_tag=signals.actor_tag,
                    )
                    connection.execute("COMMIT")
                    return _denied(
                        operation=operation,
                        decision="challenge-blocked",
                        reason="replayed-proof",
                        status_code=403,
                        detail="risk_challenge_replayed",
                        retry_after=1,
                        reset_after=1,
                    )

            exceeded_actor = False
            retry_after = 1
            remaining_values: list[int] = []
            reset_values: list[int] = []
            for window in policy.windows:
                window_start = (now // window.seconds) * window.seconds
                reset_after = window_start + window.seconds - now
                reset_values.append(max(1, reset_after))
                for scope_kind, scope_tag, limit in _scope_limits(window, signals):
                    current = _counter_value(
                        connection,
                        operation,
                        window,
                        window_start,
                        scope_kind,
                        scope_tag,
                    )
                    remaining_values.append(max(0, limit - current - 1))
                    if current < limit:
                        continue
                    retry_after = max(retry_after, reset_after)
                    if scope_kind == "global":
                        alert_new = _record_decision(
                            connection,
                            now=now,
                            operation=operation,
                            decision="capacity-blocked",
                            reason=f"global-{window.seconds}s",
                            actor_tag=signals.actor_tag,
                        )
                        connection.execute("COMMIT")
                        return _denied(
                            operation=operation,
                            decision="capacity-blocked",
                            reason=f"global-{window.seconds}s",
                            status_code=429,
                            detail="risk_capacity_limited",
                            retry_after=retry_after,
                            reset_after=retry_after,
                            alert_new=alert_new,
                        )
                    exceeded_actor = True

            if exceeded_actor and valid_proof is None:
                decision = (
                    "challenge-required" if policy.challenge else "actor-blocked"
                )
                reason = "actor-budget"
                _record_decision(
                    connection,
                    now=now,
                    operation=operation,
                    decision=decision,
                    reason=reason,
                    actor_tag=signals.actor_tag,
                )
                connection.execute("COMMIT")
                challenge = (
                    _make_challenge(key, operation, signals, now)
                    if policy.challenge
                    else None
                )
                return _denied(
                    operation=operation,
                    decision=decision,
                    reason=reason,
                    status_code=429,
                    detail=(
                        "risk_challenge_required"
                        if challenge
                        else "risk_capacity_limited"
                    ),
                    retry_after=retry_after,
                    reset_after=retry_after,
                    challenge=challenge,
                )

            active = int(
                connection.execute(
                    """
                    SELECT COUNT(*) FROM concurrency_leases
                    WHERE policy_version = ? AND operation = ? AND expires_at > ?
                    """,
                    (POLICY_VERSION, operation, now),
                ).fetchone()[0]
            )
            if active >= policy.concurrency:
                alert_new = _record_decision(
                    connection,
                    now=now,
                    operation=operation,
                    decision="capacity-blocked",
                    reason="concurrency",
                    actor_tag=signals.actor_tag,
                )
                connection.execute("COMMIT")
                return _denied(
                    operation=operation,
                    decision="capacity-blocked",
                    reason="concurrency",
                    status_code=429,
                    detail="risk_capacity_limited",
                    retry_after=min(5, policy.lease_seconds),
                    reset_after=min(5, policy.lease_seconds),
                    alert_new=alert_new,
                )

            if valid_proof is not None:
                connection.execute(
                    """
                    INSERT INTO challenge_uses(proof_hash, expires_at)
                    VALUES (?, ?)
                    """,
                    (valid_proof.proof_hash, valid_proof.expires_at),
                )
            for window in policy.windows:
                window_start = (now // window.seconds) * window.seconds
                for scope_kind, scope_tag, _ in _scope_limits(window, signals):
                    _increment_counter(
                        connection,
                        operation,
                        window,
                        window_start,
                        scope_kind,
                        scope_tag,
                    )
            lease_id = f"lease_{secrets.token_urlsafe(18)}"
            connection.execute(
                """
                INSERT INTO concurrency_leases(
                  lease_id, policy_version, operation, context_tag,
                  created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    lease_id,
                    POLICY_VERSION,
                    operation,
                    signals.workspace_tag or signals.actor_tag,
                    now,
                    now + policy.lease_seconds,
                ),
            )
            decision = "challenge-passed" if valid_proof else "allowed"
            reason = "valid-proof" if valid_proof else "within-budget"
            _record_decision(
                connection,
                now=now,
                operation=operation,
                decision=decision,
                reason=reason,
                actor_tag=signals.actor_tag,
            )
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
    return Admission(
        allowed=True,
        operation=operation,
        decision=decision,
        reason=reason,
        status_code=200,
        detail="",
        retry_after=0,
        remaining=min(remaining_values) if remaining_values else 0,
        reset_after=max(reset_values) if reset_values else 1,
        lease_id=lease_id,
    )


def release_lease(lease_id: str | None) -> None:
    if not lease_id:
        return
    with _open_store() as connection:
        connection.execute(
            "DELETE FROM concurrency_leases WHERE lease_id = ?",
            (lease_id,),
        )


def public_policy_contract() -> dict[str, Any]:
    return {
        "policy_version": POLICY_VERSION,
        "mode": policy_mode(),
        "anonymous": True,
        "login_required": False,
        "signals": ["edge_ip_hash", "device_hash", "workspace_hash", "global"],
        "challenge": {
            "algorithm": "sha256-leading-zero-bits",
            "difficulty_bits": CHALLENGE_DIFFICULTY_BITS,
            "one_use": True,
            "actor_and_operation_bound": True,
            "global_budget_bypass": False,
        },
        "public_browse_exempt": True,
        "operations": {
            name: {
                "windows": [
                    {
                        "seconds": window.seconds,
                        "per_ip": window.per_ip,
                        "per_device": window.per_device,
                        "per_workspace": window.per_workspace,
                        "global": window.global_limit,
                    }
                    for window in policy.windows
                ],
                "concurrency": policy.concurrency,
                "challenge": policy.challenge,
            }
            for name, policy in POLICIES.items()
        },
        "rejection_audit": "bounded-hashed-aggregate",
        "alerting": "one-structured-capacity-alert-per-operation-window",
    }


def operations_snapshot() -> dict[str, Any]:
    key_path = _key_path()
    if not _db_path().exists():
        return {
            "policy": public_policy_contract(),
            "healthy": True,
            "initialized": False,
            "metrics": [],
            "state_counts": {},
        }
    with _open_store() as connection:
        now = int(_now())
        connection.execute("BEGIN IMMEDIATE")
        try:
            _cleanup(connection, now)
            counts = {
                table: int(
                    connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                )
                for table in (
                    "rate_counters",
                    "concurrency_leases",
                    "challenge_uses",
                    "decision_metrics",
                    "decision_windows",
                    "capacity_alerts",
                )
            }
            metrics = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT operation, decision, reason, count, last_at
                    FROM decision_metrics
                    ORDER BY operation, decision, reason
                    """
                )
            ]
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
    return {
        "policy": public_policy_contract(),
        "healthy": True,
        "initialized": True,
        "schema_version": ABUSE_SCHEMA_VERSION,
        "key_present": key_path.is_file(),
        "raw_identifiers_stored": False,
        "state_counts": counts,
        "metrics": metrics,
    }


@ops_router.get("/ops/abuse-control/status")
def abuse_control_operations_status() -> dict[str, Any]:
    try:
        return operations_snapshot()
    except (OSError, sqlite3.Error, RuntimeError) as error:
        raise HTTPException(
            status_code=503,
            detail="abuse_control_unavailable",
        ) from error


def _response_headers(admission: Admission) -> dict[str, str]:
    headers = {
        "Cache-Control": "private, no-store",
        "Pragma": "no-cache",
        "Retry-After": str(admission.retry_after),
        "RateLimit-Remaining": str(admission.remaining),
        "RateLimit-Reset": str(admission.reset_after),
        "X-KMFA-Abuse-Policy": POLICY_VERSION,
        "X-KMFA-Abuse-Operation": admission.operation,
        "X-KMFA-Abuse-Decision": admission.decision,
        "X-KMFA-Abuse-Reason": admission.reason,
        "X-Robots-Tag": "noindex, nofollow, noarchive",
    }
    return headers


class AntiAbuseMiddleware:
    """Apply persistent budgets before request bodies reach expensive handlers."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        path = str(scope.get("path") or "")
        method = str(scope.get("method") or "GET").upper()
        operation, workspace_value = _classify(method, path)
        if not (path == API_PREFIX or path.startswith(f"{API_PREFIX}/")):
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        device, device_is_new = _device_cookie(headers)

        async def send_with_device(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                response_headers.setdefault("X-KMFA-Abuse-Policy", POLICY_VERSION)
                if device_is_new:
                    response_headers.append(
                        "Set-Cookie",
                        _device_set_cookie(device),
                    )
            await send(message)

        if not _walking_enabled():
            await self.app(scope, receive, send_with_device)
            return

        mode = policy_mode()
        if mode == "invalid":
            if operation is None:
                await self.app(scope, receive, send_with_device)
                return
            response = JSONResponse(
                {"detail": "abuse_policy_configuration_invalid"},
                status_code=503,
                headers={
                    "Cache-Control": "private, no-store",
                    "Retry-After": "30",
                    "X-KMFA-Abuse-Policy": POLICY_VERSION,
                    "X-KMFA-Abuse-Decision": "fail-closed",
                },
            )
            await response(scope, receive, send_with_device)
            return

        if operation is None or (
            mode == EMERGENCY_MODE and operation in {"read", "mutation"}
        ):
            async def send_exempt(message: Message) -> None:
                if message["type"] == "http.response.start":
                    response_headers = MutableHeaders(scope=message)
                    response_headers.setdefault(
                        "X-KMFA-Abuse-Policy",
                        POLICY_VERSION,
                    )
                    response_headers.setdefault(
                        "X-KMFA-Abuse-Decision",
                        "public-browse-exempt"
                        if operation is None
                        else "emergency-low-cost-exempt",
                    )
                await send_with_device(message)

            await self.app(scope, receive, send_exempt)
            return

        try:
            key = _load_or_create_key()
            signals = _request_signals(
                key,
                scope,
                headers,
                device,
                workspace_value,
            )
            admission = admit_request(
                operation=operation,
                signals=signals,
                proof_header=headers.get(PROOF_HEADER),
            )
        except (OSError, sqlite3.Error, RuntimeError):
            # Preserve the existing storage error contract when the configured
            # business-state root itself cannot be a directory. The request
            # cannot consume business resources in that state, so delegating is
            # safe; all other control-plane failures remain fail-closed.
            state_root = _state_root()
            if state_root.exists() and not state_root.is_dir():
                await self.app(scope, receive, send_with_device)
                return
            response = JSONResponse(
                {"detail": "abuse_control_unavailable"},
                status_code=503,
                headers={
                    "Cache-Control": "private, no-store",
                    "Retry-After": "5",
                    "X-KMFA-Abuse-Policy": POLICY_VERSION,
                    "X-KMFA-Abuse-Decision": "fail-closed",
                },
            )
            await response(scope, receive, send_with_device)
            return

        if not admission.allowed:
            if admission.alert_new:
                logger.warning(
                    "KMFA_ABUSE_CAPACITY_ALERT operation=%s reason=%s policy=%s",
                    admission.operation,
                    admission.reason,
                    POLICY_VERSION,
                )
            body: dict[str, Any] = {"detail": admission.detail}
            if admission.challenge is not None:
                body["challenge"] = admission.challenge
            response = JSONResponse(
                body,
                status_code=admission.status_code,
                headers=_response_headers(admission),
            )
            await response(scope, receive, send_with_device)
            return

        released = False

        def release_once() -> None:
            nonlocal released
            if released:
                return
            released = True
            try:
                release_lease(admission.lease_id)
            except (OSError, sqlite3.Error, RuntimeError):
                # The lease has a strict TTL and will be recovered by cleanup.
                logger.warning(
                    "KMFA_ABUSE_LEASE_RELEASE_DEFERRED operation=%s policy=%s",
                    admission.operation,
                    POLICY_VERSION,
                )

        async def send_with_budget(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                for name, value in _response_headers(admission).items():
                    if name not in response_headers:
                        response_headers[name] = value
                # Successful application responses do not tell clients to wait.
                if "Retry-After" in response_headers:
                    del response_headers["Retry-After"]
            try:
                await send_with_device(message)
            finally:
                if (
                    message["type"] == "http.response.body"
                    and not message.get("more_body", False)
                ) or message["type"] == "http.response.pathsend":
                    release_once()

        try:
            await self.app(scope, receive, send_with_budget)
        finally:
            release_once()
