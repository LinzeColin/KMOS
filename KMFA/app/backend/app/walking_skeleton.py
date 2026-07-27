"""S03/P3.4 walking skeleton with S04/P4.1-P4.4 security hardening.

This is intentionally a narrow, replaceable adapter. Structured workspace
state uses the S05 versioned database adapter (legacy SQLite by default or an
explicit shared PostgreSQL service). S05/P5.2 adds an opt-in private
S3-compatible byte store with immutable application-version keys, while
retaining the v1.5 filesystem adapter as the default and permanent legacy read
path. S05/P5.3 adds a hashed idempotency key, durable upload intent, fixed
state transitions, transactional outbox, consumer dedupe receipts and
converge-or-isolate reconciliation without raw-object deletion. P4.1 adds
128-bit workspace identifiers, 256-bit workspace secrets,
irreversible verifiers and one-hour session exchange while accepting existing
S03 identifiers. P4.2 adds a strict, minimal `.kmfa-recovery` capability file
plus atomic secret rotation. P4.3 binds newly issued browser sessions to a
Secure/HttpOnly/SameSite cookie, supports server-side revocation and keeps
legacy Authorization bearer sessions read-compatible. P4.4 adds explicit
lifetime resource ceilings alongside the persistent request/concurrency gate.
S05/P5.4 still owns backup/restore and deletion lifecycle semantics; S06
owns scanning and scalable multi-file upload semantics.

Raw recovery codes and access capabilities are returned only to their caller;
the store keeps SHA-256 hashes. Artifacts are never mapped into the static
file tree and are always downloaded as attachments after capability checks.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote

from fastapi import APIRouter, Body, Cookie, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from .anti_abuse import public_policy_contract
from .consistency_state import (
    IDEMPOTENCY_KEY_RE,
    ConsistencyConflictError,
    ConsistencyRepository,
    ConsistencyStateError,
    UploadIntent,
    idempotency_key_hash,
    upload_request_fingerprint,
)
from . import resumable_upload as RU
from .object_storage import (
    LEGACY_STORAGE_BACKEND,
    S3_STORAGE_BACKEND,
    ObjectStorageConfigurationError,
    ObjectStorageConflictError,
    ObjectStorageIntegrityError,
    ObjectStorageMissingError,
    ObjectStorageUnavailableError,
    configured_write_store,
    content_md5_base64,
    object_store_for_backend,
    s3_dual_read_configured,
)
from .retention_lifecycle import (
    DELETE_CONFIRMATION,
    DELETION_WORKER_LEASE,
    LIFECYCLE_ACTIVE_MODE,
    PUBLIC_PURGE_SLA,
    RESTORE_PROOF_MAX_AGE,
    LifecycleConflictError,
    LifecycleLegalHoldError,
    LifecyclePausedError,
    LifecycleRepository,
    RestoreProofRequiredError,
    deletion_request_fingerprint,
    lifecycle_mode,
    new_deletion_request_id,
)
from .structured_repository import (
    StructuredRepository,
    artifact_version_id,
)
from .structured_store import (
    StructuredStoreConnection,
    StructuredStoreError,
    StructuredStoreIntegrityError,
    open_structured_store,
)

API_PREFIX = "/public-api/walking-skeleton/v1"
SESSION_COOKIE_NAME = "__Secure-kmfa_session"
SESSION_COOKIE_PATH = API_PREFIX
SESSION_COOKIE_SAMESITE = "strict"
TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
CONSISTENCY_STATE_MODE_ENV = "KMFA_CONSISTENCY_STATE_MODE"
CONSISTENCY_ACTIVE_MODE = "recoverable-v1"
CONSISTENCY_PAUSED_MODE = "paused"
CONSISTENCY_STATE_MODES = frozenset(
    {CONSISTENCY_ACTIVE_MODE, CONSISTENCY_PAUSED_MODE}
)
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024
MAX_ARTIFACTS = 1
MAX_TOTAL_ARTIFACT_BYTES = 512 * 1024 * 1024
MIN_FREE_STATE_BYTES = 128 * 1024 * 1024
MAX_WORKSPACES_TOTAL = 10_000
MAX_ACTIVE_SESSIONS_PER_WORKSPACE = 8
MAX_AUDIT_EVENTS_PER_WORKSPACE = 10_000
MAX_AUDIT_EVENTS_TOTAL = 250_000
ACCESS_TOKEN_TTL = timedelta(hours=1)
WORKSPACE_ID_BYTES = 16
WORKSPACE_SECRET_BYTES = 32
ACCESS_TOKEN_BYTES = 32
RECOVERY_FILE_FORMAT = "kmfa-recovery"
RECOVERY_FILE_VERSION = 1
RECOVERY_FILE_MEDIA_TYPE = "application/vnd.kmfa.recovery+json"
MAX_RECOVERY_FILE_BYTES = 4096
RECOVERY_FILE_KEYS = frozenset(
    {"format", "version", "workspace_id", "workspace_secret"}
)

# Existing S03 workspaces used 12 random bytes (16 URL-safe characters). New
# P4.1 identities use 16 bytes (22 characters), while the verifier continues
# accepting the legacy shape so rollout never strands recovery assets.
WORKSPACE_ID_RE = re.compile(r"^ws_(?:[A-Za-z0-9_-]{16}|[A-Za-z0-9_-]{22})$")
RECOVERY_CODE_RE = re.compile(r"^kmfa-r1-[A-Za-z0-9_-]{43}$")
ACCESS_TOKEN_RE = re.compile(r"^kmfa-a1-[A-Za-z0-9_-]{43}$")
DUMMY_WORKSPACE_ID = "ws_" + ("0" * 22)
DUMMY_WORKSPACE_SECRET = "kmfa-r1-" + ("0" * 43)
DUMMY_WORKSPACE_VERIFIER = hashlib.sha256(
    DUMMY_WORKSPACE_SECRET.encode("ascii")
).hexdigest()
SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")

router = APIRouter(prefix=API_PREFIX, tags=["public-walking-skeleton"])


class CreateWorkspaceRequest(BaseModel):
    project_name: str = Field(min_length=1, max_length=120)


class RecoverWorkspaceRequest(BaseModel):
    recovery_code: str = Field(min_length=51, max_length=51)


class ExchangeWorkspaceSessionRequest(BaseModel):
    workspace_id: str = Field(min_length=1, max_length=64)
    workspace_secret: str = Field(min_length=1, max_length=128)


class ExportRecoveryFileRequest(BaseModel):
    workspace_secret: str = Field(min_length=1, max_length=128)


class UpdateWorkspaceRequest(BaseModel):
    project_name: str | None = Field(default=None, min_length=1, max_length=120)
    progress: int | None = Field(default=None, ge=0, le=100)


class DeleteWorkspaceRequest(BaseModel):
    confirmation: str = Field(min_length=1, max_length=64)
    workspace_secret: str = Field(min_length=1, max_length=128)


class SkeletonError(RuntimeError):
    def __init__(self, status_code: int, code: str) -> None:
        super().__init__(code)
        self.status_code = status_code
        self.code = code


def walking_skeleton_enabled() -> bool:
    """Only explicit true values enable this pre-GA capability."""

    return (
        os.environ.get("KMFA_WALKING_SKELETON_ENABLED", "0").strip().lower()
        in TRUE_VALUES
    )


def consistency_state_mode() -> str:
    mode = os.environ.get(
        CONSISTENCY_STATE_MODE_ENV,
        CONSISTENCY_ACTIVE_MODE,
    ).strip()
    if mode not in CONSISTENCY_STATE_MODES:
        raise SkeletonError(503, "consistency_mode_invalid")
    return mode


def _state_root() -> Path:
    explicit = os.environ.get("KMFA_WALKING_SKELETON_STATE_DIR", "").strip()
    if explicit:
        return Path(explicit)
    app_state = Path(os.environ.get("KMFA_APP_STATE_DIR", "/var/lib/kmfa/state"))
    return app_state / "walking-skeleton"


def _db_path() -> Path:
    return _state_root() / "walking_skeleton.sqlite3"


def _objects_dir() -> Path:
    return _state_root() / "objects"


def _tmp_dir() -> Path:
    return _state_root() / "tmp"


def _ensure_private_directories() -> None:
    for path in (_state_root(), _objects_dir(), _tmp_dir()):
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.chmod(0o700)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime | None = None) -> str:
    return (value or _utc_now()).isoformat(timespec="seconds").replace("+00:00", "Z")


def _hash_capability(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _open_store() -> StructuredStoreConnection:
    _ensure_private_directories()
    return open_structured_store(_db_path())


@contextmanager
def _store():
    connection = None
    try:
        connection = _open_store()
        yield connection
    except SkeletonError:
        raise
    except (OSError, StructuredStoreError) as exc:
        raise SkeletonError(503, "walking_skeleton_storage_unavailable") from exc
    finally:
        if connection is not None:
            connection.close()


def _artifact_capacity_usage(connection: StructuredStoreConnection) -> int:
    """Count projected bytes plus every unprojected upload reservation.

    Upload effects happen before their database projection is committed. Counting
    only ``artifacts`` lets concurrent or chunked requests write objects and then
    fail the final capacity check, leaving attacker-amplifiable isolated bytes.
    The durable intent is therefore the reservation until a matching artifact
    version exists; isolated operations remain conservatively accounted for
    until explicit reconciliation/deletion.
    """

    row = connection.execute(
        """
        SELECT
          COALESCE((SELECT SUM(size_bytes) FROM artifacts), 0)
          +
          COALESCE((
            SELECT SUM(co.size_bytes)
            FROM consistency_operations co
            WHERE co.operation_kind = 'upload'
              AND co.size_bytes IS NOT NULL
              AND NOT EXISTS (
                SELECT 1
                FROM artifact_versions av
                WHERE av.artifact_version_id = co.artifact_version_id
              )
          ), 0) AS total_bytes
        """
    ).fetchone()
    return int(row["total_bytes"])


def _require_enabled() -> None:
    if not walking_skeleton_enabled():
        raise SkeletonError(404, "walking_skeleton_disabled")


def _raise_http(error: SkeletonError) -> None:
    raise HTTPException(status_code=error.status_code, detail=error.code) from error


def _clean_project_name(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value).strip()
    if not normalized or len(normalized) > 120:
        raise SkeletonError(422, "invalid_project_name")
    if any(unicodedata.category(char).startswith("C") for char in normalized):
        raise SkeletonError(422, "invalid_project_name")
    return normalized


def _clean_filename(encoded_value: str | None) -> str:
    if not encoded_value or len(encoded_value) > 2048:
        raise SkeletonError(422, "invalid_filename")
    try:
        decoded = unquote(encoded_value, encoding="utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise SkeletonError(422, "invalid_filename") from exc
    normalized = unicodedata.normalize("NFC", decoded).strip()
    if (
        not normalized
        or normalized in {".", ".."}
        or "/" in normalized
        or "\\" in normalized
        or len(normalized.encode("utf-8")) > 255
        or any(unicodedata.category(char).startswith("C") for char in normalized)
    ):
        raise SkeletonError(422, "invalid_filename")
    return normalized


def _clean_media_type(value: str | None) -> str:
    media_type = (value or "application/octet-stream").strip().lower()
    if (
        not media_type
        or len(media_type) > 200
        or any(ord(char) < 32 for char in media_type)
    ):
        return "application/octet-stream"
    return media_type


def _new_workspace_id() -> str:
    return f"ws_{secrets.token_urlsafe(WORKSPACE_ID_BYTES)}"


def _new_recovery_code() -> str:
    return f"kmfa-r1-{secrets.token_urlsafe(WORKSPACE_SECRET_BYTES)}"


def _new_access_token() -> str:
    return f"kmfa-a1-{secrets.token_urlsafe(ACCESS_TOKEN_BYTES)}"


def _new_artifact_id() -> str:
    return f"artifact_{secrets.token_urlsafe(12)}"


def _new_operation_id() -> str:
    return f"operation_{secrets.token_urlsafe(18)}"


def _resolved_idempotency_key(value: str | None) -> str:
    if value is None:
        return f"auto_{secrets.token_urlsafe(24)}"
    normalized = value.strip()
    if IDEMPOTENCY_KEY_RE.fullmatch(normalized) is None:
        raise SkeletonError(422, "invalid_idempotency_key")
    return normalized


def _recovery_file_bytes(workspace_id: str, workspace_secret: str) -> bytes:
    return (
        json.dumps(
            {
                "format": RECOVERY_FILE_FORMAT,
                "version": RECOVERY_FILE_VERSION,
                "workspace_id": workspace_id,
                "workspace_secret": workspace_secret,
            },
            ensure_ascii=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _parse_recovery_file(payload: bytes) -> tuple[str, str]:
    if not payload or len(payload) > MAX_RECOVERY_FILE_BYTES:
        raise SkeletonError(404, "recovery_not_found")

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate recovery file key")
            result[key] = value
        return result

    def reject_non_finite(_: str) -> None:
        raise ValueError("non-finite recovery file value")

    try:
        decoded = payload.decode("utf-8")
        parsed = json.loads(
            decoded,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_non_finite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        raise SkeletonError(404, "recovery_not_found") from exc
    if (
        type(parsed) is not dict
        or frozenset(parsed) != RECOVERY_FILE_KEYS
        or type(parsed["format"]) is not str
        or parsed["format"] != RECOVERY_FILE_FORMAT
        or type(parsed["version"]) is not int
        or parsed["version"] != RECOVERY_FILE_VERSION
        or type(parsed["workspace_id"]) is not str
        or not WORKSPACE_ID_RE.fullmatch(parsed["workspace_id"])
        or type(parsed["workspace_secret"]) is not str
        or not RECOVERY_CODE_RE.fullmatch(parsed["workspace_secret"])
    ):
        raise SkeletonError(404, "recovery_not_found")
    return parsed["workspace_id"], parsed["workspace_secret"]


def _append_audit(
    connection: StructuredStoreConnection,
    workspace_id: str,
    action: str,
    *,
    result_status: str = "ok",
    artifact_sha256: str | None = None,
) -> None:
    total = int(
        connection.execute(
            "SELECT COUNT(*) AS count_value FROM audit_events"
        ).fetchone()["count_value"]
    )
    workspace_total = int(
        connection.execute(
            """
            SELECT COUNT(*) AS count_value
            FROM audit_events
            WHERE workspace_id = ?
            """,
            (workspace_id,),
        ).fetchone()["count_value"]
    )
    if (
        total >= MAX_AUDIT_EVENTS_TOTAL
        or workspace_total >= MAX_AUDIT_EVENTS_PER_WORKSPACE
    ):
        raise SkeletonError(429, "workspace_audit_capacity_reached")
    connection.execute(
        """
        INSERT INTO audit_events(
          event_id, workspace_id, action, result_status, artifact_sha256, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            f"walk_{secrets.token_urlsafe(18)}",
            workspace_id,
            action,
            result_status,
            artifact_sha256,
            _timestamp(),
        ),
    )


def _issue_access_token(
    connection: StructuredStoreConnection,
    workspace_id: str,
) -> tuple[str, str]:
    now = _timestamp()
    connection.execute(
        "DELETE FROM access_tokens WHERE expires_at <= ?",
        (now,),
    )
    active_rows = connection.execute(
        """
        SELECT token_hash FROM access_tokens
        WHERE workspace_id = ?
        ORDER BY issuance_order
        """,
        (workspace_id,),
    ).fetchall()
    eviction_count = max(
        0,
        len(active_rows) - MAX_ACTIVE_SESSIONS_PER_WORKSPACE + 1,
    )
    if eviction_count:
        connection.executemany(
            "DELETE FROM access_tokens WHERE token_hash = ?",
            ((str(row["token_hash"]),) for row in active_rows[:eviction_count]),
        )
        _append_audit(
            connection,
            workspace_id,
            "workspace_session_budget_eviction",
            result_status="bounded",
        )
    token = _new_access_token()
    created = _utc_now()
    expires = created + ACCESS_TOKEN_TTL
    issuance_order = int(
        connection.execute(
            """
            SELECT COALESCE(MAX(issuance_order), 0) + 1 AS next_issuance_order
            FROM access_tokens
            """
        ).fetchone()["next_issuance_order"]
    )
    connection.execute(
        """
        INSERT INTO access_tokens(
          token_hash, workspace_id, created_at, expires_at, issuance_order
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            _hash_capability(token),
            workspace_id,
            _timestamp(created),
            _timestamp(expires),
            issuance_order,
        ),
    )
    return token, _timestamp(expires)


def _artifact_payload(row: Any | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "artifact_id": row["artifact_id"],
        "name": row["original_name"],
        "size_bytes": row["size_bytes"],
        "sha256": row["sha256"],
        "created_at": row["created_at"],
        "download_mode": "attachment-only",
    }


def _workspace_payload(
    connection: StructuredStoreConnection,
    workspace_id: str,
) -> dict[str, Any]:
    repository = StructuredRepository(connection)
    retention = connection.execute(
        "SELECT state FROM workspace_retention WHERE workspace_id = ?",
        (workspace_id,),
    ).fetchone()
    if retention is None or str(retention["state"]) != "active":
        raise SkeletonError(404, "workspace_not_found")
    workspace = repository.workspace_projection(workspace_id)
    if workspace is None:
        raise SkeletonError(404, "workspace_not_found")
    legacy_timestamps = connection.execute(
        """
        SELECT created_at, updated_at
        FROM workspaces
        WHERE workspace_id = ?
        """,
        (workspace_id,),
    ).fetchone()
    if legacy_timestamps is None:
        raise SkeletonError(404, "workspace_not_found")
    artifact = repository.latest_artifact_version(workspace_id)
    return {
        "workspace_id": workspace["workspace_id"],
        "project_name": workspace["project_name"],
        "progress": workspace["progress"],
        "created_at": legacy_timestamps["created_at"],
        "updated_at": legacy_timestamps["updated_at"],
        "artifact": _artifact_payload(artifact),
        "stage_status": "early-skeleton-not-ga",
    }


def _presented_access_token(
    authorization: str | None,
    session_cookie: str | None,
    *,
    allow_missing: bool = False,
) -> str | None:
    header_token: str | None = None
    if authorization is not None:
        if not authorization.startswith("Bearer "):
            raise SkeletonError(404, "workspace_not_found")
        header_token = authorization.removeprefix("Bearer ").strip()
        if not ACCESS_TOKEN_RE.fullmatch(header_token):
            raise SkeletonError(404, "workspace_not_found")

    cookie_token = session_cookie.strip() if session_cookie else None
    if cookie_token is not None and not ACCESS_TOKEN_RE.fullmatch(cookie_token):
        raise SkeletonError(404, "workspace_not_found")
    if (
        header_token is not None
        and cookie_token is not None
        and not hmac.compare_digest(header_token, cookie_token)
    ):
        raise SkeletonError(404, "workspace_not_found")
    token = header_token or cookie_token
    if token is None and not allow_missing:
        raise SkeletonError(404, "workspace_not_found")
    return token


def _authorize(
    connection: StructuredStoreConnection,
    workspace_id: str,
    authorization: str | None,
    session_cookie: str | None = None,
) -> None:
    if not WORKSPACE_ID_RE.fullmatch(workspace_id):
        raise SkeletonError(404, "workspace_not_found")
    token = _presented_access_token(authorization, session_cookie)
    assert token is not None
    row = connection.execute(
        """
        SELECT 1
        FROM access_tokens at
        JOIN workspace_retention wr ON wr.workspace_id = at.workspace_id
        WHERE at.token_hash = ? AND at.workspace_id = ? AND at.expires_at > ?
          AND wr.state = 'active'
        """,
        (_hash_capability(token), workspace_id, _timestamp()),
    ).fetchone()
    if row is None:
        raise SkeletonError(404, "workspace_not_found")


def _workspace_secret_matches(
    connection: StructuredStoreConnection,
    workspace_id: str,
    workspace_secret: str,
) -> bool:
    """Verify a workspace capability without making ID existence observable.

    The secret has 256 bits of CSPRNG entropy, so a SHA-256 digest is an
    irreversible verifier rather than a password hash. Both unknown IDs and
    wrong secrets perform one indexed lookup, one digest and one constant-time
    comparison before returning the same public error.
    """

    id_is_valid = bool(WORKSPACE_ID_RE.fullmatch(workspace_id))
    secret_is_valid = bool(RECOVERY_CODE_RE.fullmatch(workspace_secret))
    lookup_id = workspace_id if id_is_valid else DUMMY_WORKSPACE_ID
    candidate = workspace_secret if secret_is_valid else DUMMY_WORKSPACE_SECRET
    row = connection.execute(
        """
        SELECT w.recovery_hash
        FROM workspaces w
        JOIN workspace_retention wr ON wr.workspace_id = w.workspace_id
        WHERE w.workspace_id = ? AND wr.state = 'active'
        """,
        (lookup_id,),
    ).fetchone()
    stored_verifier = (
        str(row["recovery_hash"])
        if row is not None and SHA256_HEX_RE.fullmatch(str(row["recovery_hash"]))
        else DUMMY_WORKSPACE_VERIFIER
    )
    matches = hmac.compare_digest(
        stored_verifier,
        _hash_capability(candidate),
    )
    return id_is_valid and secret_is_valid and row is not None and matches


def _issue_workspace_session_in_transaction(
    connection: StructuredStoreConnection,
    workspace_id: str,
    *,
    audit_action: str,
) -> tuple[str, str]:
    access_token, expires_at = _issue_access_token(connection, workspace_id)
    _append_audit(connection, workspace_id, audit_action)
    return access_token, expires_at


def _workspace_session_payload(
    connection: StructuredStoreConnection,
    workspace_id: str,
    access_token: str,
    expires_at: str,
) -> dict[str, Any]:
    return {
        "workspace": _workspace_payload(connection, workspace_id),
        "access_token": access_token,
        "access_expires_at": expires_at,
        "session_ttl_seconds": int(ACCESS_TOKEN_TTL.total_seconds()),
    }


def _set_session_cookie(response: Response, access_token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=access_token,
        max_age=int(ACCESS_TOKEN_TTL.total_seconds()),
        path=SESSION_COOKIE_PATH,
        secure=True,
        httponly=True,
        samesite=SESSION_COOKIE_SAMESITE,
    )
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-KMFA-Session-Transport"] = "secure-http-only-cookie"


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path=SESSION_COOKIE_PATH,
        secure=True,
        httponly=True,
        samesite=SESSION_COOKIE_SAMESITE,
    )
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-KMFA-Session-Transport"] = "revoked"


def _browser_session_payload(
    payload: dict[str, Any],
    response: Response,
) -> dict[str, Any]:
    safe_payload = dict(payload)
    access_token = str(safe_payload.pop("access_token"))
    _set_session_cookie(response, access_token)
    safe_payload["session_transport"] = "secure-http-only-cookie"
    safe_payload["session_cookie_path"] = SESSION_COOKIE_PATH
    safe_payload["session_revocable"] = True
    return safe_payload


def _create_workspace(project_name: str) -> dict[str, Any]:
    cleaned_name = _clean_project_name(project_name)
    recovery_code = _new_recovery_code()
    with _store() as connection:
        for _ in range(5):
            workspace_id = _new_workspace_id()
            try:
                connection.execute("BEGIN IMMEDIATE")
                workspace_count = int(
                    connection.execute(
                        """
                        SELECT COUNT(*) AS count_value
                        FROM workspace_retention
                        WHERE state != 'deleted'
                        """
                    ).fetchone()["count_value"]
                )
                if workspace_count >= MAX_WORKSPACES_TOTAL:
                    raise SkeletonError(429, "workspace_capacity_reached")
                now = _timestamp()
                connection.execute(
                    """
                    INSERT INTO workspaces(
                      workspace_id, recovery_hash, project_name, progress,
                      created_at, updated_at
                    ) VALUES (?, ?, ?, 0, ?, ?)
                    """,
                    (
                        workspace_id,
                        _hash_capability(recovery_code),
                        cleaned_name,
                        now,
                        now,
                    ),
                )
                StructuredRepository(connection).create_project_projection(
                    workspace_id=workspace_id,
                    name=cleaned_name,
                    progress=0,
                    created_at=now,
                    updated_at=now,
                )
                LifecycleRepository(connection).ensure_workspace_retention(
                    workspace_id=workspace_id,
                    created_at=now,
                    updated_at=now,
                )
                access_token, expires_at = _issue_access_token(connection, workspace_id)
                _append_audit(connection, workspace_id, "workspace_created")
                connection.execute("COMMIT")
                return {
                    "workspace": _workspace_payload(connection, workspace_id),
                    "access_token": access_token,
                    "access_expires_at": expires_at,
                    "recovery_code": recovery_code,
                    "recovery_code_shown_once": True,
                }
            except StructuredStoreIntegrityError:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
        raise SkeletonError(503, "workspace_identity_unavailable")


def _recover_workspace(recovery_code: str) -> dict[str, Any]:
    if not RECOVERY_CODE_RE.fullmatch(recovery_code):
        raise SkeletonError(404, "recovery_not_found")
    with _store() as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            workspace = connection.execute(
                """
                SELECT w.workspace_id
                FROM workspaces w
                JOIN workspace_retention wr ON wr.workspace_id = w.workspace_id
                WHERE w.recovery_hash = ? AND wr.state = 'active'
                """,
                (_hash_capability(recovery_code),),
            ).fetchone()
            if workspace is None:
                raise SkeletonError(404, "recovery_not_found")
            workspace_id = str(workspace["workspace_id"])
            access_token, expires_at = _issue_workspace_session_in_transaction(
                connection,
                workspace_id,
                audit_action="workspace_recovered",
            )
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        payload = _workspace_session_payload(
            connection,
            workspace_id,
            access_token,
            expires_at,
        )
        payload["recovery_code_shown_once"] = False
        return payload


def _exchange_workspace_session(
    workspace_id: str,
    workspace_secret: str,
    *,
    audit_action: str = "workspace_session_exchanged",
    not_found_code: str = "workspace_not_found",
) -> dict[str, Any]:
    with _store() as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            if not _workspace_secret_matches(
                connection,
                workspace_id,
                workspace_secret,
            ):
                raise SkeletonError(404, not_found_code)
            access_token, expires_at = _issue_workspace_session_in_transaction(
                connection,
                workspace_id,
                audit_action=audit_action,
            )
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        payload = _workspace_session_payload(
            connection,
            workspace_id,
            access_token,
            expires_at,
        )
        payload["workspace_secret_returned"] = False
        return payload


def _export_recovery_file(
    workspace_id: str,
    authorization: str | None,
    workspace_secret: str,
    session_cookie: str | None = None,
) -> bytes:
    with _store() as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            _authorize(connection, workspace_id, authorization, session_cookie)
            if not _workspace_secret_matches(
                connection,
                workspace_id,
                workspace_secret,
            ):
                raise SkeletonError(404, "workspace_not_found")
            _append_audit(connection, workspace_id, "recovery_file_exported")
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
    return _recovery_file_bytes(workspace_id, workspace_secret)


def _import_recovery_file(payload: bytes) -> dict[str, Any]:
    workspace_id, workspace_secret = _parse_recovery_file(payload)
    result = _exchange_workspace_session(
        workspace_id,
        workspace_secret,
        audit_action="recovery_file_imported",
        not_found_code="recovery_not_found",
    )
    result["recovery_file_imported"] = True
    return result


def _rotate_workspace_secret(
    workspace_id: str,
    authorization: str | None,
    session_cookie: str | None = None,
) -> dict[str, Any]:
    with _store() as connection:
        for _ in range(5):
            workspace_secret = _new_recovery_code()
            try:
                connection.execute("BEGIN IMMEDIATE")
                _authorize(connection, workspace_id, authorization, session_cookie)
                connection.execute(
                    """
                    UPDATE workspaces SET recovery_hash = ?, updated_at = ?
                    WHERE workspace_id = ?
                    """,
                    (
                        _hash_capability(workspace_secret),
                        _timestamp(),
                        workspace_id,
                    ),
                )
                revoked_session_count = connection.execute(
                    "DELETE FROM access_tokens WHERE workspace_id = ?",
                    (workspace_id,),
                ).rowcount
                access_token, expires_at = _issue_access_token(
                    connection,
                    workspace_id,
                )
                _append_audit(
                    connection,
                    workspace_id,
                    "workspace_sessions_revoked",
                )
                _append_audit(connection, workspace_id, "workspace_secret_rotated")
                connection.execute("COMMIT")
                return {
                    "workspace_id": workspace_id,
                    "workspace_secret": workspace_secret,
                    "workspace_secret_shown_once": True,
                    "previous_workspace_secret_revoked": True,
                    "existing_sessions_revoked": True,
                    "revoked_session_count": revoked_session_count,
                    "access_token": access_token,
                    "access_expires_at": expires_at,
                    "session_ttl_seconds": int(ACCESS_TOKEN_TTL.total_seconds()),
                }
            except StructuredStoreIntegrityError:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
    raise SkeletonError(503, "workspace_identity_unavailable")


def _revoke_current_session(
    authorization: str | None,
    session_cookie: str | None,
) -> bool:
    token = _presented_access_token(
        authorization,
        session_cookie,
        allow_missing=True,
    )
    if token is None:
        return False
    with _store() as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            row = connection.execute(
                "SELECT workspace_id FROM access_tokens WHERE token_hash = ?",
                (_hash_capability(token),),
            ).fetchone()
            if row is None:
                connection.execute("COMMIT")
                return False
            workspace_id = str(row["workspace_id"])
            connection.execute(
                "DELETE FROM access_tokens WHERE token_hash = ?",
                (_hash_capability(token),),
            )
            _append_audit(connection, workspace_id, "workspace_session_revoked")
            connection.execute("COMMIT")
            return True
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise


async def _read_recovery_file_request(request: Request) -> bytes:
    media_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    if media_type.strip() != RECOVERY_FILE_MEDIA_TYPE:
        raise SkeletonError(415, "invalid_recovery_file")
    content_length = request.headers.get("content-length", "").strip()
    if content_length:
        try:
            declared = int(content_length)
        except ValueError as exc:
            raise SkeletonError(400, "invalid_content_length") from exc
        if declared < 0:
            raise SkeletonError(400, "invalid_content_length")
        if declared > MAX_RECOVERY_FILE_BYTES:
            raise SkeletonError(413, "recovery_file_too_large")
    payload = bytearray()
    async for chunk in request.stream():
        payload.extend(chunk)
        if len(payload) > MAX_RECOVERY_FILE_BYTES:
            raise SkeletonError(413, "recovery_file_too_large")
    return bytes(payload)


def _get_workspace(
    workspace_id: str,
    authorization: str | None,
    session_cookie: str | None = None,
) -> dict[str, Any]:
    with _store() as connection:
        _authorize(connection, workspace_id, authorization, session_cookie)
        return _workspace_payload(connection, workspace_id)


def _update_workspace(
    workspace_id: str,
    authorization: str | None,
    request: UpdateWorkspaceRequest,
    session_cookie: str | None = None,
) -> dict[str, Any]:
    if request.project_name is None and request.progress is None:
        raise SkeletonError(422, "workspace_update_required")
    project_name = (
        _clean_project_name(request.project_name)
        if request.project_name is not None
        else None
    )
    with _store() as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            _authorize(connection, workspace_id, authorization, session_cookie)
            current = StructuredRepository(
                connection
            ).workspace_projection(workspace_id)
            if current is None:
                raise SkeletonError(404, "workspace_not_found")
            resolved_name = (
                project_name if project_name is not None else current["project_name"]
            )
            resolved_progress = (
                request.progress
                if request.progress is not None
                else current["progress"]
            )
            now = _timestamp()
            connection.execute(
                """
                UPDATE workspaces SET project_name = ?, progress = ?, updated_at = ?
                WHERE workspace_id = ?
                """,
                (resolved_name, resolved_progress, now, workspace_id),
            )
            StructuredRepository(connection).save_project_projection(
                workspace_id=workspace_id,
                name=str(resolved_name),
                progress=int(resolved_progress),
                updated_at=now,
            )
            _append_audit(connection, workspace_id, "workspace_saved")
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        return _workspace_payload(connection, workspace_id)


def _request_workspace_deletion(
    workspace_id: str,
    authorization: str | None,
    session_cookie: str | None,
    request: DeleteWorkspaceRequest,
    idempotency_key: str | None,
) -> dict[str, Any]:
    if idempotency_key is None:
        raise SkeletonError(422, "idempotency_key_required")
    with _store() as connection:
        try:
            with connection.transaction():
                repository = LifecycleRepository(connection)
                request_fingerprint = deletion_request_fingerprint(
                    workspace_id=workspace_id,
                    confirmation=request.confirmation,
                    idempotency_key=idempotency_key,
                    workspace_secret=request.workspace_secret,
                )
                deletion = repository.replay_workspace_deletion(
                    workspace_id=workspace_id,
                    idempotency_key=idempotency_key,
                    request_fingerprint=request_fingerprint,
                )
                if deletion is None:
                    _authorize(
                        connection,
                        workspace_id,
                        authorization,
                        session_cookie,
                    )
                    if not _workspace_secret_matches(
                        connection,
                        workspace_id,
                        request.workspace_secret,
                    ):
                        raise SkeletonError(404, "workspace_not_found")
                    deletion = repository.request_workspace_deletion(
                        workspace_id=workspace_id,
                        idempotency_key=idempotency_key,
                        confirmation=request.confirmation,
                        request_fingerprint=request_fingerprint,
                        deletion_request_id=new_deletion_request_id(),
                        timestamp=_timestamp(),
                    )
        except LifecyclePausedError as exc:
            raise SkeletonError(503, "lifecycle_deletion_paused") from exc
        except RestoreProofRequiredError as exc:
            raise SkeletonError(
                503, "deletion_restore_proof_required"
            ) from exc
        except LifecycleLegalHoldError as exc:
            raise SkeletonError(409, "workspace_legal_hold") from exc
        except LifecycleConflictError as exc:
            code = str(exc)
            status = 404 if code == "workspace_not_found" else 409
            if code in {
                "deletion_confirmation_required",
                "invalid_idempotency_key",
            }:
                status = 422
            raise SkeletonError(status, code) from exc
        return {
            "deletion_request_id": deletion["deletion_request_id"],
            "state": deletion["state"],
            "public_purge_due_at": deletion["public_purge_due_at"],
            "access_revoked": True,
            "default_retention_expiry": None,
            "status": (
                "completed"
                if str(deletion["state"]) == "completed"
                else "accepted"
            ),
        }


def _staged_file_digests(path: Path) -> tuple[int, str, Any]:
    if path.is_symlink() or not path.is_file():
        raise SkeletonError(503, "walking_skeleton_storage_unavailable")
    sha256_digest = hashlib.sha256()
    md5_digest = hashlib.md5(usedforsecurity=False)
    size = 0
    try:
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                size += len(chunk)
                sha256_digest.update(chunk)
                md5_digest.update(chunk)
    except OSError as exc:
        raise SkeletonError(
            503, "walking_skeleton_storage_unavailable"
        ) from exc
    return size, sha256_digest.hexdigest(), md5_digest


def _ensure_staged_upload(
    request_path: Path,
    operation: Any,
) -> Path:
    staged_name = str(operation["staged_object_name"])
    if (
        Path(staged_name).name != staged_name
        or "/" in staged_name
        or "\\" in staged_name
    ):
        raise SkeletonError(503, "walking_skeleton_storage_unavailable")
    staged_path = _tmp_dir() / staged_name
    try:
        if not staged_path.exists():
            os.link(request_path, staged_path)
            staged_path.chmod(0o600)
            descriptor = os.open(_tmp_dir(), os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    except FileExistsError:
        pass
    except OSError as exc:
        raise SkeletonError(
            503, "walking_skeleton_storage_unavailable"
        ) from exc
    actual_size, actual_sha256, _ = _staged_file_digests(staged_path)
    if (
        actual_size != int(operation["size_bytes"])
        or actual_sha256 != str(operation["content_sha256"])
    ):
        raise SkeletonError(409, "artifact_upload_isolated")
    return staged_path


def _load_consistency_operation(operation_id: str) -> dict[str, Any]:
    with _store() as connection:
        row = ConsistencyRepository(connection).operation(operation_id)
        if row is None:
            raise SkeletonError(503, "walking_skeleton_storage_unavailable")
        return dict(row)


def _record_upload_retry(
    operation_id: str,
    *,
    state: str,
    error_code: str,
) -> None:
    with _store() as connection:
        with connection.transaction():
            current = ConsistencyRepository(connection).operation(operation_id)
            if current is None or str(current["state"]) != state:
                return
            ConsistencyRepository(connection).record_attempt_failure(
                operation_id,
                expected_state=state,
                error_code=error_code,
                timestamp=_timestamp(),
            )


def _isolate_upload(
    operation_id: str,
    *,
    expected_state: str,
    error_code: str,
) -> None:
    with _store() as connection:
        with connection.transaction():
            repository = ConsistencyRepository(connection)
            current = repository.operation(operation_id)
            if current is None:
                raise SkeletonError(503, "walking_skeleton_storage_unavailable")
            state = str(current["state"])
            if state == "converged":
                raise SkeletonError(503, "walking_skeleton_storage_unavailable")
            if state not in {expected_state, "isolated"}:
                # Another reconciler advanced the operation after the caller's
                # observation. Its newer state is authoritative; do not apply a
                # stale isolation decision.
                return
            repository.quarantine_object(
                operation_id=operation_id,
                storage_backend=str(current["storage_backend"]),
                storage_key=str(current["storage_key"]),
                reason_code=error_code,
                timestamp=_timestamp(),
            )
            if state != "isolated":
                repository.isolate(
                    operation_id,
                    expected_state=state,
                    error_code=error_code,
                    timestamp=_timestamp(),
                )


def _resume_upload_operation(
    operation_id: str,
    object_store: Any,
    *,
    fault_hook: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    def fault(point: str) -> None:
        if fault_hook is not None:
            fault_hook(point)

    for _ in range(8):
        operation = _load_consistency_operation(operation_id)
        state = str(operation["state"])
        if state == "isolated":
            raise SkeletonError(409, "artifact_upload_isolated")
        if state == "converged":
            with _store() as connection:
                payload = _workspace_payload(
                    connection,
                    str(operation["workspace_id"]),
                )
            if payload["artifact"] is None:
                raise SkeletonError(503, "walking_skeleton_storage_unavailable")
            return payload

        if state == "intent_recorded":
            with _store() as connection:
                with connection.transaction():
                    ConsistencyRepository(connection).transition(
                        operation_id,
                        expected_state="intent_recorded",
                        to_state="effect_pending",
                        transition_code="object_write_started",
                        timestamp=_timestamp(),
                    )
            fault("effect_pending")
            continue

        if state == "effect_pending":
            staged_name = str(operation["staged_object_name"])
            staged_path = _tmp_dir() / staged_name
            try:
                operation_backend = str(operation["storage_backend"])
                if (
                    object_store is None
                    or getattr(object_store, "storage_backend", None)
                    != operation_backend
                ):
                    object_store = object_store_for_backend(
                        _state_root(),
                        operation_backend,
                    )
                    object_store.ensure_ready()
                if staged_path.is_file() and not staged_path.is_symlink():
                    actual_size, actual_sha256, md5_digest = (
                        _staged_file_digests(staged_path)
                    )
                    if (
                        actual_size != int(operation["size_bytes"])
                        or actual_sha256 != str(operation["content_sha256"])
                    ):
                        raise ObjectStorageIntegrityError(
                            "object_integrity_failed"
                        )
                    try:
                        object_store.put_file(
                            staged_path,
                            storage_key=str(operation["storage_key"]),
                            size_bytes=int(operation["size_bytes"]),
                            sha256=str(operation["content_sha256"]),
                            content_md5=content_md5_base64(md5_digest),
                            artifact_id=str(operation["artifact_id"]),
                            artifact_version_id=str(
                                operation["artifact_version_id"]
                            ),
                        )
                    except ObjectStorageConflictError:
                        object_store.verify_existing(
                            storage_key=str(operation["storage_key"]),
                            expected_size=int(operation["size_bytes"]),
                            expected_sha256=str(operation["content_sha256"]),
                            artifact_id=str(operation["artifact_id"]),
                            artifact_version_id=str(
                                operation["artifact_version_id"]
                            ),
                        )
                    except ObjectStorageUnavailableError:
                        object_store.verify_existing(
                            storage_key=str(operation["storage_key"]),
                            expected_size=int(operation["size_bytes"]),
                            expected_sha256=str(operation["content_sha256"]),
                            artifact_id=str(operation["artifact_id"]),
                            artifact_version_id=str(
                                operation["artifact_version_id"]
                            ),
                        )
                else:
                    object_store.verify_existing(
                        storage_key=str(operation["storage_key"]),
                        expected_size=int(operation["size_bytes"]),
                        expected_sha256=str(operation["content_sha256"]),
                        artifact_id=str(operation["artifact_id"]),
                        artifact_version_id=str(
                            operation["artifact_version_id"]
                        ),
                    )
            except (
                ObjectStorageConfigurationError,
                ObjectStorageMissingError,
                ObjectStorageUnavailableError,
                OSError,
            ) as exc:
                _record_upload_retry(
                    operation_id,
                    state="effect_pending",
                    error_code="object_write_retryable",
                )
                raise SkeletonError(
                    503, "walking_skeleton_storage_unavailable"
                ) from exc
            except (ObjectStorageConflictError, ObjectStorageIntegrityError) as exc:
                _isolate_upload(
                    operation_id,
                    expected_state="effect_pending",
                    error_code="object_identity_mismatch",
                )
                raise SkeletonError(409, "artifact_upload_isolated") from exc

            fault("primary_effect_applied")
            with _store() as connection:
                with connection.transaction():
                    ConsistencyRepository(connection).transition(
                        operation_id,
                        expected_state="effect_pending",
                        to_state="effect_applied",
                        transition_code="object_write_verified",
                        timestamp=_timestamp(),
                        increment_attempt=True,
                    )
            fault("effect_applied")
            try:
                staged_path.unlink(missing_ok=True)
            except OSError:
                pass
            continue

        if state == "effect_applied":
            # The durable state proves the object was verified. A crash between
            # that commit and normal staging cleanup may leave only a redundant
            # local hardlink, which is now safe to remove.
            try:
                (_tmp_dir() / str(operation["staged_object_name"])).unlink(
                    missing_ok=True
                )
            except OSError:
                pass
            with _store() as connection:
                with connection.transaction():
                    ConsistencyRepository(connection).transition(
                        operation_id,
                        expected_state="effect_applied",
                        to_state="commit_pending",
                        transition_code="database_commit_started",
                        timestamp=_timestamp(),
                    )
            fault("commit_pending")
            continue

        if state == "commit_pending":
            projection_conflict = False
            try:
                with _store() as connection:
                    try:
                        with connection.transaction():
                            consistency = ConsistencyRepository(connection)
                            repository = StructuredRepository(connection)
                            operation = consistency.operation(operation_id)
                            if (
                                operation is None
                                or str(operation["state"]) != "commit_pending"
                            ):
                                continue
                            compatibility = connection.execute(
                                """
                                SELECT artifact_id
                                FROM artifacts
                                WHERE artifact_id = ?
                                """,
                                (operation["artifact_id"],),
                            ).fetchone()
                            if compatibility is None:
                                used_bytes = int(
                                    connection.execute(
                                        """
                                        SELECT COALESCE(SUM(size_bytes), 0)
                                          AS total_bytes
                                        FROM artifacts
                                        """
                                    ).fetchone()["total_bytes"]
                                )
                                if (
                                    used_bytes + int(operation["size_bytes"])
                                    > MAX_TOTAL_ARTIFACT_BYTES
                                ):
                                    raise SkeletonError(
                                        429, "artifact_capacity_reached"
                                    )
                            created_at = str(operation["created_at"])
                            repository.ensure_uploaded_artifact(
                                workspace_id=str(operation["workspace_id"]),
                                artifact_id=str(operation["artifact_id"]),
                                version_number=1,
                                storage_backend=str(operation["storage_backend"]),
                                storage_key=str(operation["storage_key"]),
                                original_name=str(operation["original_name"]),
                                reported_media_type=str(
                                    operation["reported_media_type"]
                                ),
                                size_bytes=int(operation["size_bytes"]),
                                sha256=str(operation["content_sha256"]),
                                created_at=created_at,
                            )
                            connection.execute(
                                """
                                UPDATE workspaces
                                SET updated_at = ?
                                WHERE workspace_id = ?
                                """,
                                (created_at, operation["workspace_id"]),
                            )
                            _append_audit(
                                connection,
                                str(operation["workspace_id"]),
                                "artifact_uploaded",
                                artifact_sha256=str(
                                    operation["content_sha256"]
                                ),
                            )
                            # This durable process request is not a claim that a
                            # business processor already exists or has run.
                            consistency.ensure_outbox(
                                operation_id=operation_id,
                                effect_kind="process",
                                timestamp=_timestamp(),
                            )
                            consistency.transition(
                                operation_id,
                                expected_state="commit_pending",
                                to_state="outbox_committed",
                                transition_code="database_and_outbox_committed",
                                timestamp=_timestamp(),
                            )
                    except StructuredStoreIntegrityError:
                        projection_conflict = True
            except SkeletonError as exc:
                if exc.code in {
                    "artifact_capacity_reached",
                    "workspace_audit_capacity_reached",
                }:
                    _isolate_upload(
                        operation_id,
                        expected_state="commit_pending",
                        error_code="database_capacity_isolated",
                    )
                raise
            if projection_conflict:
                _isolate_upload(
                    operation_id,
                    expected_state="commit_pending",
                    error_code="database_projection_conflict",
                )
                raise SkeletonError(409, "artifact_upload_isolated")
            fault("outbox_committed")
            continue

        if state == "outbox_committed":
            with _store() as connection:
                with connection.transaction():
                    ConsistencyRepository(connection).transition(
                        operation_id,
                        expected_state="outbox_committed",
                        to_state="converged",
                        transition_code="upload_converged",
                        timestamp=_timestamp(),
                    )
            fault("converged")
            continue
        raise SkeletonError(503, "walking_skeleton_storage_unavailable")
    raise SkeletonError(503, "walking_skeleton_storage_unavailable")


def _persist_completed_upload(
    *,
    workspace_id: str,
    request_path: Path,
    size: int,
    sha256: str,
    filename: str,
    media_type: str,
    idempotency_key: str,
    key_hash: str,
    object_store: Any,
    operation_id: str,
    artifact_id: str,
    version_number: int,
    version_id: str,
) -> dict[str, Any]:
    """把一个**已经完整落盘且已知摘要**的文件交给持久化链。

    S06/P6.1 从 `_store_artifact` 里抽出来，为的是让断点续传的 complete 走
    **同一条**链而不是复制一份：idempotency、竞争上传检测、容量复核、
    staging 硬链校验、isolate 处置——这些是 S05 一条条挣出来的，
    复制一份等于让续传这条路重新踩一遍同样的坑。

    调用方各自负责把字节写到 `request_path` 并给出 size/sha256：
    单次上传边收边算，续传在 complete 时对暂存文件整体重算。
    """
    try:
        fingerprint = upload_request_fingerprint(
            workspace_id=workspace_id,
            original_name=filename,
            reported_media_type=media_type,
            size_bytes=size,
            content_sha256=sha256,
        )
        storage_key = object_store.build_storage_key(
            workspace_id=workspace_id,
            artifact_id=artifact_id,
            artifact_version_id=version_id,
            version_number=version_number,
            sha256=sha256,
        )
        intent = UploadIntent(
            workspace_id=workspace_id,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
            artifact_id=artifact_id,
            artifact_version_id=version_id,
            storage_backend=object_store.storage_backend,
            storage_key=storage_key,
            staged_object_name=f"workflow-{operation_id}.part",
            original_name=filename,
            reported_media_type=media_type,
            size_bytes=size,
            content_sha256=sha256,
        )
        with _store() as connection:
            try:
                with connection.transaction():
                    consistency = ConsistencyRepository(connection)
                    durable_replay = consistency.operation_for_idempotency(
                        workspace_id=workspace_id,
                        operation_kind="upload",
                        idempotency_key_hash_value=key_hash,
                    )
                    if durable_replay is None:
                        competing_upload = connection.execute(
                            """
                            SELECT 1
                            FROM consistency_operations
                            WHERE workspace_id = ?
                              AND operation_kind = 'upload'
                              AND state NOT IN ('converged', 'isolated')
                            LIMIT 1
                            """,
                            (workspace_id,),
                        ).fetchone()
                        projected_artifact = connection.execute(
                            """
                            SELECT 1 FROM artifacts
                            WHERE workspace_id = ?
                            LIMIT 1
                            """,
                            (workspace_id,),
                        ).fetchone()
                        if (
                            competing_upload is not None
                            or projected_artifact is not None
                        ):
                            raise SkeletonError(409, "artifact_limit_reached")
                        if (
                            _artifact_capacity_usage(connection) + size
                            > MAX_TOTAL_ARTIFACT_BYTES
                        ):
                            raise SkeletonError(
                                429,
                                "artifact_capacity_reached",
                            )
                    identity = consistency.create_or_load_upload(
                        intent,
                        operation_id=operation_id,
                        timestamp=_timestamp(),
                    )
                    operation = consistency.operation(identity.operation_id)
                    if operation is None:
                        raise SkeletonError(
                            503, "walking_skeleton_storage_unavailable"
                        )
                    operation = dict(operation)
            except ConsistencyConflictError as exc:
                raise SkeletonError(409, "idempotency_key_conflict") from exc
        if str(operation["state"]) in {"intent_recorded", "effect_pending"}:
            try:
                _ensure_staged_upload(request_path, operation)
            except SkeletonError as exc:
                if exc.code == "artifact_upload_isolated":
                    _isolate_upload(
                        identity.operation_id,
                        expected_state=str(operation["state"]),
                        error_code="staged_object_mismatch",
                    )
                raise
        # Once the durable intent either owns a verified staging hardlink or
        # has advanced beyond object verification, the random request name is
        # redundant. Remove it before any injected/process crash can strand an
        # untracked full-file copy.
        request_path.unlink(missing_ok=True)
        descriptor = os.open(_tmp_dir(), os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return _resume_upload_operation(identity.operation_id, object_store)
    finally:
        request_path.unlink(missing_ok=True)


async def _store_artifact(
    workspace_id: str,
    authorization: str | None,
    session_cookie: str | None,
    filename_header: str | None,
    idempotency_key_header: str | None,
    request: Request,
) -> dict[str, Any]:
    if consistency_state_mode() == CONSISTENCY_PAUSED_MODE:
        raise SkeletonError(503, "consistency_processing_paused")
    filename = _clean_filename(filename_header)
    idempotency_key = _resolved_idempotency_key(idempotency_key_header)
    try:
        key_hash = idempotency_key_hash(idempotency_key)
    except ConsistencyStateError as exc:
        raise SkeletonError(422, "invalid_idempotency_key") from exc
    content_length = request.headers.get("content-length", "").strip()
    declared_length: int | None = None
    if content_length:
        try:
            declared_length = int(content_length)
        except ValueError as exc:
            raise SkeletonError(400, "invalid_content_length") from exc
        if declared_length < 0:
            raise SkeletonError(400, "invalid_content_length")
        if declared_length > MAX_ARTIFACT_BYTES:
            raise SkeletonError(413, "artifact_too_large")

    with _store() as connection:
        _authorize(connection, workspace_id, authorization, session_cookie)
        existing_operation = ConsistencyRepository(
            connection
        ).operation_for_idempotency(
            workspace_id=workspace_id,
            operation_kind="upload",
            idempotency_key_hash_value=key_hash,
        )
        if (
            connection.execute(
                "SELECT 1 FROM artifacts WHERE workspace_id = ?",
                (workspace_id,),
            ).fetchone()
            and existing_operation is None
        ):
            raise SkeletonError(409, "artifact_limit_reached")
        if existing_operation is None:
            used_bytes = _artifact_capacity_usage(connection)
            remaining_bytes = MAX_TOTAL_ARTIFACT_BYTES - used_bytes
            if remaining_bytes <= 0:
                raise SkeletonError(429, "artifact_capacity_reached")
            if declared_length is not None and declared_length > remaining_bytes:
                raise SkeletonError(429, "artifact_capacity_reached")

    try:
        free_bytes = shutil.disk_usage(_state_root()).free
    except OSError as exc:
        raise SkeletonError(503, "walking_skeleton_storage_unavailable") from exc
    declared_or_max = (
        declared_length if declared_length is not None else MAX_ARTIFACT_BYTES
    )
    if free_bytes - declared_or_max < MIN_FREE_STATE_BYTES:
        raise SkeletonError(429, "artifact_capacity_reached")

    try:
        object_store = configured_write_store(_state_root())
        object_store.ensure_ready()
    except (
        ObjectStorageConfigurationError,
        ObjectStorageUnavailableError,
        OSError,
    ) as exc:
        raise SkeletonError(503, "walking_skeleton_storage_unavailable") from exc

    operation_id = _new_operation_id()
    artifact_id = _new_artifact_id()
    version_number = 1
    version_id = artifact_version_id(artifact_id, version_number)
    request_path = _tmp_dir() / f"request-{secrets.token_urlsafe(24)}.part"
    sha256_digest = hashlib.sha256()
    size = 0
    descriptor = os.open(
        request_path,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "wb") as output:
            async for chunk in request.stream():
                if not chunk:
                    continue
                size += len(chunk)
                if size > MAX_ARTIFACT_BYTES:
                    raise SkeletonError(413, "artifact_too_large")
                sha256_digest.update(chunk)
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        sha256 = sha256_digest.hexdigest()
        media_type = _clean_media_type(request.headers.get("content-type"))
        return _persist_completed_upload(
            workspace_id=workspace_id, request_path=request_path, size=size,
            sha256=sha256, filename=filename, media_type=media_type,
            idempotency_key=idempotency_key, key_hash=key_hash,
            object_store=object_store, operation_id=operation_id,
            artifact_id=artifact_id, version_number=version_number,
            version_id=version_id,
        )
    finally:
        request_path.unlink(missing_ok=True)


def _audit_artifact_download(
    workspace_id: str,
    authorization: str | None,
    session_cookie: str | None,
    *,
    result_status: str,
    artifact_sha256: str | None = None,
) -> None:
    with _store() as connection:
        _authorize(connection, workspace_id, authorization, session_cookie)
        _append_audit(
            connection,
            workspace_id,
            "artifact_download",
            result_status=result_status,
            artifact_sha256=artifact_sha256,
        )


def _artifact_for_download(
    workspace_id: str,
    authorization: str | None,
    session_cookie: str | None = None,
) -> tuple[Path, dict[str, Any], bool]:
    with _store() as connection:
        _authorize(connection, workspace_id, authorization, session_cookie)
        artifact = StructuredRepository(connection).latest_artifact_version(
            workspace_id
        )
        if artifact is None:
            raise SkeletonError(404, "artifact_not_found")
        artifact_payload = dict(artifact)

    materialized = None
    try:
        object_store = object_store_for_backend(
            _state_root(),
            str(artifact_payload["storage_backend"]),
        )
        materialized = object_store.materialize_verified(
            storage_key=str(artifact_payload["storage_key"]),
            expected_size=int(artifact_payload["size_bytes"]),
            expected_sha256=str(artifact_payload["sha256"]),
        )
    except ObjectStorageMissingError as exc:
        _audit_artifact_download(
            workspace_id,
            authorization,
            session_cookie,
            result_status="missing",
        )
        raise SkeletonError(503, "artifact_unavailable") from exc
    except ObjectStorageIntegrityError as exc:
        _audit_artifact_download(
            workspace_id,
            authorization,
            session_cookie,
            result_status="integrity_failed",
        )
        raise SkeletonError(503, "artifact_integrity_failed") from exc
    except (
        ObjectStorageConfigurationError,
        ObjectStorageUnavailableError,
    ) as exc:
        _audit_artifact_download(
            workspace_id,
            authorization,
            session_cookie,
            result_status="unavailable",
        )
        raise SkeletonError(503, "artifact_unavailable") from exc

    try:
        _audit_artifact_download(
            workspace_id,
            authorization,
            session_cookie,
            result_status="ok",
            artifact_sha256=str(artifact_payload["sha256"]),
        )
    except Exception:
        if materialized.temporary:
            materialized.path.unlink(missing_ok=True)
        raise
    return materialized.path, artifact_payload, materialized.temporary


def _audit_events(
    workspace_id: str,
    authorization: str | None,
    session_cookie: str | None = None,
) -> dict[str, Any]:
    with _store() as connection:
        _authorize(connection, workspace_id, authorization, session_cookie)
        rows = connection.execute(
            """
            SELECT action, result_status, artifact_sha256, created_at
            FROM audit_events WHERE workspace_id = ? ORDER BY seq
            """,
            (workspace_id,),
        ).fetchall()
        return {
            "workspace_id": workspace_id,
            "append_only": True,
            "events": [dict(row) for row in rows],
        }


@router.get("/status")
def walking_skeleton_status() -> dict[str, Any]:
    enabled = walking_skeleton_enabled()
    if not enabled:
        return {
            "enabled": False,
            "mode": "rollback",
            "preserves_existing_data": True,
            "stage_status": "early-skeleton-not-ga",
        }
    try:
        consistency_mode = consistency_state_mode()
        retention_mode = lifecycle_mode()
        with _store() as connection:
            schema_version = connection.schema_version()
            structured_store = connection.backend_name
            connection.execute("SELECT 1").fetchone()
            restore_proof = LifecycleRepository(
                connection
            ).active_restore_proof()
        object_store = configured_write_store(_state_root())
        object_store.ensure_ready()
    except (SkeletonError, LifecyclePausedError) as error:
        if isinstance(error, SkeletonError):
            _raise_http(error)
        _raise_http(SkeletonError(503, "lifecycle_mode_invalid"))
    except (
        ObjectStorageConfigurationError,
        ObjectStorageUnavailableError,
        OSError,
    ):
        _raise_http(
            SkeletonError(503, "walking_skeleton_storage_unavailable")
        )
    return {
        "enabled": True,
        "mode": "early-skeleton",
        "healthy": True,
        "schema_version": schema_version,
        "structured_store": structured_store,
        "structured_data": {
            "projects": True,
            "progress": True,
            "scores": True,
            "financial_records": True,
            "artifact_versions": True,
            "tasks": True,
            "migration_strategy": "expand-only-forward-fix",
            "legacy_sqlite_read_path": True,
        },
        "artifact_store": object_store.public_label,
        "artifact_storage": {
            "write_backend": object_store.storage_backend,
            "access_contract": "server-credential-only-private-required",
            "application_issues_public_object_urls": False,
            "bucket_policy_verified_by": "deployment-oracle-required",
            "application_versioning": (
                "immutable-key-v1"
                if object_store.application_versioning
                else "legacy-single-object"
            ),
            "conditional_create": object_store.storage_backend
            == S3_STORAGE_BACKEND,
            "legacy_filesystem_read": True,
            "s3_dual_read_configured": s3_dual_read_configured(),
            "inventory_reconciliation": object_store.storage_backend
            == S3_STORAGE_BACKEND,
        },
        "consistency_state": {
            "schema": "recoverable-state-v1",
            "mode": consistency_mode,
            "new_uploads_paused": consistency_mode == CONSISTENCY_PAUSED_MODE,
            "upload_path": "wired",
            "operation_kinds": ["upload", "process", "index", "export"],
            "idempotency_header": "Idempotency-Key",
            "idempotency_persistence": "sha256-only",
            "outbox_delivery": "at-least-once-idempotent-consumer-required",
            "reconciliation": "converge-or-isolate",
            "raw_object_compensation_delete": False,
            "business_adapters": "stage-owned-not-claimed-by-p5.3",
        },
        "retention_lifecycle": {
            "mode": retention_mode,
            "default_auto_expiry": False,
            "explicit_workspace_deletion": True,
            "delete_confirmation": DELETE_CONFIRMATION,
            "public_cache_index_purge_sla_seconds": int(
                PUBLIC_PURGE_SLA.total_seconds()
            ),
            "restore_drill_proof_current_schema": restore_proof is not None,
            "restore_drill_max_age_days": RESTORE_PROOF_MAX_AGE.days,
            "worker_lease_seconds": int(
                DELETION_WORKER_LEASE.total_seconds()
            ),
            "application_object_delete_credentials": (
                object_store.storage_backend == LEGACY_STORAGE_BACKEND
            ),
            "worker_uses_separate_credentials": (
                object_store.storage_backend == S3_STORAGE_BACKEND
            ),
        },
        "browser_storage": False,
        "recovery_capability": "high-entropy-server-hashed",
        "access_session_seconds": int(ACCESS_TOKEN_TTL.total_seconds()),
        "anonymous_identity": {
            "workspace_id_entropy_bits": WORKSPACE_ID_BYTES * 8,
            "workspace_secret_entropy_bits": WORKSPACE_SECRET_BYTES * 8,
            "access_token_entropy_bits": ACCESS_TOKEN_BYTES * 8,
            "verifier": "sha256-of-256-bit-secret",
            "session_exchange": f"{API_PREFIX}/sessions",
        },
        "recovery_experience": {
            "file_format": RECOVERY_FILE_FORMAT,
            "file_version": RECOVERY_FILE_VERSION,
            "file_media_type": RECOVERY_FILE_MEDIA_TYPE,
            "max_file_bytes": MAX_RECOVERY_FILE_BYTES,
            "import": f"{API_PREFIX}/recovery-files/import",
            "secret_rotation": True,
            "email_recovery": False,
        },
        "secret_hygiene": {
            "session_transport": "secure-http-only-cookie",
            "cookie": {
                "name": SESSION_COOKIE_NAME,
                "secure": True,
                "http_only": True,
                "same_site": "Strict",
                "path": SESSION_COOKIE_PATH,
                "max_age_seconds": int(ACCESS_TOKEN_TTL.total_seconds()),
            },
            "revocation": f"{API_PREFIX}/sessions/current",
            "legacy_bearer_compatible_until_expiry": True,
            "browser_receives_access_token": False,
            "same_origin_cookie_mutations_required": True,
            "runtime_telemetry": "none",
        },
        "limits": {
            "max_artifacts": MAX_ARTIFACTS,
            "max_bytes": MAX_ARTIFACT_BYTES,
            "max_total_artifact_bytes": MAX_TOTAL_ARTIFACT_BYTES,
            "min_free_state_bytes": MIN_FREE_STATE_BYTES,
            "max_workspaces_total": MAX_WORKSPACES_TOTAL,
            "max_active_sessions_per_workspace": (
                MAX_ACTIVE_SESSIONS_PER_WORKSPACE
            ),
            "max_audit_events_per_workspace": MAX_AUDIT_EVENTS_PER_WORKSPACE,
            "max_audit_events_total": MAX_AUDIT_EVENTS_TOTAL,
            "file_types": "any-stored-attachment-only",
        },
        "abuse_control": public_policy_contract(),
        "stage_status": "early-skeleton-not-ga",
        "hardening_pending": (
            (
                ["durable-database-service"]
                if structured_store.startswith("sqlite")
                else []
            )
            + (
                ["s3-compatible-object-store"]
                if object_store.storage_backend == LEGACY_STORAGE_BACKEND
                else []
            )
            + ([] if restore_proof is not None else ["backup-restore-drill"])
            + (
                ["lifecycle-deletion-worker"]
                if retention_mode != LIFECYCLE_ACTIVE_MODE
                else []
            )
            + [
                "malware-controls",
                "multi-file-lifecycle",
                "process-index-export-business-adapters",
            ]
        ),
    }


@router.post("/workspaces", status_code=201)
def create_workspace(
    request: CreateWorkspaceRequest,
    response: Response,
) -> dict[str, Any]:
    try:
        _require_enabled()
        return _browser_session_payload(
            _create_workspace(request.project_name),
            response,
        )
    except SkeletonError as error:
        _raise_http(error)


@router.post("/recoveries")
def recover_workspace(
    request: RecoverWorkspaceRequest,
    response: Response,
) -> dict[str, Any]:
    try:
        _require_enabled()
        return _browser_session_payload(
            _recover_workspace(request.recovery_code),
            response,
        )
    except SkeletonError as error:
        _raise_http(error)


@router.post("/sessions")
def exchange_workspace_session(
    request: ExchangeWorkspaceSessionRequest,
    response: Response,
) -> dict[str, Any]:
    try:
        _require_enabled()
        return _browser_session_payload(
            _exchange_workspace_session(
                request.workspace_id,
                request.workspace_secret,
            ),
            response,
        )
    except SkeletonError as error:
        _raise_http(error)


@router.post("/recovery-files/import")
async def import_recovery_file(
    request: Request,
    response: Response,
) -> dict[str, Any]:
    try:
        _require_enabled()
        payload = await _read_recovery_file_request(request)
        return _browser_session_payload(
            _import_recovery_file(payload),
            response,
        )
    except SkeletonError as error:
        _raise_http(error)


@router.delete("/sessions/current", status_code=204)
def revoke_current_session(
    authorization: str | None = Header(default=None),
    session_cookie: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
) -> Response:
    response = Response(status_code=204)
    try:
        _revoke_current_session(authorization, session_cookie)
    except SkeletonError as error:
        _raise_http(error)
    # Missing, expired, unknown and already-revoked well-formed sessions are
    # idempotent. Malformed or conflicting header/cookie credentials fail
    # closed above instead of reporting a revocation that did not occur.
    _clear_session_cookie(response)
    return response


@router.get("/workspaces/{workspace_id}")
def get_workspace(
    workspace_id: str,
    authorization: str | None = Header(default=None),
    session_cookie: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
) -> dict[str, Any]:
    try:
        _require_enabled()
        return _get_workspace(workspace_id, authorization, session_cookie)
    except SkeletonError as error:
        _raise_http(error)


@router.post("/workspaces/{workspace_id}/recovery-file")
def export_recovery_file(
    workspace_id: str,
    request: ExportRecoveryFileRequest,
    authorization: str | None = Header(default=None),
    session_cookie: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
) -> Response:
    try:
        _require_enabled()
        payload = _export_recovery_file(
            workspace_id,
            authorization,
            request.workspace_secret,
            session_cookie,
        )
    except SkeletonError as error:
        _raise_http(error)
    return Response(
        content=payload,
        media_type=RECOVERY_FILE_MEDIA_TYPE,
        headers={
            "Cache-Control": "private, no-store",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
            "X-Robots-Tag": "noindex, nofollow, noarchive",
            "Content-Disposition": (
                'attachment; filename="kmfa-workspace.kmfa-recovery"'
            ),
        },
    )


@router.post("/workspaces/{workspace_id}/recovery-secret/rotate")
def rotate_workspace_secret(
    workspace_id: str,
    response: Response,
    authorization: str | None = Header(default=None),
    session_cookie: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
) -> dict[str, Any]:
    try:
        _require_enabled()
        return _browser_session_payload(
            _rotate_workspace_secret(
                workspace_id,
                authorization,
                session_cookie,
            ),
            response,
        )
    except SkeletonError as error:
        _raise_http(error)


@router.patch("/workspaces/{workspace_id}")
def update_workspace(
    workspace_id: str,
    request: UpdateWorkspaceRequest,
    authorization: str | None = Header(default=None),
    session_cookie: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
) -> dict[str, Any]:
    try:
        _require_enabled()
        return _update_workspace(
            workspace_id,
            authorization,
            request,
            session_cookie,
        )
    except SkeletonError as error:
        _raise_http(error)


@router.delete("/workspaces/{workspace_id}", status_code=202)
def delete_workspace(
    workspace_id: str,
    request: DeleteWorkspaceRequest,
    response: Response,
    authorization: str | None = Header(default=None),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
    ),
    session_cookie: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
) -> dict[str, Any]:
    try:
        _require_enabled()
        payload = _request_workspace_deletion(
            workspace_id,
            authorization,
            session_cookie,
            request,
            idempotency_key,
        )
    except SkeletonError as error:
        _raise_http(error)
    _clear_session_cookie(response)
    return payload


# ── S06/P6.1 · T-S06-01：断点续传（AC-UP-001 / AC-UP-002）────────────────────
#
# 会话状态写在 .part 旁边的 sidecar JSON 里，不进 SQLite：
#   AC-UP-002 要的是「进程重启后客户端仍能从服务端问到正确偏移」，
#   sidecar + fsync 已经满足；为此加一张表要动 schema 与迁移，
#   而任务包这一项没有要求 schema 变更——按「只作等价识别或增量适配」办。
# 配额则复用既有的 _artifact_capacity_usage，另加未完成会话的已声明字节，
# 否则并发开多个会话可以整体超额（每个单看都在额度内）。

def _upload_sidecar(upload_id: str) -> Path:
    return _tmp_dir() / f"{upload_id}.session.json"


def _reserved_by_open_sessions() -> int:
    total = 0
    for sidecar in _tmp_dir().glob("up_*.session.json"):
        try:
            state = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        total += max(0, int(state.get("total_bytes", 0)) - int(state.get("received_bytes", 0)))
    return total


def _load_session(workspace_id: str, upload_id: str) -> RU.UploadSession:
    RU.validate_upload_id(upload_id)
    sidecar = _upload_sidecar(upload_id)
    try:
        state = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RU.ResumableUploadError(404, "upload_session_not_found") from exc
    if state.get("workspace_id") != workspace_id:
        # 跨 workspace 读会话等于跨租户信息泄露——按不存在处理，不透露它存在。
        raise RU.ResumableUploadError(404, "upload_session_not_found")
    return RU.UploadSession(
        upload_id=upload_id, workspace_id=workspace_id,
        original_name=state["original_name"], media_type=state["media_type"],
        total_bytes=int(state["total_bytes"]), expected_sha256=state["expected_sha256"],
        received_bytes=int(state["received_bytes"]),
        part_path=Path(state["part_path"]),
    )


def _save_session(session: RU.UploadSession) -> None:
    """先写临时文件再原子改名——半截的 sidecar 会让整个会话读不回来。"""
    sidecar = _upload_sidecar(session.upload_id)
    staging = sidecar.with_suffix(".tmp")
    staging.write_text(json.dumps({
        "workspace_id": session.workspace_id, "original_name": session.original_name,
        "media_type": session.media_type, "total_bytes": session.total_bytes,
        "expected_sha256": session.expected_sha256,
        "received_bytes": session.received_bytes, "part_path": str(session.part_path),
    }, ensure_ascii=False), encoding="utf-8")
    os.replace(staging, sidecar)


@router.post("/workspaces/{workspace_id}/artifact/uploads", status_code=201)
def open_upload_session(
    workspace_id: str,
    payload: dict[str, Any] = Body(...),
    authorization: str | None = Header(default=None),
    session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, Any]:
    """开会话。**准入检查全在这里，一个字节都还没收。**"""
    try:
        _require_enabled()
        total_bytes = payload.get("total_bytes")
        expected = payload.get("content_sha256")
        filename = _clean_filename(payload.get("filename"))
        media_type = _clean_media_type(payload.get("media_type"))
        with _store() as connection:
            _authorize(connection, workspace_id, authorization, session_cookie)
            used = _artifact_capacity_usage(connection) + _reserved_by_open_sessions()
            existing = connection.execute(
                # 列名是 sha256（见 migrations/sqlite/0002_structured_data.sql）。
                # 初版写成 content_sha256，查询抛错被 _store() 兜成 503——
                # 一个列名错误伪装成了「存储不可用」，这类错最难从状态码看出来。
                "SELECT artifact_version_id FROM artifact_versions WHERE sha256 = ? LIMIT 1",
                (expected,),
            ).fetchone() if isinstance(expected, str) and len(expected) == 64 else None
        RU.plan_session(
            total_bytes=total_bytes if isinstance(total_bytes, int) else -1,
            expected_sha256=expected if isinstance(expected, str) else "",
            max_artifact_bytes=MAX_ARTIFACT_BYTES,
            remaining_quota_bytes=MAX_TOTAL_ARTIFACT_BYTES - used,
        )
        decision = RU.dedupe_decision(
            expected_sha256=expected,
            existing_version_id=existing["artifact_version_id"] if existing else None)
        if not decision.accept_bytes:
            # 内容已存在——一个字节都不收（AC-UP-002 重复对象不可控增长=0）
            return {"upload_id": None, "duplicate_of": decision.existing_artifact_version_id,
                    "accept_bytes": False, "reason": decision.reason}
        upload_id = RU.new_upload_id()
        part_path = _tmp_dir() / f"{upload_id}.part"
        descriptor = os.open(part_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        session = RU.UploadSession(
            upload_id=upload_id, workspace_id=workspace_id, original_name=filename,
            media_type=media_type, total_bytes=total_bytes, expected_sha256=expected,
            received_bytes=0, part_path=part_path)
        _save_session(session)
        return {"upload_id": upload_id, "accept_bytes": True,
                "chunk_bytes": RU.CHUNK_BYTES, "received_bytes": 0,
                "total_bytes": total_bytes}
    except RU.ResumableUploadError as error:
        raise HTTPException(status_code=error.status_code, detail=error.code) from error
    except SkeletonError as error:
        _raise_http(error)


@router.get("/workspaces/{workspace_id}/artifact/uploads/{upload_id}")
def upload_session_status(
    workspace_id: str,
    upload_id: str,
    authorization: str | None = Header(default=None),
    session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, Any]:
    """续传的支点：客户端断线重连后靠它问「我传到哪了」（AC-UP-002 恢复 100%）。"""
    try:
        _require_enabled()
        with _store() as connection:
            _authorize(connection, workspace_id, authorization, session_cookie)
        session = _load_session(workspace_id, upload_id)
        return {"upload_id": upload_id, "received_bytes": session.received_bytes,
                "total_bytes": session.total_bytes, "chunk_bytes": RU.CHUNK_BYTES}
    except RU.ResumableUploadError as error:
        raise HTTPException(status_code=error.status_code, detail=error.code) from error
    except SkeletonError as error:
        _raise_http(error)


@router.patch("/workspaces/{workspace_id}/artifact/uploads/{upload_id}")
async def append_upload_chunk(
    workspace_id: str,
    upload_id: str,
    request: Request,
    authorization: str | None = Header(default=None),
    upload_offset: str | None = Header(default=None, alias="Upload-Offset"),
    chunk_sha256: str | None = Header(default=None, alias="Chunk-SHA256"),
    session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, Any]:
    """收一片。**先验后写**——被拒的片一个字节都不落盘（AC-UP-002 篡改漏检=0）。"""
    try:
        _require_enabled()
        with _store() as connection:
            _authorize(connection, workspace_id, authorization, session_cookie)
        session = _load_session(workspace_id, upload_id)
        try:
            offset = int(upload_offset or "")
        except ValueError as exc:
            raise RU.ResumableUploadError(422, "invalid_upload_offset") from exc
        body = bytearray()
        async for block in request.stream():
            body.extend(block)
            if len(body) > RU.MAX_CHUNK_BYTES:
                raise RU.ResumableUploadError(413, "chunk_too_large")
        RU.validate_chunk(session=session, offset=offset, payload=bytes(body),
                          chunk_sha256=chunk_sha256 or "")
        received = RU.append_chunk(session, bytes(body))
        _save_session(replace(session, received_bytes=received))
        return {"upload_id": upload_id, "received_bytes": received,
                "total_bytes": session.total_bytes}
    except RU.ResumableUploadError as error:
        raise HTTPException(status_code=error.status_code, detail=error.code) from error
    except SkeletonError as error:
        _raise_http(error)


@router.post("/workspaces/{workspace_id}/artifact/uploads/{upload_id}/complete")
def complete_upload_session(
    workspace_id: str,
    upload_id: str,
    authorization: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, Any]:
    """完成会话：整体复核后交给**与单次上传同一条**持久化链。

    这里对暂存文件**整体重算摘要**，尽管每片都已验过。逐片校验管不到
    「片本身没坏但顺序被换 / 有片被重放 / 暂存文件在传输之外被改动」——
    整体摘要管得到。两道都要，少一道就有一类篡改漏网（AC-UP-002 篡改漏检=0）。
    """
    try:
        _require_enabled()
        with _store() as connection:
            _authorize(connection, workspace_id, authorization, session_cookie)
        session = _load_session(workspace_id, upload_id)
        RU.verify_complete(session, RU.file_sha256(session.part_path))

        try:
            key_hash = idempotency_key_hash(idempotency_key)
        except ConsistencyStateError as exc:
            raise SkeletonError(422, "invalid_idempotency_key") from exc
        try:
            object_store = configured_write_store(_state_root())
            object_store.ensure_ready()
        except (ObjectStorageConfigurationError, ObjectStorageUnavailableError, OSError) as exc:
            raise SkeletonError(503, "walking_skeleton_storage_unavailable") from exc

        operation_id = _new_operation_id()
        artifact_id = _new_artifact_id()
        version_number = 1
        version_id = artifact_version_id(artifact_id, version_number)
        payload = _persist_completed_upload(
            workspace_id=workspace_id, request_path=session.part_path,
            size=session.total_bytes, sha256=session.expected_sha256,
            filename=session.original_name, media_type=session.media_type,
            idempotency_key=idempotency_key, key_hash=key_hash,
            object_store=object_store, operation_id=operation_id,
            artifact_id=artifact_id, version_number=version_number,
            version_id=version_id,
        )
        # 会话已经兑现成 artifact，sidecar 留着只会让配额把它的字节重复计一遍。
        _upload_sidecar(upload_id).unlink(missing_ok=True)
        return payload
    except RU.ResumableUploadError as error:
        raise HTTPException(status_code=error.status_code, detail=error.code) from error
    except SkeletonError as error:
        _raise_http(error)


@router.put("/workspaces/{workspace_id}/artifact")
async def upload_artifact(
    workspace_id: str,
    request: Request,
    authorization: str | None = Header(default=None),
    x_kmfa_filename: str | None = Header(default=None),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
    ),
    session_cookie: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
) -> dict[str, Any]:
    try:
        _require_enabled()
        return await _store_artifact(
            workspace_id,
            authorization,
            session_cookie,
            x_kmfa_filename,
            idempotency_key,
            request,
        )
    except SkeletonError as error:
        _raise_http(error)
    except OSError as error:
        raise HTTPException(
            status_code=503,
            detail="walking_skeleton_storage_unavailable",
        ) from error


@router.post("/workspaces/{workspace_id}/artifact/download")
def download_artifact(
    workspace_id: str,
    authorization: str | None = Header(default=None),
    session_cookie: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
) -> FileResponse:
    try:
        _require_enabled()
        path, artifact, temporary = _artifact_for_download(
            workspace_id,
            authorization,
            session_cookie,
        )
    except SkeletonError as error:
        _raise_http(error)
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=artifact["original_name"],
        content_disposition_type="attachment",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "X-KMFA-Artifact-SHA256": artifact["sha256"],
            "X-KMFA-Artifact-Mode": "attachment-only",
        },
        background=(
            BackgroundTask(path.unlink, missing_ok=True) if temporary else None
        ),
    )


@router.get("/workspaces/{workspace_id}/audit-events")
def get_audit_events(
    workspace_id: str,
    authorization: str | None = Header(default=None),
    session_cookie: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
) -> dict[str, Any]:
    try:
        _require_enabled()
        return _audit_events(workspace_id, authorization, session_cookie)
    except SkeletonError as error:
        _raise_http(error)
