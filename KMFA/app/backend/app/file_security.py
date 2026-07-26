"""Durable quarantine state and private scanner coordination for S06/P6.2.

The web/worker process may read the already verified private original, but it
never parses the file.  Parsing is delegated to the authenticated scanner
service.  The scanner receives no database DSN, object-store credential, or
state volume.  Scanner timeout/error is persisted and is never interpreted as
``clean``.
"""

from __future__ import annotations

import hashlib
import http.client
import ipaddress
import os
import re
import secrets
import socket
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import SplitResult, urlsplit

from .consistency_state import ConsistencyRepository
from .file_security_protocol import (
    FILE_SECURITY_POLICY_VERSION,
    MAX_RESPONSE_BYTES,
    PROTOCOL_VERSION,
    SCANNER_ENGINE,
    SCANNER_VERSION,
    FileSecurityProtocolError,
    encode_filename,
    request_mac,
    validate_signed_response,
    validated_shared_secret,
)
from .object_storage import ObjectStorageError, object_store_for_backend
from .structured_store import (
    StructuredStoreConnection,
    StructuredStoreError,
    open_structured_store,
)

FILE_SECURITY_ENABLED_ENV = "KMFA_FILE_SECURITY_ENABLED"
SCANNER_URL_ENV = "KMFA_FILE_SCANNER_URL"
SCANNER_SHARED_SECRET_ENV = "KMFA_FILE_SCANNER_SHARED_SECRET"
SCANNER_TIMEOUT_ENV = "KMFA_FILE_SCANNER_TIMEOUT_SECONDS"
SCAN_LEASE_ENV = "KMFA_FILE_SCAN_LEASE_SECONDS"
SCAN_RETRY_DELAY_ENV = "KMFA_FILE_SCAN_RETRY_DELAY_SECONDS"
SCAN_MAX_ATTEMPTS_ENV = "KMFA_FILE_SCAN_MAX_ATTEMPTS"

TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
TERMINAL_SECURITY_STATES = frozenset(
    {
        "clean",
        "attachment_only",
        "rejected",
        "timed_out",
        "scanner_error",
    }
)
SECURITY_STATES = frozenset(
    {"quarantined", "scanning", *TERMINAL_SECURITY_STATES}
)
RETRYABLE_SECURITY_STATES = frozenset(
    {"quarantined", "scanning", "timed_out", "scanner_error"}
)
DOWNLOADABLE_WHEN_ENABLED = frozenset(
    {"clean", "attachment_only", "timed_out", "scanner_error"}
)

_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{2,79}$")
_MEDIA_TYPE_RE = re.compile(
    r"^[a-z0-9][a-z0-9!#$&^_.+-]{0,126}/"
    r"[a-z0-9][a-z0-9!#$&^_.+-]{0,126}$"
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class FileSecurityError(StructuredStoreError):
    """Static, private-data-free file security failure."""


class FileSecurityConfigurationError(FileSecurityError):
    pass


class FileSecurityStateConflict(FileSecurityError):
    pass


class FileSecurityClientError(FileSecurityError):
    pass


class FileSecurityTimeoutError(FileSecurityClientError):
    pass


@dataclass(frozen=True)
class FileSecurityConfig:
    scanner_url: str
    shared_secret: bytes
    timeout_seconds: float
    lease_seconds: int
    retry_delay_seconds: int
    max_attempts: int

    @classmethod
    def from_environment(cls) -> FileSecurityConfig:
        scanner_url = os.environ.get(SCANNER_URL_ENV, "").strip()
        try:
            secret = validated_shared_secret(
                os.environ.get(SCANNER_SHARED_SECRET_ENV, "")
            )
        except FileSecurityProtocolError as exc:
            raise FileSecurityConfigurationError(
                "file_security_configuration_invalid"
            ) from exc
        timeout_seconds = _float_environment(
            SCANNER_TIMEOUT_ENV,
            default=10.0,
            minimum=0.05,
            maximum=60.0,
        )
        lease_seconds = _integer_environment(
            SCAN_LEASE_ENV,
            default=60,
            minimum=max(1, int(timeout_seconds) + 1),
            maximum=600,
        )
        retry_delay_seconds = _integer_environment(
            SCAN_RETRY_DELAY_ENV,
            default=30,
            minimum=0,
            maximum=3600,
        )
        max_attempts = _integer_environment(
            SCAN_MAX_ATTEMPTS_ENV,
            default=3,
            minimum=1,
            maximum=10,
        )
        _validated_endpoint(scanner_url)
        return cls(
            scanner_url=scanner_url,
            shared_secret=secret,
            timeout_seconds=timeout_seconds,
            lease_seconds=lease_seconds,
            retry_delay_seconds=retry_delay_seconds,
            max_attempts=max_attempts,
        )


@dataclass(frozen=True)
class SecurityScanClaim:
    artifact_version_id: str
    operation_id: str | None
    normalized_name: str
    reported_media_type: str
    source_size_bytes: int
    source_sha256: str
    storage_backend: str
    storage_key: str
    attempt_count: int
    row_version: int


@dataclass(frozen=True)
class ScanOutcome:
    verdict: str
    reason_code: str
    detected_media_type: str
    scanner_engine: str
    scanner_version: str
    policy_version: str


@dataclass(frozen=True)
class SecurityRunResult:
    artifact_version_id: str
    state: str
    reason_code: str
    attempt_count: int


def file_security_enabled() -> bool:
    return (
        os.environ.get(FILE_SECURITY_ENABLED_ENV, "").strip().lower()
        in TRUE_VALUES
    )


def _float_environment(
    name: str,
    *,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    raw = os.environ.get(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise FileSecurityConfigurationError(
            "file_security_configuration_invalid"
        ) from exc
    if not minimum <= value <= maximum:
        raise FileSecurityConfigurationError(
            "file_security_configuration_invalid"
        )
    return value


def _integer_environment(
    name: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw = os.environ.get(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise FileSecurityConfigurationError(
            "file_security_configuration_invalid"
        ) from exc
    if not minimum <= value <= maximum:
        raise FileSecurityConfigurationError(
            "file_security_configuration_invalid"
        )
    return value


def _timestamp(value: datetime | None = None) -> str:
    return (
        (value or datetime.now(timezone.utc))
        .astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _new_event_id() -> str:
    return f"security-event_{secrets.token_urlsafe(18)}"


def _opaque_artifact_ref(artifact_version_id: str) -> str:
    return hashlib.sha256(artifact_version_id.encode("utf-8")).hexdigest()[:20]


def _validated_endpoint(value: str) -> SplitResult:
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError as exc:
        raise FileSecurityConfigurationError(
            "file_security_scanner_url_invalid"
        ) from exc
    if (
        parsed.scheme != "http"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path != "/scan"
        or port is None
    ):
        raise FileSecurityConfigurationError(
            "file_security_scanner_url_invalid"
        )
    return parsed


def _resolved_private_address(parsed: SplitResult) -> tuple[str, int]:
    assert parsed.hostname is not None
    assert parsed.port is not None
    try:
        addresses = socket.getaddrinfo(
            parsed.hostname,
            parsed.port,
            type=socket.SOCK_STREAM,
        )
    except OSError as exc:
        raise FileSecurityClientError("file_security_scanner_unavailable") from exc
    resolved: list[str] = []
    for address in addresses:
        candidate = str(address[4][0])
        try:
            ip = ipaddress.ip_address(candidate)
        except ValueError as exc:
            raise FileSecurityClientError(
                "file_security_scanner_unavailable"
            ) from exc
        if (
            not (ip.is_private or ip.is_loopback)
            or ip.is_multicast
            or ip.is_unspecified
            or ip.is_link_local
            or ip.is_reserved
        ):
            raise FileSecurityClientError(
                "file_security_scanner_not_private"
            )
        if candidate not in resolved:
            resolved.append(candidate)
    if not resolved:
        raise FileSecurityClientError("file_security_scanner_unavailable")
    return resolved[0], parsed.port


class FileSecurityRepository:
    """Transactional assessment state; callers own the transaction."""

    def __init__(self, connection: StructuredStoreConnection) -> None:
        self.connection = connection

    def _append_event(
        self,
        *,
        artifact_version_id: str,
        from_state: str | None,
        to_state: str,
        reason_code: str,
        timestamp: str,
    ) -> None:
        if (
            (from_state is not None and from_state not in SECURITY_STATES)
            or to_state not in SECURITY_STATES
            or _CODE_RE.fullmatch(reason_code) is None
        ):
            raise FileSecurityStateConflict("file_security_state_invalid")
        self.connection.execute(
            """
            INSERT INTO artifact_security_events(
              event_id, artifact_ref, from_state, to_state,
              reason_code, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                _new_event_id(),
                _opaque_artifact_ref(artifact_version_id),
                from_state,
                to_state,
                reason_code,
                timestamp,
            ),
        )

    def assessment(self, artifact_version_id: str) -> Any | None:
        return self.connection.execute(
            """
            SELECT *
            FROM artifact_security_assessments
            WHERE artifact_version_id = ?
            """,
            (artifact_version_id,),
        ).fetchone()

    def ensure_quarantined(
        self,
        *,
        artifact_version_id: str,
        operation_id: str | None,
        normalized_name: str,
        reported_media_type: str,
        source_size_bytes: int,
        source_sha256: str,
        storage_backend: str,
        storage_key: str,
        timestamp: str,
    ) -> Any:
        if (
            not normalized_name
            or len(normalized_name.encode("utf-8")) > 255
            or _MEDIA_TYPE_RE.fullmatch(reported_media_type) is None
            or source_size_bytes < 0
            or _SHA256_RE.fullmatch(source_sha256) is None
        ):
            raise FileSecurityStateConflict("file_security_identity_invalid")
        inserted = self.connection.execute(
            """
            INSERT INTO artifact_security_assessments(
              artifact_version_id, operation_id, normalized_name,
              reported_media_type, detected_media_type, source_size_bytes,
              source_sha256, state, reason_code, scanner_engine,
              scanner_version, policy_version, attempt_count, lease_until,
              row_version, created_at, updated_at, completed_at
            ) VALUES (
              ?, ?, ?, ?, NULL, ?, ?, 'quarantined',
              'security_scan_pending', NULL, NULL, ?, 0, NULL, 1, ?, ?, NULL
            )
            ON CONFLICT(artifact_version_id) DO NOTHING
            """,
            (
                artifact_version_id,
                operation_id,
                normalized_name,
                reported_media_type,
                source_size_bytes,
                source_sha256,
                FILE_SECURITY_POLICY_VERSION,
                timestamp,
                timestamp,
            ),
        )
        row = self.assessment(artifact_version_id)
        expected = {
            "operation_id": operation_id,
            "normalized_name": normalized_name,
            "reported_media_type": reported_media_type,
            "source_size_bytes": source_size_bytes,
            "source_sha256": source_sha256,
        }
        if row is None or any(row[key] != value for key, value in expected.items()):
            raise FileSecurityStateConflict(
                "file_security_assessment_conflict"
            )
        if inserted.rowcount == 1:
            self._append_event(
                artifact_version_id=artifact_version_id,
                from_state=None,
                to_state="quarantined",
                reason_code="security_scan_pending",
                timestamp=timestamp,
            )
        ConsistencyRepository(self.connection).quarantine_object(
            operation_id=operation_id,
            storage_backend=storage_backend,
            storage_key=storage_key,
            reason_code="security_scan_pending",
            timestamp=timestamp,
        )
        return row

    def claim(
        self,
        *,
        now: datetime,
        lease_seconds: int,
        retry_delay_seconds: int,
        max_attempts: int,
        artifact_version_id: str | None = None,
    ) -> SecurityScanClaim | None:
        now_text = _timestamp(now)
        retry_before = _timestamp(now - timedelta(seconds=retry_delay_seconds))
        identity_clause = (
            "AND asa.artifact_version_id = ?"
            if artifact_version_id is not None
            else ""
        )
        parameters: tuple[Any, ...] = (
            max_attempts,
            retry_before,
            now_text,
            *((artifact_version_id,) if artifact_version_id is not None else ()),
        )
        row = self.connection.execute(
            f"""
            SELECT
              asa.*, av.storage_backend, av.storage_key
            FROM artifact_security_assessments asa
            JOIN artifact_versions av
              ON av.artifact_version_id = asa.artifact_version_id
            JOIN projects project
              ON project.project_id = av.project_id
            JOIN workspace_retention retention
              ON retention.workspace_id = project.workspace_id
            WHERE retention.state = 'active'
              AND asa.attempt_count < ?
              AND (
                asa.state = 'quarantined'
                OR (
                  asa.state IN ('timed_out', 'scanner_error')
                  AND asa.updated_at <= ?
                )
                OR (
                  asa.state = 'scanning'
                  AND asa.lease_until <= ?
                )
              )
              {identity_clause}
            ORDER BY asa.updated_at, asa.artifact_version_id
            LIMIT 1
            """,
            parameters,
        ).fetchone()
        if row is None:
            return None
        from_state = str(row["state"])
        lease_until = _timestamp(now + timedelta(seconds=lease_seconds))
        updated = self.connection.execute(
            """
            UPDATE artifact_security_assessments
            SET state = 'scanning',
                reason_code = 'security_scan_in_progress',
                detected_media_type = NULL,
                scanner_engine = NULL,
                scanner_version = NULL,
                attempt_count = attempt_count + 1,
                lease_until = ?,
                row_version = row_version + 1,
                updated_at = ?,
                completed_at = NULL
            WHERE artifact_version_id = ?
              AND row_version = ?
              AND state = ?
            """,
            (
                lease_until,
                now_text,
                row["artifact_version_id"],
                row["row_version"],
                from_state,
            ),
        )
        if updated.rowcount != 1:
            return None
        self._append_event(
            artifact_version_id=str(row["artifact_version_id"]),
            from_state=from_state,
            to_state="scanning",
            reason_code="security_scan_in_progress",
            timestamp=now_text,
        )
        self.connection.execute(
            """
            UPDATE object_quarantine
            SET state = 'isolated', last_seen_at = ?
            WHERE storage_backend = ? AND storage_key = ?
              AND reason_code = 'security_scan_pending'
            """,
            (now_text, row["storage_backend"], row["storage_key"]),
        )
        claimed = self.assessment(str(row["artifact_version_id"]))
        if claimed is None:
            raise FileSecurityStateConflict("file_security_assessment_missing")
        return SecurityScanClaim(
            artifact_version_id=str(claimed["artifact_version_id"]),
            operation_id=(
                str(claimed["operation_id"])
                if claimed["operation_id"] is not None
                else None
            ),
            normalized_name=str(claimed["normalized_name"]),
            reported_media_type=str(claimed["reported_media_type"]),
            source_size_bytes=int(claimed["source_size_bytes"]),
            source_sha256=str(claimed["source_sha256"]),
            storage_backend=str(row["storage_backend"]),
            storage_key=str(row["storage_key"]),
            attempt_count=int(claimed["attempt_count"]),
            row_version=int(claimed["row_version"]),
        )

    def complete(
        self,
        claim: SecurityScanClaim,
        *,
        state: str,
        reason_code: str,
        detected_media_type: str | None,
        scanner_engine: str | None,
        scanner_version: str | None,
        policy_version: str,
        timestamp: str,
    ) -> SecurityRunResult:
        if (
            state not in TERMINAL_SECURITY_STATES
            or _CODE_RE.fullmatch(reason_code) is None
            or (
                detected_media_type is not None
                and _MEDIA_TYPE_RE.fullmatch(detected_media_type) is None
            )
        ):
            raise FileSecurityStateConflict("file_security_result_invalid")
        updated = self.connection.execute(
            """
            UPDATE artifact_security_assessments
            SET state = ?, reason_code = ?, detected_media_type = ?,
                scanner_engine = ?, scanner_version = ?, policy_version = ?,
                lease_until = NULL, row_version = row_version + 1,
                updated_at = ?, completed_at = ?
            WHERE artifact_version_id = ?
              AND state = 'scanning'
              AND row_version = ?
            """,
            (
                state,
                reason_code,
                detected_media_type,
                scanner_engine,
                scanner_version,
                policy_version,
                timestamp,
                timestamp,
                claim.artifact_version_id,
                claim.row_version,
            ),
        )
        if updated.rowcount != 1:
            raise FileSecurityStateConflict("file_security_state_conflict")
        self._append_event(
            artifact_version_id=claim.artifact_version_id,
            from_state="scanning",
            to_state=state,
            reason_code=reason_code,
            timestamp=timestamp,
        )
        if state != "rejected":
            self.connection.execute(
                """
                UPDATE object_quarantine
                SET state = 'released', last_seen_at = ?
                WHERE storage_backend = ? AND storage_key = ?
                  AND reason_code = 'security_scan_pending'
                """,
                (timestamp, claim.storage_backend, claim.storage_key),
            )
        return SecurityRunResult(
            artifact_version_id=claim.artifact_version_id,
            state=state,
            reason_code=reason_code,
            attempt_count=claim.attempt_count,
        )


def artifact_security_payload(
    connection: StructuredStoreConnection,
    *,
    artifact_version_id: str,
) -> dict[str, Any]:
    row = FileSecurityRepository(connection).assessment(artifact_version_id)
    enabled = file_security_enabled()
    if row is None:
        return {
            "state": "unscanned_attachment_only",
            "reason_code": "security_assessment_not_available",
            "detected_media_type": None,
            "attempt_count": 0,
            "scan_complete": False,
            "download_allowed": True,
            "preview_allowed": False,
            "processing_allowed": False,
            "policy_version": FILE_SECURITY_POLICY_VERSION,
            "updated_at": None,
        }
    state = str(row["state"])
    download_allowed = (
        state != "rejected"
        and (not enabled or state in DOWNLOADABLE_WHEN_ENABLED)
    )
    return {
        "state": state,
        "reason_code": str(row["reason_code"]),
        "detected_media_type": row["detected_media_type"],
        "attempt_count": int(row["attempt_count"]),
        "scan_complete": state in TERMINAL_SECURITY_STATES,
        "download_allowed": download_allowed,
        "preview_allowed": False,
        "processing_allowed": False,
        "policy_version": str(row["policy_version"]),
        "updated_at": str(row["updated_at"]),
    }


def require_download_allowed(
    connection: StructuredStoreConnection,
    *,
    artifact_version_id: str,
) -> None:
    row = FileSecurityRepository(connection).assessment(artifact_version_id)
    if row is None:
        return
    state = str(row["state"])
    if state == "rejected":
        raise FileSecurityStateConflict("artifact_security_rejected")
    if file_security_enabled() and state not in DOWNLOADABLE_WHEN_ENABLED:
        raise FileSecurityStateConflict("artifact_security_pending")


class FileSecurityClient:
    def __init__(self, config: FileSecurityConfig) -> None:
        self.config = config

    def scan(
        self,
        source_path: Path,
        *,
        filename: str,
        reported_media_type: str,
        expected_size: int,
        expected_sha256: str,
    ) -> ScanOutcome:
        if expected_size < 0 or _SHA256_RE.fullmatch(expected_sha256) is None:
            raise FileSecurityClientError("file_security_source_invalid")
        parsed = _validated_endpoint(self.config.scanner_url)
        address, port = _resolved_private_address(parsed)
        nonce = secrets.token_urlsafe(18)
        filename_b64 = encode_filename(filename)
        mac = request_mac(
            self.config.shared_secret,
            nonce=nonce,
            expected_sha256=expected_sha256,
            size_bytes=expected_size,
            filename_b64=filename_b64,
            reported_media_type=reported_media_type,
        )
        host_header = str(parsed.hostname)
        if ":" in host_header and not host_header.startswith("["):
            host_header = f"[{host_header}]"
        host_header = f"{host_header}:{port}"
        connection = http.client.HTTPConnection(
            address,
            port,
            timeout=self.config.timeout_seconds,
        )
        digest = hashlib.sha256()
        sent = 0
        try:
            connection.putrequest(
                "POST",
                parsed.path,
                skip_host=True,
                skip_accept_encoding=True,
            )
            for key, value in (
                ("Host", host_header),
                ("Content-Type", "application/octet-stream"),
                ("Content-Length", str(expected_size)),
                ("Connection", "close"),
                ("X-KMFA-Scan-Protocol", PROTOCOL_VERSION),
                ("X-KMFA-Scan-Nonce", nonce),
                ("X-KMFA-Scan-SHA256", expected_sha256),
                ("X-KMFA-Scan-Size", str(expected_size)),
                ("X-KMFA-Scan-Filename", filename_b64),
                ("X-KMFA-Scan-Media-Type", reported_media_type),
                ("X-KMFA-Scan-MAC", mac),
            ):
                connection.putheader(key, value)
            connection.endheaders()
            with source_path.open("rb") as source:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    sent += len(chunk)
                    if sent > expected_size:
                        raise FileSecurityClientError(
                            "file_security_source_invalid"
                        )
                    digest.update(chunk)
                    connection.send(chunk)
            if sent != expected_size or digest.hexdigest() != expected_sha256:
                raise FileSecurityClientError("file_security_source_invalid")
            response = connection.getresponse()
            body = response.read(MAX_RESPONSE_BYTES + 1)
            content_type = response.getheader("Content-Type", "").split(
                ";", 1
            )[0].strip().lower()
            if (
                response.status != 200
                or content_type != "application/json"
                or len(body) > MAX_RESPONSE_BYTES
            ):
                raise FileSecurityClientError(
                    "file_security_scanner_rejected_request"
                )
            try:
                parsed_response = validate_signed_response(
                    self.config.shared_secret,
                    body,
                    expected_nonce=nonce,
                )
            except FileSecurityProtocolError as exc:
                raise FileSecurityClientError(
                    "file_security_scanner_response_invalid"
                ) from exc
        except TimeoutError as exc:
            raise FileSecurityTimeoutError(
                "file_security_scanner_timeout"
            ) from exc
        except FileSecurityError:
            raise
        except (OSError, http.client.HTTPException) as exc:
            raise FileSecurityClientError(
                "file_security_scanner_unavailable"
            ) from exc
        finally:
            connection.close()
        if (
            parsed_response["scanner_engine"] != SCANNER_ENGINE
            or parsed_response["scanner_version"] != SCANNER_VERSION
            or parsed_response["policy_version"]
            != FILE_SECURITY_POLICY_VERSION
        ):
            raise FileSecurityClientError("file_security_scanner_identity_invalid")
        return ScanOutcome(
            verdict=str(parsed_response["verdict"]),
            reason_code=str(parsed_response["reason_code"]),
            detected_media_type=str(parsed_response["detected_media_type"]),
            scanner_engine=str(parsed_response["scanner_engine"]),
            scanner_version=str(parsed_response["scanner_version"]),
            policy_version=str(parsed_response["policy_version"]),
        )


def run_security_scan_once(
    *,
    state_root: Path,
    artifact_version_id: str | None = None,
    now: datetime | None = None,
) -> SecurityRunResult | None:
    """Claim, scan, and durably complete at most one assessment."""

    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    configuration: FileSecurityConfig | None = None
    connection = open_structured_store(
        state_root / "walking_skeleton.sqlite3"
    )
    try:
        with connection.transaction():
            basic_config = FileSecurityConfig.from_environment()
            claim = FileSecurityRepository(connection).claim(
                now=current_time,
                lease_seconds=basic_config.lease_seconds,
                retry_delay_seconds=basic_config.retry_delay_seconds,
                max_attempts=basic_config.max_attempts,
                artifact_version_id=artifact_version_id,
            )
            configuration = basic_config
    except FileSecurityConfigurationError:
        # A missing scanner credential must still become a durable non-clean
        # state when an assessment can be claimed. Use safe scheduling values
        # without manufacturing scanner identity or a clean result.
        with connection.transaction():
            claim = FileSecurityRepository(connection).claim(
                now=current_time,
                lease_seconds=60,
                retry_delay_seconds=30,
                max_attempts=3,
                artifact_version_id=artifact_version_id,
            )
    finally:
        connection.close()
    if claim is None:
        return None

    outcome: ScanOutcome | None = None
    failure_state: str | None = None
    failure_reason: str | None = None
    materialized = None
    try:
        if configuration is None:
            raise FileSecurityConfigurationError(
                "file_security_configuration_invalid"
            )
        object_store = object_store_for_backend(
            state_root,
            claim.storage_backend,
        )
        materialized = object_store.materialize_verified(
            storage_key=claim.storage_key,
            expected_size=claim.source_size_bytes,
            expected_sha256=claim.source_sha256,
        )
        outcome = FileSecurityClient(configuration).scan(
            materialized.path,
            filename=claim.normalized_name,
            reported_media_type=claim.reported_media_type,
            expected_size=claim.source_size_bytes,
            expected_sha256=claim.source_sha256,
        )
    except FileSecurityTimeoutError:
        failure_state = "timed_out"
        failure_reason = "security_scanner_timeout"
    except (FileSecurityError, ObjectStorageError, OSError):
        failure_state = "scanner_error"
        failure_reason = "security_scanner_error"
    finally:
        if materialized is not None and materialized.temporary:
            try:
                materialized.path.unlink(missing_ok=True)
            except OSError:
                pass

    completed_at = _timestamp()
    connection = open_structured_store(
        state_root / "walking_skeleton.sqlite3"
    )
    try:
        with connection.transaction():
            repository = FileSecurityRepository(connection)
            if outcome is not None:
                return repository.complete(
                    claim,
                    state=outcome.verdict,
                    reason_code=outcome.reason_code,
                    detected_media_type=outcome.detected_media_type,
                    scanner_engine=outcome.scanner_engine,
                    scanner_version=outcome.scanner_version,
                    policy_version=outcome.policy_version,
                    timestamp=completed_at,
                )
            assert failure_state is not None
            assert failure_reason is not None
            return repository.complete(
                claim,
                state=failure_state,
                reason_code=failure_reason,
                detected_media_type=None,
                scanner_engine=None,
                scanner_version=None,
                policy_version=FILE_SECURITY_POLICY_VERSION,
                timestamp=completed_at,
            )
    finally:
        connection.close()


def public_file_security_contract() -> dict[str, Any]:
    enabled = file_security_enabled()
    if enabled:
        config = FileSecurityConfig.from_environment()
        timeout_seconds: float | None = config.timeout_seconds
        max_attempts: int | None = config.max_attempts
    else:
        timeout_seconds = None
        max_attempts = None
    return {
        "enabled": enabled,
        "mode": "quarantine-scan-v1" if enabled else "rollback-attachment-only",
        "scanner_process_isolated": True,
        "scanner_database_access": False,
        "scanner_object_credentials": False,
        "scanner_reachability": "verified-per-scan",
        "timeout_is_clean": False,
        "unknown_is_attachment_only": True,
        "preview_allowed": False,
        "persisted_rejected_remains_blocked_on_rollback": True,
        "policy_version": FILE_SECURITY_POLICY_VERSION,
        "timeout_seconds": timeout_seconds,
        "max_attempts": max_attempts,
    }
