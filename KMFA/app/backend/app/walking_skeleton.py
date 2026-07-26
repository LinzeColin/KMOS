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
P6.1 adds a flag-guarded offset protocol whose durable session identity reuses
the S05 upload intent. Incomplete chunks stay in private bounded staging and
the completed immutable original still passes through the same object/outbox
state machine. S06/P6.2 adds quarantine-first assessment and sends verified
originals to a credential-minimal private scanner; scan timeout/error is never
clean and no preview is created. S06/P6.3 adds immutable revisions, explicit
parent/source lineage and an opt-in worker-generated bounded text preview;
originals are never overwritten and the web process never parses them. Later
S06 phases own scalable multi-file lifecycle semantics.

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
from pathlib import Path
from typing import Any, Callable, Literal
from urllib.parse import unquote

from fastapi import APIRouter, Cookie, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask
from starlette.requests import ClientDisconnect

from .anti_abuse import public_policy_contract
from .artifact_lineage import (
    MAX_TOTAL_ARTIFACT_BYTES,
    SUPPORTED_DETECTED_MEDIA_TYPES,
    ArtifactLineageError,
    ArtifactLineageRepository,
    derivation_enabled,
    public_derivation_contract,
)
from .consistency_state import (
    IDEMPOTENCY_KEY_RE,
    ConsistencyConflictError,
    ConsistencyRepository,
    ConsistencyStateError,
    UploadIntent,
    idempotency_key_hash,
    upload_request_fingerprint,
)
from .file_security import (
    FileSecurityError,
    FileSecurityRepository,
    FileSecurityStateConflict,
    artifact_security_payload,
    file_security_enabled,
    public_file_security_contract,
    require_download_allowed,
    run_security_scan_once,
)
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
from .resumable_upload import (
    UPLOAD_SESSION_ID_RE,
    ResumableStorageError,
    assemble_upload,
    cleanup_chunks,
    discard_incomplete,
    inspect_upload,
    is_resumable_staged_name,
    resumable_staged_name,
    store_verified_chunk,
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
RESUMABLE_UPLOAD_ENABLED_ENV = "KMFA_RESUMABLE_UPLOAD_ENABLED"
SINGLE_FILE_DOWNLOAD_ENABLED_ENV = "KMFA_SINGLE_FILE_DOWNLOAD_ENABLED"
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024
MAX_RESUMABLE_ARTIFACT_BYTES = 64 * 1024 * 1024
MAX_UPLOAD_CHUNK_BYTES = 4 * 1024 * 1024
MAX_RESUMABLE_SESSIONS_PER_WORKSPACE = 16
MAX_ARTIFACTS = 1
MAX_ARTIFACT_VERSIONS = 32
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
MEDIA_TYPE_RE = re.compile(
    r"^[a-z0-9][a-z0-9!#$&^_.+-]{0,126}/"
    r"[a-z0-9][a-z0-9!#$&^_.+-]{0,126}$"
)

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


class CreateUploadSessionRequest(BaseModel):
    original_name: str = Field(min_length=1, max_length=255)
    reported_media_type: str = Field(
        default="application/octet-stream",
        min_length=1,
        max_length=200,
    )
    size_bytes: int = Field(ge=0)
    sha256: str = Field(min_length=64, max_length=64)


class DownloadAssetRequest(BaseModel):
    kind: Literal["original", "derivative"]
    asset_id: str = Field(min_length=1, max_length=200)


class SkeletonError(RuntimeError):
    def __init__(
        self,
        status_code: int,
        code: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(code)
        self.status_code = status_code
        self.code = code
        self.headers = headers or {}


def walking_skeleton_enabled() -> bool:
    """Only explicit true values enable this pre-GA capability."""

    return (
        os.environ.get("KMFA_WALKING_SKELETON_ENABLED", "0").strip().lower()
        in TRUE_VALUES
    )


def resumable_upload_enabled() -> bool:
    """Only an explicit true value enables the P6.1 protocol."""

    return (
        os.environ.get(RESUMABLE_UPLOAD_ENABLED_ENV, "0").strip().lower()
        in TRUE_VALUES
    )


def single_file_download_enabled() -> bool:
    """Only an explicit true value enables the P7.1 exact selector."""

    return (
        os.environ.get(SINGLE_FILE_DOWNLOAD_ENABLED_ENV, "0")
        .strip()
        .lower()
        in TRUE_VALUES
    )


def public_single_file_download_contract() -> dict[str, Any]:
    return {
        "enabled": single_file_download_enabled(),
        "selector_transport": "authorized-json-body",
        "asset_kinds": ["original", "derivative"],
        "content_disposition": "attachment-only",
        "legacy_latest_original_fallback": True,
        "public_snapshot_access": "deferred-to-s08",
    }


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
          COALESCE((SELECT SUM(size_bytes) FROM artifact_versions), 0)
          +
          COALESCE((SELECT SUM(size_bytes) FROM artifact_derivatives), 0)
          +
          COALESCE((
            SELECT SUM(co.size_bytes)
            FROM consistency_operations co
            WHERE co.operation_kind = 'upload'
              AND co.size_bytes IS NOT NULL
              AND NOT (
                co.state = 'isolated'
                AND co.last_error_code = 'resumable_upload_cancelled'
                AND co.staged_object_name LIKE ?
              )
              AND NOT EXISTS (
                SELECT 1
                FROM artifact_versions av
                WHERE av.artifact_version_id = co.artifact_version_id
              )
          ), 0) AS total_bytes
        """,
        ("resumable-%",),
    ).fetchone()
    return int(row["total_bytes"])


def _artifact_version_slots_used(
    connection: StructuredStoreConnection,
    workspace_id: str,
) -> int:
    artifact = connection.execute(
        """
        SELECT artifact_id
        FROM artifacts
        WHERE workspace_id = ?
        """,
        (workspace_id,),
    ).fetchone()
    if artifact is None:
        return 0
    row = connection.execute(
        """
        SELECT MAX(version_number) AS max_version
        FROM (
          SELECT av.version_number
          FROM artifact_versions av
          WHERE av.artifact_id = ?
          UNION ALL
          SELECT operation.artifact_version_number
          FROM consistency_operations operation
          WHERE operation.operation_kind = 'upload'
            AND operation.artifact_id = ?
            AND operation.artifact_version_number IS NOT NULL
        ) versions
        """,
        (artifact["artifact_id"], artifact["artifact_id"]),
    ).fetchone()
    return int(row["max_version"] or 0)


def _next_artifact_version_identity(
    connection: StructuredStoreConnection,
    workspace_id: str,
) -> tuple[str, int]:
    # A harmless update takes the workspace row lock in PostgreSQL and the
    # write transaction in SQLite. Only one request may reserve the next
    # immutable version number at a time.
    locked = connection.execute(
        """
        UPDATE workspaces
        SET updated_at = updated_at
        WHERE workspace_id = ?
        """,
        (workspace_id,),
    )
    if locked.rowcount != 1:
        raise SkeletonError(404, "workspace_not_found")
    artifact = connection.execute(
        """
        SELECT artifact_id
        FROM artifacts
        WHERE workspace_id = ?
        """,
        (workspace_id,),
    ).fetchone()
    if artifact is None:
        return _new_artifact_id(), 1
    used = _artifact_version_slots_used(connection, workspace_id)
    if used >= MAX_ARTIFACT_VERSIONS:
        raise SkeletonError(409, "artifact_version_limit_reached")
    return str(artifact["artifact_id"]), used + 1


def _require_enabled() -> None:
    if not walking_skeleton_enabled():
        raise SkeletonError(404, "walking_skeleton_disabled")


def _raise_http(error: SkeletonError) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail=error.code,
        headers=error.headers,
    ) from error


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
    return _clean_plain_filename(decoded)


def _clean_plain_filename(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value).strip()
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
    media_type = (
        value or "application/octet-stream"
    ).split(";", 1)[0].strip().lower()
    if MEDIA_TYPE_RE.fullmatch(media_type) is None:
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


def _downloadable_payloads(
    connection: StructuredStoreConnection,
    workspace_id: str,
) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for row in StructuredRepository(connection).downloadable_assets(
        workspace_id
    ):
        kind = str(row["asset_kind"])
        source_artifact_version_id = str(
            row["source_artifact_version_id"]
        )
        security = artifact_security_payload(
            connection,
            artifact_version_id=source_artifact_version_id,
        )
        if kind == "original":
            source = {
                "kind": "upload",
                "artifact_version_id": source_artifact_version_id,
                "operation_id": (
                    str(row["source_operation_id"])
                    if row["source_operation_id"] is not None
                    else None
                ),
            }
            download_allowed = bool(security["download_allowed"])
        else:
            source = {
                "kind": "processor",
                "artifact_version_id": source_artifact_version_id,
                "processor": {
                    "name": str(row["processor_name"]),
                    "version": str(row["processor_version"]),
                },
                "generation_number": int(row["generation_number"]),
            }
            download_allowed = security["state"] == "clean"
        payloads.append(
            {
                "kind": kind,
                "id": str(row["asset_id"]),
                "name": str(row["original_name"]),
                "media_type": _clean_media_type(str(row["media_type"])),
                "size_bytes": int(row["size_bytes"]),
                "sha256": str(row["sha256"]),
                "created_at": str(row["created_at"]),
                "version_number": int(row["version_number"]),
                "download_allowed": download_allowed,
                "download_mode": "attachment-only",
                "source": source,
            }
        )
    return payloads


def _artifact_payload(
    connection: StructuredStoreConnection,
    row: Any | None,
    workspace_id: str,
) -> dict[str, Any] | None:
    if row is None:
        return None
    security = dict(
        artifact_security_payload(
            connection,
            artifact_version_id=str(row["artifact_version_id"]),
        )
    )
    processing_allowed = (
        derivation_enabled()
        and security["state"] == "clean"
        and security["detected_media_type"]
        in SUPPORTED_DETECTED_MEDIA_TYPES
    )
    derivative = (
        ArtifactLineageRepository(connection).latest_derivative(
            str(row["artifact_version_id"])
        )
        if processing_allowed
        else None
    )
    preview_allowed = derivative is not None
    security["processing_allowed"] = processing_allowed
    security["preview_allowed"] = preview_allowed
    lineage = connection.execute(
        """
        SELECT
          parent_artifact_version_id, relation_kind, source_operation_id
        FROM artifact_version_lineage
        WHERE artifact_version_id = ?
        """,
        (row["artifact_version_id"],),
    ).fetchone()
    version_count = int(
        connection.execute(
            """
            SELECT COUNT(*) AS count_value
            FROM artifact_versions
            WHERE artifact_id = ?
            """,
            (row["artifact_id"],),
        ).fetchone()["count_value"]
    )
    preview = (
        {
            "derivative_id": str(derivative["derivative_id"]),
            "kind": str(derivative["output_kind"]),
            "generation_number": int(derivative["generation_number"]),
            "media_type": str(derivative["media_type"]),
            "size_bytes": int(derivative["size_bytes"]),
            "sha256": str(derivative["sha256"]),
            "processor": {
                "name": str(derivative["processor_name"]),
                "version": str(derivative["processor_version"]),
            },
            "created_at": str(derivative["created_at"]),
        }
        if derivative is not None
        else None
    )
    payload = {
        "artifact_id": row["artifact_id"],
        "artifact_version_id": row["artifact_version_id"],
        "version_number": int(row["version_number"]),
        "version_count": version_count,
        "parent_artifact_version_id": (
            str(lineage["parent_artifact_version_id"])
            if lineage is not None
            and lineage["parent_artifact_version_id"] is not None
            else None
        ),
        "lineage_relation": (
            str(lineage["relation_kind"]) if lineage is not None else None
        ),
        "name": row["original_name"],
        "media_type": _clean_media_type(str(row["reported_media_type"])),
        "size_bytes": row["size_bytes"],
        "sha256": row["sha256"],
        "created_at": row["created_at"],
        "source": {
            "kind": "upload",
            "artifact_version_id": str(row["artifact_version_id"]),
            "operation_id": (
                str(lineage["source_operation_id"])
                if lineage is not None
                and lineage["source_operation_id"] is not None
                else None
            ),
        },
        "download_mode": "attachment-only",
        "download_allowed": security["download_allowed"],
        "preview_allowed": preview_allowed,
        "preview": preview,
        "security": security,
    }
    if single_file_download_enabled():
        payload["downloadables"] = _downloadable_payloads(
            connection,
            workspace_id,
        )
    return payload


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
        "artifact": _artifact_payload(connection, artifact, workspace_id),
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
            if file_security_enabled():
                try:
                    run_security_scan_once(
                        state_root=_state_root(),
                        artifact_version_id=str(
                            operation["artifact_version_id"]
                        ),
                    )
                except FileSecurityError:
                    # The immutable upload is already converged. Assessment
                    # remains durable pending/error and must not be rewritten
                    # as clean merely to make this response succeed.
                    pass
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
                            projected_version = connection.execute(
                                """
                                SELECT artifact_version_id
                                FROM artifact_versions
                                WHERE artifact_version_id = ?
                                """,
                                (operation["artifact_version_id"],),
                            ).fetchone()
                            if (
                                projected_version is None
                                and _artifact_capacity_usage(connection)
                                > MAX_TOTAL_ARTIFACT_BYTES
                            ):
                                raise SkeletonError(
                                    429, "artifact_capacity_reached"
                                )
                            created_at = str(operation["created_at"])
                            uploaded_version_id = (
                                repository.ensure_uploaded_artifact(
                                    workspace_id=str(
                                        operation["workspace_id"]
                                    ),
                                    artifact_id=str(
                                        operation["artifact_id"]
                                    ),
                                    version_number=int(
                                        operation[
                                            "artifact_version_number"
                                        ]
                                    ),
                                    storage_backend=str(
                                        operation["storage_backend"]
                                    ),
                                    storage_key=str(
                                        operation["storage_key"]
                                    ),
                                    original_name=str(
                                        operation["original_name"]
                                    ),
                                    reported_media_type=str(
                                        operation["reported_media_type"]
                                    ),
                                    size_bytes=int(operation["size_bytes"]),
                                    sha256=str(
                                        operation["content_sha256"]
                                    ),
                                    created_at=created_at,
                                )
                            )
                            ArtifactLineageRepository(
                                connection
                            ).ensure_version_lineage(
                                artifact_version_id=uploaded_version_id,
                                artifact_id=str(operation["artifact_id"]),
                                version_number=int(
                                    operation["artifact_version_number"]
                                ),
                                source_operation_id=operation_id,
                                created_at=created_at,
                            )
                            if file_security_enabled():
                                FileSecurityRepository(
                                    connection
                                ).ensure_quarantined(
                                    artifact_version_id=uploaded_version_id,
                                    operation_id=operation_id,
                                    normalized_name=str(
                                        operation["original_name"]
                                    ),
                                    reported_media_type=str(
                                        operation["reported_media_type"]
                                    ),
                                    source_size_bytes=int(
                                        operation["size_bytes"]
                                    ),
                                    source_sha256=str(
                                        operation["content_sha256"]
                                    ),
                                    storage_backend=str(
                                        operation["storage_backend"]
                                    ),
                                    storage_key=str(
                                        operation["storage_key"]
                                    ),
                                    timestamp=created_at,
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
        if existing_operation is None:
            if (
                _artifact_version_slots_used(connection, workspace_id)
                >= MAX_ARTIFACT_VERSIONS
            ):
                raise SkeletonError(409, "artifact_version_limit_reached")
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
        fingerprint = upload_request_fingerprint(
            workspace_id=workspace_id,
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
                        if competing_upload is not None:
                            raise SkeletonError(
                                409, "artifact_upload_in_progress"
                            )
                        if (
                            _artifact_capacity_usage(connection) + size
                            > MAX_TOTAL_ARTIFACT_BYTES
                        ):
                            raise SkeletonError(
                                429,
                                "artifact_capacity_reached",
                            )
                        artifact_id, version_number = (
                            _next_artifact_version_identity(
                                connection,
                                workspace_id,
                            )
                        )
                        version_id = artifact_version_id(
                            artifact_id,
                            version_number,
                        )
                        storage_key = object_store.build_storage_key(
                            workspace_id=workspace_id,
                            artifact_id=artifact_id,
                            artifact_version_id=version_id,
                            version_number=version_number,
                            sha256=sha256,
                        )
                        staged_object_name = f"workflow-{operation_id}.part"
                    else:
                        artifact_id = str(durable_replay["artifact_id"])
                        version_id = str(
                            durable_replay["artifact_version_id"]
                        )
                        version_number = int(
                            durable_replay["artifact_version_number"]
                        )
                        storage_key = str(durable_replay["storage_key"])
                        staged_object_name = str(
                            durable_replay["staged_object_name"]
                        )
                    intent = UploadIntent(
                        workspace_id=workspace_id,
                        idempotency_key=idempotency_key,
                        request_fingerprint=fingerprint,
                        artifact_id=artifact_id,
                        artifact_version_id=version_id,
                        storage_backend=object_store.storage_backend,
                        storage_key=storage_key,
                        staged_object_name=staged_object_name,
                        original_name=filename,
                        reported_media_type=media_type,
                        size_bytes=size,
                        content_sha256=sha256,
                        artifact_version_number=version_number,
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


def _require_resumable_upload() -> None:
    _require_enabled()
    if not resumable_upload_enabled():
        raise SkeletonError(404, "resumable_upload_disabled")
    if consistency_state_mode() == CONSISTENCY_PAUSED_MODE:
        raise SkeletonError(503, "consistency_processing_paused")


def _upload_offset_headers(offset: int) -> dict[str, str]:
    return {
        "Upload-Offset": str(offset),
        "Upload-Max-Chunk-Bytes": str(MAX_UPLOAD_CHUNK_BYTES),
        "Cache-Control": "private, no-store",
    }


def _raise_resumable_storage(error: ResumableStorageError) -> None:
    status_by_code = {
        "upload_session_not_found": 404,
        "invalid_upload_offset": 422,
        "upload_chunk_size_invalid": 422,
        "upload_chunk_conflict": 409,
        "upload_offset_conflict": 409,
        "upload_chunk_state_invalid": 409,
        "upload_incomplete": 409,
        "upload_checksum_mismatch": 409,
        "artifact_too_large": 413,
        "resumable_storage_unavailable": 503,
    }
    raise SkeletonError(
        status_by_code.get(error.code, 503),
        error.code,
        headers=(
            _upload_offset_headers(error.offset)
            if error.offset is not None
            else None
        ),
    ) from error


def _resumable_operation(
    workspace_id: str,
    authorization: str | None,
    session_cookie: str | None,
    upload_session_id: str,
) -> dict[str, Any]:
    if UPLOAD_SESSION_ID_RE.fullmatch(upload_session_id) is None:
        raise SkeletonError(404, "upload_session_not_found")
    with _store() as connection:
        _authorize(connection, workspace_id, authorization, session_cookie)
        row = ConsistencyRepository(connection).operation(upload_session_id)
        if (
            row is None
            or str(row["workspace_id"]) != workspace_id
            or str(row["operation_kind"]) != "upload"
            or not is_resumable_staged_name(str(row["staged_object_name"]))
        ):
            raise SkeletonError(404, "upload_session_not_found")
        return dict(row)


def _upload_session_payload(operation: dict[str, Any]) -> dict[str, Any]:
    expected_size = int(operation["size_bytes"])
    state = str(operation["state"])
    if state == "converged":
        offset = expected_size
        chunk_count = 0
        public_state = "completed"
    elif state == "isolated":
        try:
            snapshot = inspect_upload(
                _tmp_dir(),
                str(operation["operation_id"]),
                expected_size=expected_size,
                max_chunk_bytes=MAX_UPLOAD_CHUNK_BYTES,
            )
            offset = snapshot.offset_bytes
            chunk_count = snapshot.chunk_count
        except ResumableStorageError:
            offset = 0
            chunk_count = 0
        public_state = "isolated"
    elif state == "intent_recorded":
        try:
            snapshot = inspect_upload(
                _tmp_dir(),
                str(operation["operation_id"]),
                expected_size=expected_size,
                max_chunk_bytes=MAX_UPLOAD_CHUNK_BYTES,
            )
        except ResumableStorageError as error:
            _raise_resumable_storage(error)
        offset = snapshot.offset_bytes
        chunk_count = snapshot.chunk_count
        public_state = "active"
    else:
        offset = expected_size
        chunk_count = 0
        public_state = "finalizing"
    workspace_id = str(operation["workspace_id"])
    upload_session_id = str(operation["operation_id"])
    session_path = (
        f"{API_PREFIX}/workspaces/{workspace_id}/upload-sessions/"
        f"{upload_session_id}"
    )
    return {
        "upload_session_id": upload_session_id,
        "state": public_state,
        "protocol": "kmfa-offset-v1",
        "original_name": str(operation["original_name"]),
        "reported_media_type": str(operation["reported_media_type"]),
        "size_bytes": expected_size,
        "offset_bytes": offset,
        "remaining_bytes": max(0, expected_size - offset),
        "chunk_count": chunk_count,
        "max_chunk_bytes": MAX_UPLOAD_CHUNK_BYTES,
        "checksum_algorithm": "sha256",
        "sha256": str(operation["content_sha256"]),
        "attachment_only": True,
        "upload_url": session_path,
        "complete_url": f"{session_path}/complete",
    }


def _create_resumable_upload_session(
    workspace_id: str,
    authorization: str | None,
    session_cookie: str | None,
    idempotency_key_header: str | None,
    request: CreateUploadSessionRequest,
) -> dict[str, Any]:
    _require_resumable_upload()
    if idempotency_key_header is None:
        raise SkeletonError(422, "invalid_idempotency_key")
    idempotency_key = _resolved_idempotency_key(idempotency_key_header)
    try:
        key_hash = idempotency_key_hash(idempotency_key)
    except ConsistencyStateError as exc:
        raise SkeletonError(422, "invalid_idempotency_key") from exc
    filename = _clean_plain_filename(request.original_name)
    media_type = _clean_media_type(request.reported_media_type)
    if SHA256_HEX_RE.fullmatch(request.sha256) is None:
        raise SkeletonError(422, "invalid_upload_checksum")
    if request.size_bytes > MAX_RESUMABLE_ARTIFACT_BYTES:
        raise SkeletonError(413, "artifact_too_large")
    try:
        fingerprint = upload_request_fingerprint(
            workspace_id=workspace_id,
            original_name=filename,
            reported_media_type=media_type,
            size_bytes=request.size_bytes,
            content_sha256=request.sha256,
        )
    except ConsistencyStateError as exc:
        raise SkeletonError(422, "invalid_upload_checksum") from exc

    with _store() as connection:
        _authorize(connection, workspace_id, authorization, session_cookie)
        existing = ConsistencyRepository(
            connection
        ).operation_for_idempotency(
            workspace_id=workspace_id,
            operation_kind="upload",
            idempotency_key_hash_value=key_hash,
        )
        if existing is not None:
            if (
                str(existing["request_fingerprint"]) != fingerprint
                or not is_resumable_staged_name(
                    str(existing["staged_object_name"])
                )
            ):
                raise SkeletonError(409, "idempotency_key_conflict")
            return {"upload_session": _upload_session_payload(dict(existing))}

    try:
        free_bytes = shutil.disk_usage(_state_root()).free
    except OSError as exc:
        raise SkeletonError(
            503, "walking_skeleton_storage_unavailable"
        ) from exc
    # Chunks and the verified assembled file coexist until the existing S05
    # object workflow accepts the original. Reserve both local copies so one
    # maximum session cannot consume the configured free-space floor.
    if free_bytes - (request.size_bytes * 2) < MIN_FREE_STATE_BYTES:
        raise SkeletonError(429, "artifact_capacity_reached")
    try:
        object_store = configured_write_store(_state_root())
        object_store.ensure_ready()
    except (
        ObjectStorageConfigurationError,
        ObjectStorageUnavailableError,
        OSError,
    ) as exc:
        raise SkeletonError(
            503, "walking_skeleton_storage_unavailable"
        ) from exc

    operation_id = _new_operation_id()
    try:
        with _store() as connection:
            with connection.transaction():
                _authorize(
                    connection,
                    workspace_id,
                    authorization,
                    session_cookie,
                )
                consistency = ConsistencyRepository(connection)
                durable_replay = consistency.operation_for_idempotency(
                    workspace_id=workspace_id,
                    operation_kind="upload",
                    idempotency_key_hash_value=key_hash,
                )
                if durable_replay is None:
                    resumable_session_count = int(
                        connection.execute(
                            """
                            SELECT COUNT(*) AS session_count
                            FROM consistency_operations
                            WHERE workspace_id = ?
                              AND operation_kind = 'upload'
                              AND staged_object_name LIKE ?
                            """,
                            (workspace_id, "resumable-%"),
                        ).fetchone()["session_count"]
                    )
                    if (
                        resumable_session_count
                        >= MAX_RESUMABLE_SESSIONS_PER_WORKSPACE
                    ):
                        raise SkeletonError(
                            429,
                            "upload_session_capacity_reached",
                        )
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
                    if competing_upload is not None:
                        raise SkeletonError(
                            409, "artifact_upload_in_progress"
                        )
                    if (
                        _artifact_capacity_usage(connection)
                        + request.size_bytes
                        > MAX_TOTAL_ARTIFACT_BYTES
                    ):
                        raise SkeletonError(
                            429, "artifact_capacity_reached"
                        )
                    artifact_id, version_number = (
                        _next_artifact_version_identity(
                            connection,
                            workspace_id,
                        )
                    )
                    version_id = artifact_version_id(
                        artifact_id,
                        version_number,
                    )
                    storage_key = object_store.build_storage_key(
                        workspace_id=workspace_id,
                        artifact_id=artifact_id,
                        artifact_version_id=version_id,
                        version_number=version_number,
                        sha256=request.sha256,
                    )
                    staged_object_name = resumable_staged_name(
                        operation_id
                    )
                else:
                    artifact_id = str(durable_replay["artifact_id"])
                    version_id = str(
                        durable_replay["artifact_version_id"]
                    )
                    version_number = int(
                        durable_replay["artifact_version_number"]
                    )
                    storage_key = str(durable_replay["storage_key"])
                    staged_object_name = str(
                        durable_replay["staged_object_name"]
                    )
                intent = UploadIntent(
                    workspace_id=workspace_id,
                    idempotency_key=idempotency_key,
                    request_fingerprint=fingerprint,
                    artifact_id=artifact_id,
                    artifact_version_id=version_id,
                    storage_backend=object_store.storage_backend,
                    storage_key=storage_key,
                    staged_object_name=staged_object_name,
                    original_name=filename,
                    reported_media_type=media_type,
                    size_bytes=request.size_bytes,
                    content_sha256=request.sha256,
                    artifact_version_number=version_number,
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
    if not is_resumable_staged_name(str(operation["staged_object_name"])):
        raise SkeletonError(409, "idempotency_key_conflict")
    return {"upload_session": _upload_session_payload(operation)}


async def _store_resumable_chunk(
    workspace_id: str,
    authorization: str | None,
    session_cookie: str | None,
    upload_session_id: str,
    upload_offset_header: str | None,
    chunk_sha256_header: str | None,
    request: Request,
) -> int:
    _require_resumable_upload()
    operation = _resumable_operation(
        workspace_id,
        authorization,
        session_cookie,
        upload_session_id,
    )
    if str(operation["state"]) != "intent_recorded":
        raise SkeletonError(409, "upload_session_not_active")
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != (
        "application/offset+octet-stream"
    ):
        raise SkeletonError(415, "invalid_upload_chunk_media_type")
    content_encoding = request.headers.get("content-encoding", "").strip().lower()
    if content_encoding not in {"", "identity"}:
        raise SkeletonError(415, "invalid_upload_content_encoding")
    try:
        upload_offset = int(upload_offset_header or "")
    except ValueError as exc:
        raise SkeletonError(422, "invalid_upload_offset") from exc
    if upload_offset < 0:
        raise SkeletonError(422, "invalid_upload_offset")
    claimed_sha256 = (chunk_sha256_header or "").strip().lower()
    if SHA256_HEX_RE.fullmatch(claimed_sha256) is None:
        raise SkeletonError(422, "invalid_upload_checksum")
    expected_size = int(operation["size_bytes"])
    content_length = request.headers.get("content-length", "").strip()
    declared_length: int | None = None
    if content_length:
        try:
            declared_length = int(content_length)
        except ValueError as exc:
            raise SkeletonError(400, "invalid_content_length") from exc
        if (
            declared_length < 1
            or declared_length > MAX_UPLOAD_CHUNK_BYTES
            or upload_offset + declared_length > expected_size
        ):
            raise SkeletonError(
                413,
                "artifact_too_large",
                headers=_upload_offset_headers(upload_offset),
            )
    try:
        free_bytes = shutil.disk_usage(_state_root()).free
    except OSError as exc:
        raise SkeletonError(
            503, "walking_skeleton_storage_unavailable"
        ) from exc
    if free_bytes - (
        declared_length or MAX_UPLOAD_CHUNK_BYTES
    ) < MIN_FREE_STATE_BYTES:
        raise SkeletonError(429, "artifact_capacity_reached")

    request_path = _tmp_dir() / f"request-{secrets.token_urlsafe(24)}.part"
    digest = hashlib.sha256()
    size = 0
    descriptor = os.open(
        request_path,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "wb") as output:
            try:
                async for chunk in request.stream():
                    if not chunk:
                        continue
                    size += len(chunk)
                    if (
                        size > MAX_UPLOAD_CHUNK_BYTES
                        or upload_offset + size > expected_size
                    ):
                        raise SkeletonError(
                            413,
                            "artifact_too_large",
                            headers=_upload_offset_headers(upload_offset),
                        )
                    digest.update(chunk)
                    output.write(chunk)
            except ClientDisconnect as exc:
                raise SkeletonError(
                    409,
                    "upload_chunk_interrupted",
                    headers=_upload_offset_headers(upload_offset),
                ) from exc
            output.flush()
            os.fsync(output.fileno())
        if size < 1:
            raise SkeletonError(422, "upload_chunk_size_invalid")
        actual_sha256 = digest.hexdigest()
        if actual_sha256 != claimed_sha256:
            raise SkeletonError(
                409,
                "upload_chunk_checksum_mismatch",
                headers=_upload_offset_headers(upload_offset),
            )
        operation = _resumable_operation(
            workspace_id,
            authorization,
            session_cookie,
            upload_session_id,
        )
        if str(operation["state"]) != "intent_recorded":
            raise SkeletonError(409, "upload_session_not_active")

        def assert_active_and_touch() -> None:
            with _store() as connection:
                with connection.transaction():
                    current = ConsistencyRepository(connection).operation(
                        upload_session_id
                    )
                    if (
                        current is None
                        or str(current["workspace_id"]) != workspace_id
                        or str(current["state"]) != "intent_recorded"
                    ):
                        raise SkeletonError(
                            409,
                            "upload_session_not_active",
                        )
                    connection.execute(
                        """
                        UPDATE consistency_operations
                        SET updated_at = ?, row_version = row_version + 1
                        WHERE operation_id = ? AND state = 'intent_recorded'
                        """,
                        (_timestamp(), upload_session_id),
                    )

        try:
            snapshot = store_verified_chunk(
                _tmp_dir(),
                upload_session_id,
                request_path,
                upload_offset=upload_offset,
                chunk_size=size,
                chunk_sha256=actual_sha256,
                expected_size=int(operation["size_bytes"]),
                max_chunk_bytes=MAX_UPLOAD_CHUNK_BYTES,
                active_check=assert_active_and_touch,
            )
        except ResumableStorageError as error:
            _raise_resumable_storage(error)
        return snapshot.offset_bytes
    finally:
        request_path.unlink(missing_ok=True)


def _complete_resumable_upload(
    workspace_id: str,
    authorization: str | None,
    session_cookie: str | None,
    upload_session_id: str,
) -> dict[str, Any]:
    _require_resumable_upload()
    operation = _resumable_operation(
        workspace_id,
        authorization,
        session_cookie,
        upload_session_id,
    )
    state = str(operation["state"])
    if state == "isolated":
        raise SkeletonError(409, "upload_session_isolated")
    if state == "intent_recorded":
        try:
            assemble_upload(
                _tmp_dir(),
                upload_session_id,
                expected_size=int(operation["size_bytes"]),
                expected_sha256=str(operation["content_sha256"]),
                max_chunk_bytes=MAX_UPLOAD_CHUNK_BYTES,
            )
        except ResumableStorageError as error:
            _raise_resumable_storage(error)
    payload = _resume_upload_operation(upload_session_id, None)
    try:
        cleanup_chunks(
            _tmp_dir(),
            upload_session_id,
            expected_size=int(operation["size_bytes"]),
            max_chunk_bytes=MAX_UPLOAD_CHUNK_BYTES,
        )
    except ResumableStorageError as error:
        _raise_resumable_storage(error)
    return payload


def _cancel_resumable_upload(
    workspace_id: str,
    authorization: str | None,
    session_cookie: str | None,
    upload_session_id: str,
) -> None:
    _require_resumable_upload()
    operation = _resumable_operation(
        workspace_id,
        authorization,
        session_cookie,
        upload_session_id,
    )
    operation_state = str(operation["state"])
    already_cancelled = (
        operation_state == "isolated"
        and str(operation["last_error_code"])
        == "resumable_upload_cancelled"
    )
    if operation_state != "intent_recorded" and not already_cancelled:
        raise SkeletonError(409, "upload_session_not_cancellable")

    def claim_cancellation() -> None:
        with _store() as connection:
            with connection.transaction():
                current = ConsistencyRepository(connection).operation(
                    upload_session_id
                )
                if current is None:
                    raise SkeletonError(404, "upload_session_not_found")
                if (
                    str(current["state"]) == "isolated"
                    and str(current["last_error_code"])
                    == "resumable_upload_cancelled"
                ):
                    return
                if str(current["state"]) != "intent_recorded":
                    raise SkeletonError(
                        409,
                        "upload_session_not_cancellable",
                    )
                try:
                    ConsistencyRepository(connection).transition(
                        upload_session_id,
                        expected_state="intent_recorded",
                        to_state="isolated",
                        transition_code="resumable_upload_cancelled",
                        error_code="resumable_upload_cancelled",
                        timestamp=_timestamp(),
                    )
                except ConsistencyStateError as exc:
                    raise SkeletonError(
                        409,
                        "upload_session_not_cancellable",
                    ) from exc

    try:
        discard_incomplete(
            _tmp_dir(),
            upload_session_id,
            expected_size=int(operation["size_bytes"]),
            max_chunk_bytes=MAX_UPLOAD_CHUNK_BYTES,
            before_discard=claim_cancellation,
        )
    except ResumableStorageError as error:
        _raise_resumable_storage(error)


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
        try:
            require_download_allowed(
                connection,
                artifact_version_id=str(
                    artifact_payload["artifact_version_id"]
                ),
            )
        except FileSecurityStateConflict as exc:
            raise SkeletonError(409, str(exc)) from exc
        artifact_payload["security"] = artifact_security_payload(
            connection,
            artifact_version_id=str(
                artifact_payload["artifact_version_id"]
            ),
        )

    return _materialize_download_asset(
        workspace_id,
        authorization,
        session_cookie,
        artifact_payload,
    )


def _selected_asset_for_download(
    workspace_id: str,
    authorization: str | None,
    session_cookie: str | None,
    request: DownloadAssetRequest,
) -> tuple[Path, dict[str, Any], bool]:
    if not single_file_download_enabled():
        raise SkeletonError(404, "single_file_download_disabled")
    with _store() as connection:
        _authorize(connection, workspace_id, authorization, session_cookie)
        selected = next(
            (
                row
                for row in StructuredRepository(
                    connection
                ).downloadable_assets(workspace_id)
                if str(row["asset_kind"]) == request.kind
                and str(row["asset_id"]) == request.asset_id
            ),
            None,
        )
        if selected is None:
            raise SkeletonError(404, "artifact_download_not_found")
        artifact_payload = dict(selected)
        source_artifact_version_id = str(
            artifact_payload["source_artifact_version_id"]
        )
        security = artifact_security_payload(
            connection,
            artifact_version_id=source_artifact_version_id,
        )
        if request.kind == "original":
            try:
                require_download_allowed(
                    connection,
                    artifact_version_id=source_artifact_version_id,
                )
            except FileSecurityStateConflict as exc:
                raise SkeletonError(409, str(exc)) from exc
        elif security["state"] != "clean":
            raise SkeletonError(409, "artifact_security_pending")
        artifact_payload["security"] = security

    return _materialize_download_asset(
        workspace_id,
        authorization,
        session_cookie,
        artifact_payload,
    )


def _materialize_download_asset(
    workspace_id: str,
    authorization: str | None,
    session_cookie: str | None,
    artifact_payload: dict[str, Any],
) -> tuple[Path, dict[str, Any], bool]:
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


def _artifact_for_preview(
    workspace_id: str,
    authorization: str | None,
    session_cookie: str | None = None,
) -> tuple[Path, dict[str, Any], bool]:
    if not derivation_enabled():
        raise SkeletonError(404, "artifact_preview_disabled")
    with _store() as connection:
        _authorize(connection, workspace_id, authorization, session_cookie)
        artifact = StructuredRepository(connection).latest_artifact_version(
            workspace_id
        )
        if artifact is None:
            raise SkeletonError(404, "artifact_not_found")
        security = artifact_security_payload(
            connection,
            artifact_version_id=str(artifact["artifact_version_id"]),
        )
        if (
            security["state"] != "clean"
            or security["detected_media_type"]
            not in SUPPORTED_DETECTED_MEDIA_TYPES
        ):
            raise SkeletonError(409, "artifact_preview_unavailable")
        derivative = ArtifactLineageRepository(
            connection
        ).latest_derivative(str(artifact["artifact_version_id"]))
        if derivative is None:
            raise SkeletonError(409, "artifact_preview_pending")
        derivative_payload = dict(derivative)
    try:
        object_store = object_store_for_backend(
            _state_root(),
            str(derivative_payload["storage_backend"]),
        )
        materialized = object_store.materialize_verified(
            storage_key=str(derivative_payload["storage_key"]),
            expected_size=int(derivative_payload["size_bytes"]),
            expected_sha256=str(derivative_payload["sha256"]),
        )
    except ObjectStorageMissingError as exc:
        raise SkeletonError(503, "artifact_preview_unavailable") from exc
    except ObjectStorageIntegrityError as exc:
        raise SkeletonError(503, "artifact_preview_integrity_failed") from exc
    except (
        ObjectStorageConfigurationError,
        ObjectStorageUnavailableError,
    ) as exc:
        raise SkeletonError(503, "artifact_preview_unavailable") from exc
    return materialized.path, derivative_payload, materialized.temporary


def _artifact_lineage(
    workspace_id: str,
    authorization: str | None,
    session_cookie: str | None = None,
) -> dict[str, Any]:
    with _store() as connection:
        _authorize(connection, workspace_id, authorization, session_cookie)
        return ArtifactLineageRepository(connection).lineage_graph(
            workspace_id
        )


def _request_artifact_reprocess(
    workspace_id: str,
    authorization: str | None,
    session_cookie: str | None,
    idempotency_key: str | None,
) -> dict[str, Any]:
    if not derivation_enabled():
        raise SkeletonError(404, "artifact_preview_disabled")
    if idempotency_key is None:
        raise SkeletonError(422, "invalid_idempotency_key")
    with _store() as connection:
        try:
            with connection.transaction():
                _authorize(
                    connection,
                    workspace_id,
                    authorization,
                    session_cookie,
                )
                artifact = StructuredRepository(
                    connection
                ).latest_artifact_version(workspace_id)
                if artifact is None:
                    raise SkeletonError(404, "artifact_not_found")
                security = artifact_security_payload(
                    connection,
                    artifact_version_id=str(
                        artifact["artifact_version_id"]
                    ),
                )
                if (
                    security["state"] != "clean"
                    or security["detected_media_type"]
                    not in SUPPORTED_DETECTED_MEDIA_TYPES
                ):
                    raise SkeletonError(
                        409, "artifact_preview_unavailable"
                    )
                run, created = ArtifactLineageRepository(
                    connection
                ).request_reprocess(
                    workspace_id=workspace_id,
                    source_artifact_version_id=str(
                        artifact["artifact_version_id"]
                    ),
                    idempotency_key=idempotency_key,
                    timestamp=_timestamp(),
                )
                if created:
                    _append_audit(
                        connection,
                        workspace_id,
                        "artifact_reprocess_requested",
                        artifact_sha256=str(artifact["sha256"]),
                    )
        except ArtifactLineageError as exc:
            code = str(exc)
            if code == "invalid_idempotency_key":
                raise SkeletonError(422, code) from exc
            raise SkeletonError(409, code) from exc
    return {
        "processing_run_id": str(run["processing_run_id"]),
        "artifact_version_id": str(run["source_artifact_version_id"]),
        "processor": {
            "name": str(run["processor_name"]),
            "version": str(run["processor_version"]),
        },
        "state": str(run["state"]),
        "original_preserved": True,
    }


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
        security_contract = public_file_security_contract()
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
    except FileSecurityError:
        _raise_http(SkeletonError(503, "file_security_unavailable"))
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
            "artifact_version_lineage": True,
            "artifact_derivatives": True,
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
            "max_versions_per_artifact": MAX_ARTIFACT_VERSIONS,
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
        "resumable_upload": {
            "enabled": resumable_upload_enabled(),
            "protocol": "kmfa-offset-v1",
            "max_file_bytes": MAX_RESUMABLE_ARTIFACT_BYTES,
            "max_chunk_bytes": MAX_UPLOAD_CHUNK_BYTES,
            "max_sessions_per_workspace": (
                MAX_RESUMABLE_SESSIONS_PER_WORKSPACE
            ),
            "checksum": "sha256",
            "attachment_only_until_classified": True,
            "standard_upload_rollback": True,
        },
        "file_security": security_contract,
        "artifact_derivation": public_derivation_contract(),
        "single_file_download": public_single_file_download_contract(),
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
            + (
                [] if file_security_enabled() else ["malware-controls"]
            )
            + (
                [] if derivation_enabled() else ["safe-preview-worker"]
            )
            + [
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


@router.post("/workspaces/{workspace_id}/upload-sessions", status_code=201)
def create_resumable_upload_session(
    workspace_id: str,
    request: CreateUploadSessionRequest,
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
        payload = _create_resumable_upload_session(
            workspace_id,
            authorization,
            session_cookie,
            idempotency_key,
            request,
        )
    except SkeletonError as error:
        _raise_http(error)
    upload_session = payload["upload_session"]
    response.headers.update(
        {
            **_upload_offset_headers(
                int(upload_session["offset_bytes"]),
            ),
            "Upload-Length": str(upload_session["size_bytes"]),
            "Location": str(upload_session["upload_url"]),
        }
    )
    return payload


@router.get(
    "/workspaces/{workspace_id}/upload-sessions/{upload_session_id}"
)
def get_resumable_upload_session(
    workspace_id: str,
    upload_session_id: str,
    authorization: str | None = Header(default=None),
    session_cookie: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
) -> dict[str, Any]:
    try:
        _require_resumable_upload()
        operation = _resumable_operation(
            workspace_id,
            authorization,
            session_cookie,
            upload_session_id,
        )
        return {"upload_session": _upload_session_payload(operation)}
    except SkeletonError as error:
        _raise_http(error)


@router.head(
    "/workspaces/{workspace_id}/upload-sessions/{upload_session_id}"
)
def head_resumable_upload_session(
    workspace_id: str,
    upload_session_id: str,
    authorization: str | None = Header(default=None),
    session_cookie: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
) -> Response:
    try:
        _require_resumable_upload()
        operation = _resumable_operation(
            workspace_id,
            authorization,
            session_cookie,
            upload_session_id,
        )
        payload = _upload_session_payload(operation)
    except SkeletonError as error:
        _raise_http(error)
    return Response(
        status_code=204,
        headers={
            **_upload_offset_headers(int(payload["offset_bytes"])),
            "Upload-Length": str(payload["size_bytes"]),
            "Upload-State": str(payload["state"]),
        },
    )


@router.patch(
    "/workspaces/{workspace_id}/upload-sessions/{upload_session_id}",
    status_code=204,
)
async def upload_resumable_chunk(
    workspace_id: str,
    upload_session_id: str,
    request: Request,
    authorization: str | None = Header(default=None),
    upload_offset: str | None = Header(default=None, alias="Upload-Offset"),
    chunk_sha256: str | None = Header(
        default=None,
        alias="X-KMFA-Chunk-SHA256",
    ),
    session_cookie: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
) -> Response:
    try:
        next_offset = await _store_resumable_chunk(
            workspace_id,
            authorization,
            session_cookie,
            upload_session_id,
            upload_offset,
            chunk_sha256,
            request,
        )
        operation = _resumable_operation(
            workspace_id,
            authorization,
            session_cookie,
            upload_session_id,
        )
    except SkeletonError as error:
        _raise_http(error)
    return Response(
        status_code=204,
        headers={
            **_upload_offset_headers(next_offset),
            "Upload-Length": str(operation["size_bytes"]),
        },
    )


@router.post(
    "/workspaces/{workspace_id}/upload-sessions/{upload_session_id}/complete"
)
def complete_resumable_upload(
    workspace_id: str,
    upload_session_id: str,
    authorization: str | None = Header(default=None),
    session_cookie: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
) -> dict[str, Any]:
    try:
        return _complete_resumable_upload(
            workspace_id,
            authorization,
            session_cookie,
            upload_session_id,
        )
    except SkeletonError as error:
        _raise_http(error)


@router.delete(
    "/workspaces/{workspace_id}/upload-sessions/{upload_session_id}",
    status_code=204,
)
def cancel_resumable_upload(
    workspace_id: str,
    upload_session_id: str,
    authorization: str | None = Header(default=None),
    session_cookie: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
) -> Response:
    try:
        _cancel_resumable_upload(
            workspace_id,
            authorization,
            session_cookie,
            upload_session_id,
        )
    except SkeletonError as error:
        _raise_http(error)
    return Response(status_code=204)


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
            "X-KMFA-Artifact-Security": artifact["security"]["state"],
        },
        background=(
            BackgroundTask(path.unlink, missing_ok=True) if temporary else None
        ),
    )


@router.post("/workspaces/{workspace_id}/artifact/downloads")
def download_selected_artifact(
    workspace_id: str,
    request: DownloadAssetRequest,
    authorization: str | None = Header(default=None),
    session_cookie: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
) -> FileResponse:
    try:
        _require_enabled()
        path, asset, temporary = _selected_asset_for_download(
            workspace_id,
            authorization,
            session_cookie,
            request,
        )
    except SkeletonError as error:
        _raise_http(error)
    headers = {
        "Cache-Control": "private, no-store",
        "Pragma": "no-cache",
        "X-Content-Type-Options": "nosniff",
        "X-KMFA-Artifact-SHA256": str(asset["sha256"]),
        "X-KMFA-Artifact-Size": str(asset["size_bytes"]),
        "X-KMFA-Artifact-Media-Type": str(asset["media_type"]),
        "X-KMFA-Artifact-Kind": str(asset["asset_kind"]),
        "X-KMFA-Artifact-ID": str(asset["asset_id"]),
        "X-KMFA-Artifact-Mode": "attachment-only",
        "X-KMFA-Artifact-Security": str(asset["security"]["state"]),
        "X-KMFA-Source-Artifact-Version": str(
            asset["source_artifact_version_id"]
        ),
        "X-KMFA-Source-Kind": (
            "upload"
            if str(asset["asset_kind"]) == "original"
            else "processor"
        ),
    }
    if asset["source_operation_id"] is not None:
        headers["X-KMFA-Source-Operation"] = str(
            asset["source_operation_id"]
        )
    if asset["processor_name"] is not None:
        headers["X-KMFA-Processor"] = (
            f"{asset['processor_name']}/{asset['processor_version']}"
        )
    return FileResponse(
        path,
        media_type=_clean_media_type(str(asset["media_type"])),
        filename=str(asset["original_name"]),
        content_disposition_type="attachment",
        headers=headers,
        background=(
            BackgroundTask(path.unlink, missing_ok=True) if temporary else None
        ),
    )


@router.get("/workspaces/{workspace_id}/artifact/preview")
def preview_artifact(
    workspace_id: str,
    authorization: str | None = Header(default=None),
    session_cookie: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
) -> FileResponse:
    try:
        _require_enabled()
        path, derivative, temporary = _artifact_for_preview(
            workspace_id,
            authorization,
            session_cookie,
        )
    except SkeletonError as error:
        _raise_http(error)
    return FileResponse(
        path,
        media_type="text/plain; charset=utf-8",
        filename="kmfa-safe-text-preview.txt",
        content_disposition_type="inline",
        headers={
            "Cache-Control": "private, no-store",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; sandbox",
            "X-KMFA-Derivative-SHA256": str(derivative["sha256"]),
            "X-KMFA-Processor": (
                f"{derivative['processor_name']}/"
                f"{derivative['processor_version']}"
            ),
        },
        background=(
            BackgroundTask(path.unlink, missing_ok=True) if temporary else None
        ),
    )


@router.get("/workspaces/{workspace_id}/artifact/lineage")
def get_artifact_lineage(
    workspace_id: str,
    authorization: str | None = Header(default=None),
    session_cookie: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
) -> dict[str, Any]:
    try:
        _require_enabled()
        return _artifact_lineage(
            workspace_id,
            authorization,
            session_cookie,
        )
    except SkeletonError as error:
        _raise_http(error)


@router.post(
    "/workspaces/{workspace_id}/artifact/reprocess",
    status_code=202,
)
def reprocess_artifact(
    workspace_id: str,
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
        return _request_artifact_reprocess(
            workspace_id,
            authorization,
            session_cookie,
            idempotency_key,
        )
    except SkeletonError as error:
        _raise_http(error)


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
