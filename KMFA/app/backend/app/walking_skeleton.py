"""S03/P3.4 walking skeleton with S04/P4.1-P4.2 recovery hardening.

This is intentionally a narrow, replaceable adapter. Structured workspace
state lives in SQLite while artifact bytes live outside the database in a
private filesystem root. Both must be mounted on the same durable deployment
volume for this early skeleton. P4.1 adds 128-bit workspace identifiers,
256-bit workspace secrets, irreversible verifiers and one-hour session
exchange while accepting existing S03 identifiers. P4.2 adds a strict,
minimal `.kmfa-recovery` capability file plus atomic secret rotation. S04/P4.3
onward still owns session revocation, whole-chain secret hygiene, object
storage, backup/restore, abuse controls, scanning and multi-file lifecycle
semantics.

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
import sqlite3
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

API_PREFIX = "/public-api/walking-skeleton/v1"
TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024
MAX_ARTIFACTS = 1
ACCESS_TOKEN_TTL = timedelta(hours=1)
SCHEMA_VERSION = 1
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


def _open_store() -> sqlite3.Connection:
    _ensure_private_directories()
    connection = sqlite3.connect(
        str(_db_path()),
        isolation_level=None,
        timeout=5,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=FULL")
    connection.execute("PRAGMA busy_timeout=5000")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS workspaces (
          workspace_id TEXT PRIMARY KEY,
          recovery_hash TEXT NOT NULL UNIQUE,
          project_name TEXT NOT NULL,
          progress INTEGER NOT NULL CHECK(progress BETWEEN 0 AND 100),
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS access_tokens (
          token_hash TEXT PRIMARY KEY,
          workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
          created_at TEXT NOT NULL,
          expires_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS access_tokens_workspace
          ON access_tokens(workspace_id);
        CREATE TABLE IF NOT EXISTS artifacts (
          artifact_id TEXT PRIMARY KEY,
          workspace_id TEXT NOT NULL UNIQUE REFERENCES workspaces(workspace_id),
          object_name TEXT NOT NULL UNIQUE,
          original_name TEXT NOT NULL,
          reported_media_type TEXT NOT NULL,
          size_bytes INTEGER NOT NULL CHECK(size_bytes >= 0),
          sha256 TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_events (
          seq INTEGER PRIMARY KEY AUTOINCREMENT,
          event_id TEXT NOT NULL UNIQUE,
          workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id),
          action TEXT NOT NULL,
          result_status TEXT NOT NULL,
          artifact_sha256 TEXT,
          created_at TEXT NOT NULL
        );
        CREATE TRIGGER IF NOT EXISTS walking_audit_no_update
          BEFORE UPDATE ON audit_events BEGIN
            SELECT RAISE(ABORT, 'walking-skeleton audit is append-only');
          END;
        CREATE TRIGGER IF NOT EXISTS walking_audit_no_delete
          BEFORE DELETE ON audit_events BEGIN
            SELECT RAISE(ABORT, 'walking-skeleton audit is append-only');
          END;
        """
    )
    connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
    _db_path().chmod(0o600)
    return connection


@contextmanager
def _store():
    connection = None
    try:
        connection = _open_store()
        yield connection
    except SkeletonError:
        raise
    except (OSError, sqlite3.Error) as exc:
        raise SkeletonError(503, "walking_skeleton_storage_unavailable") from exc
    finally:
        if connection is not None:
            connection.close()


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
    connection: sqlite3.Connection,
    workspace_id: str,
    action: str,
    *,
    result_status: str = "ok",
    artifact_sha256: str | None = None,
) -> None:
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
    connection: sqlite3.Connection,
    workspace_id: str,
) -> tuple[str, str]:
    token = _new_access_token()
    created = _utc_now()
    expires = created + ACCESS_TOKEN_TTL
    connection.execute(
        """
        INSERT INTO access_tokens(token_hash, workspace_id, created_at, expires_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            _hash_capability(token),
            workspace_id,
            _timestamp(created),
            _timestamp(expires),
        ),
    )
    return token, _timestamp(expires)


def _artifact_payload(row: sqlite3.Row | None) -> dict[str, Any] | None:
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
    connection: sqlite3.Connection,
    workspace_id: str,
) -> dict[str, Any]:
    workspace = connection.execute(
        """
        SELECT workspace_id, project_name, progress, created_at, updated_at
        FROM workspaces WHERE workspace_id = ?
        """,
        (workspace_id,),
    ).fetchone()
    if workspace is None:
        raise SkeletonError(404, "workspace_not_found")
    artifact = connection.execute(
        """
        SELECT artifact_id, original_name, size_bytes, sha256, created_at
        FROM artifacts WHERE workspace_id = ?
        """,
        (workspace_id,),
    ).fetchone()
    return {
        "workspace_id": workspace["workspace_id"],
        "project_name": workspace["project_name"],
        "progress": workspace["progress"],
        "created_at": workspace["created_at"],
        "updated_at": workspace["updated_at"],
        "artifact": _artifact_payload(artifact),
        "stage_status": "early-skeleton-not-ga",
    }


def _authorization_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise SkeletonError(404, "workspace_not_found")
    token = authorization.removeprefix("Bearer ").strip()
    if not ACCESS_TOKEN_RE.fullmatch(token):
        raise SkeletonError(404, "workspace_not_found")
    return token


def _authorize(
    connection: sqlite3.Connection,
    workspace_id: str,
    authorization: str | None,
) -> None:
    if not WORKSPACE_ID_RE.fullmatch(workspace_id):
        raise SkeletonError(404, "workspace_not_found")
    token = _authorization_token(authorization)
    row = connection.execute(
        """
        SELECT 1 FROM access_tokens
        WHERE token_hash = ? AND workspace_id = ? AND expires_at > ?
        """,
        (_hash_capability(token), workspace_id, _timestamp()),
    ).fetchone()
    if row is None:
        raise SkeletonError(404, "workspace_not_found")


def _workspace_secret_matches(
    connection: sqlite3.Connection,
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
        "SELECT recovery_hash FROM workspaces WHERE workspace_id = ?",
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
    connection: sqlite3.Connection,
    workspace_id: str,
    *,
    audit_action: str,
) -> tuple[str, str]:
    access_token, expires_at = _issue_access_token(connection, workspace_id)
    _append_audit(connection, workspace_id, audit_action)
    return access_token, expires_at


def _workspace_session_payload(
    connection: sqlite3.Connection,
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


def _create_workspace(project_name: str) -> dict[str, Any]:
    cleaned_name = _clean_project_name(project_name)
    recovery_code = _new_recovery_code()
    with _store() as connection:
        for _ in range(5):
            workspace_id = _new_workspace_id()
            try:
                connection.execute("BEGIN IMMEDIATE")
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
            except sqlite3.IntegrityError:
                connection.execute("ROLLBACK")
        raise SkeletonError(503, "workspace_identity_unavailable")


def _recover_workspace(recovery_code: str) -> dict[str, Any]:
    if not RECOVERY_CODE_RE.fullmatch(recovery_code):
        raise SkeletonError(404, "recovery_not_found")
    with _store() as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            workspace = connection.execute(
                "SELECT workspace_id FROM workspaces WHERE recovery_hash = ?",
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
) -> bytes:
    with _store() as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            _authorize(connection, workspace_id, authorization)
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
) -> dict[str, Any]:
    with _store() as connection:
        for _ in range(5):
            workspace_secret = _new_recovery_code()
            try:
                connection.execute("BEGIN IMMEDIATE")
                _authorize(connection, workspace_id, authorization)
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
                _append_audit(connection, workspace_id, "workspace_secret_rotated")
                connection.execute("COMMIT")
                return {
                    "workspace_id": workspace_id,
                    "workspace_secret": workspace_secret,
                    "workspace_secret_shown_once": True,
                    "previous_workspace_secret_revoked": True,
                    "existing_sessions_revoked": False,
                }
            except sqlite3.IntegrityError:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
    raise SkeletonError(503, "workspace_identity_unavailable")


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


def _get_workspace(workspace_id: str, authorization: str | None) -> dict[str, Any]:
    with _store() as connection:
        _authorize(connection, workspace_id, authorization)
        return _workspace_payload(connection, workspace_id)


def _update_workspace(
    workspace_id: str,
    authorization: str | None,
    request: UpdateWorkspaceRequest,
) -> dict[str, Any]:
    if request.project_name is None and request.progress is None:
        raise SkeletonError(422, "workspace_update_required")
    project_name = (
        _clean_project_name(request.project_name)
        if request.project_name is not None
        else None
    )
    with _store() as connection:
        _authorize(connection, workspace_id, authorization)
        current = connection.execute(
            "SELECT project_name, progress FROM workspaces WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()
        if current is None:
            raise SkeletonError(404, "workspace_not_found")
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """
            UPDATE workspaces SET project_name = ?, progress = ?, updated_at = ?
            WHERE workspace_id = ?
            """,
            (
                project_name if project_name is not None else current["project_name"],
                request.progress
                if request.progress is not None
                else current["progress"],
                _timestamp(),
                workspace_id,
            ),
        )
        _append_audit(connection, workspace_id, "workspace_saved")
        connection.execute("COMMIT")
        return _workspace_payload(connection, workspace_id)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


async def _store_artifact(
    workspace_id: str,
    authorization: str | None,
    filename_header: str | None,
    request: Request,
) -> dict[str, Any]:
    filename = _clean_filename(filename_header)
    content_length = request.headers.get("content-length", "").strip()
    if content_length:
        try:
            if int(content_length) > MAX_ARTIFACT_BYTES:
                raise SkeletonError(413, "artifact_too_large")
        except ValueError as exc:
            raise SkeletonError(400, "invalid_content_length") from exc

    with _store() as connection:
        _authorize(connection, workspace_id, authorization)
        if connection.execute(
            "SELECT 1 FROM artifacts WHERE workspace_id = ?", (workspace_id,)
        ).fetchone():
            raise SkeletonError(409, "artifact_limit_reached")

    artifact_id = _new_artifact_id()
    object_name = f"{secrets.token_urlsafe(24)}.blob"
    temp_path = _tmp_dir() / f"{object_name}.part"
    object_path = _objects_dir() / object_name
    digest = hashlib.sha256()
    size = 0
    object_registered = False
    descriptor = os.open(temp_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as output:
            async for chunk in request.stream():
                if not chunk:
                    continue
                size += len(chunk)
                if size > MAX_ARTIFACT_BYTES:
                    raise SkeletonError(413, "artifact_too_large")
                digest.update(chunk)
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp_path, object_path)
        object_path.chmod(0o600)
        _fsync_directory(_objects_dir())

        with _store() as connection:
            _authorize(connection, workspace_id, authorization)
            connection.execute("BEGIN IMMEDIATE")
            try:
                now = _timestamp()
                connection.execute(
                    """
                    INSERT INTO artifacts(
                      artifact_id, workspace_id, object_name, original_name,
                      reported_media_type, size_bytes, sha256, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        artifact_id,
                        workspace_id,
                        object_name,
                        filename,
                        _clean_media_type(request.headers.get("content-type")),
                        size,
                        digest.hexdigest(),
                        now,
                    ),
                )
                connection.execute(
                    "UPDATE workspaces SET updated_at = ? WHERE workspace_id = ?",
                    (now, workspace_id),
                )
                _append_audit(
                    connection,
                    workspace_id,
                    "artifact_uploaded",
                    artifact_sha256=digest.hexdigest(),
                )
                payload = _workspace_payload(connection, workspace_id)
                connection.execute("COMMIT")
                object_registered = True
            except sqlite3.IntegrityError as exc:
                connection.execute("ROLLBACK")
                raise SkeletonError(409, "artifact_limit_reached") from exc
            except Exception:
                connection.execute("ROLLBACK")
                raise
            return payload
    except Exception:
        temp_path.unlink(missing_ok=True)
        if not object_registered:
            object_path.unlink(missing_ok=True)
        raise


def _artifact_for_download(
    workspace_id: str,
    authorization: str | None,
) -> tuple[Path, dict[str, Any]]:
    with _store() as connection:
        _authorize(connection, workspace_id, authorization)
        artifact = connection.execute(
            """
            SELECT artifact_id, object_name, original_name, size_bytes, sha256, created_at
            FROM artifacts WHERE workspace_id = ?
            """,
            (workspace_id,),
        ).fetchone()
        if artifact is None:
            raise SkeletonError(404, "artifact_not_found")
        path = (_objects_dir() / artifact["object_name"]).resolve()
        if path.parent != _objects_dir().resolve() or not path.is_file():
            _append_audit(
                connection, workspace_id, "artifact_download", result_status="missing"
            )
            raise SkeletonError(503, "artifact_unavailable")
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                size += len(chunk)
                digest.update(chunk)
        if size != artifact["size_bytes"] or digest.hexdigest() != artifact["sha256"]:
            _append_audit(
                connection,
                workspace_id,
                "artifact_download",
                result_status="integrity_failed",
            )
            raise SkeletonError(503, "artifact_integrity_failed")
        _append_audit(
            connection,
            workspace_id,
            "artifact_download",
            artifact_sha256=artifact["sha256"],
        )
        return path, dict(artifact)


def _audit_events(workspace_id: str, authorization: str | None) -> dict[str, Any]:
    with _store() as connection:
        _authorize(connection, workspace_id, authorization)
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
        with _store() as connection:
            schema_version = connection.execute("PRAGMA user_version").fetchone()[0]
            connection.execute("SELECT 1").fetchone()
    except SkeletonError as error:
        _raise_http(error)
    return {
        "enabled": True,
        "mode": "early-skeleton",
        "healthy": True,
        "schema_version": schema_version,
        "structured_store": "sqlite-durable-volume-adapter",
        "artifact_store": "private-filesystem-volume-adapter",
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
        "limits": {
            "max_artifacts": MAX_ARTIFACTS,
            "max_bytes": MAX_ARTIFACT_BYTES,
            "file_types": "any-stored-attachment-only",
        },
        "stage_status": "early-skeleton-not-ga",
        "hardening_pending": [
            "durable-database-service",
            "s3-compatible-object-store",
            "backup-restore-drill",
            "abuse-and-malware-controls",
            "multi-file-lifecycle-and-explicit-deletion",
        ],
    }


@router.post("/workspaces", status_code=201)
def create_workspace(request: CreateWorkspaceRequest) -> dict[str, Any]:
    try:
        _require_enabled()
        return _create_workspace(request.project_name)
    except SkeletonError as error:
        _raise_http(error)


@router.post("/recoveries")
def recover_workspace(request: RecoverWorkspaceRequest) -> dict[str, Any]:
    try:
        _require_enabled()
        return _recover_workspace(request.recovery_code)
    except SkeletonError as error:
        _raise_http(error)


@router.post("/sessions")
def exchange_workspace_session(
    request: ExchangeWorkspaceSessionRequest,
) -> dict[str, Any]:
    try:
        _require_enabled()
        return _exchange_workspace_session(
            request.workspace_id,
            request.workspace_secret,
        )
    except SkeletonError as error:
        _raise_http(error)


@router.post("/recovery-files/import")
async def import_recovery_file(request: Request) -> dict[str, Any]:
    try:
        _require_enabled()
        payload = await _read_recovery_file_request(request)
        return _import_recovery_file(payload)
    except SkeletonError as error:
        _raise_http(error)


@router.get("/workspaces/{workspace_id}")
def get_workspace(
    workspace_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    try:
        _require_enabled()
        return _get_workspace(workspace_id, authorization)
    except SkeletonError as error:
        _raise_http(error)


@router.post("/workspaces/{workspace_id}/recovery-file")
def export_recovery_file(
    workspace_id: str,
    request: ExportRecoveryFileRequest,
    authorization: str | None = Header(default=None),
) -> Response:
    try:
        _require_enabled()
        payload = _export_recovery_file(
            workspace_id,
            authorization,
            request.workspace_secret,
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
            "Content-Disposition": 'attachment; filename="kmfa-workspace.kmfa-recovery"',
        },
    )


@router.post("/workspaces/{workspace_id}/recovery-secret/rotate")
def rotate_workspace_secret(
    workspace_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    try:
        _require_enabled()
        return _rotate_workspace_secret(workspace_id, authorization)
    except SkeletonError as error:
        _raise_http(error)


@router.patch("/workspaces/{workspace_id}")
def update_workspace(
    workspace_id: str,
    request: UpdateWorkspaceRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    try:
        _require_enabled()
        return _update_workspace(workspace_id, authorization, request)
    except SkeletonError as error:
        _raise_http(error)


@router.put("/workspaces/{workspace_id}/artifact")
async def upload_artifact(
    workspace_id: str,
    request: Request,
    authorization: str | None = Header(default=None),
    x_kmfa_filename: str | None = Header(default=None),
) -> dict[str, Any]:
    try:
        _require_enabled()
        return await _store_artifact(
            workspace_id,
            authorization,
            x_kmfa_filename,
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
) -> FileResponse:
    try:
        _require_enabled()
        path, artifact = _artifact_for_download(workspace_id, authorization)
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
    )


@router.get("/workspaces/{workspace_id}/audit-events")
def get_audit_events(
    workspace_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    try:
        _require_enabled()
        return _audit_events(workspace_id, authorization)
    except SkeletonError as error:
        _raise_http(error)
