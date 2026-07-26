"""Credential-minimal private scanner service for KMFA S06/P6.2."""

from __future__ import annotations

import hashlib
import os
import tempfile
import threading
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.requests import ClientDisconnect

from .file_security_policy import (
    ENGINE_NAME,
    ENGINE_VERSION,
    MAX_SCAN_BYTES,
    POLICY_VERSION,
    FileSecurityPolicyError,
    inspect_file,
)
from .file_security_protocol import (
    PROTOCOL_VERSION,
    FileSecurityProtocolError,
    decode_filename,
    signed_response,
    validated_shared_secret,
    verify_request_mac,
)

SCANNER_SHARED_SECRET_ENV = "KMFA_FILE_SCANNER_SHARED_SECRET"
NONCE_TTL_SECONDS = 300.0
MAX_NONCES = 10_000

app = FastAPI(
    title="KMFA private file scanner",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

_nonce_lock = threading.Lock()
_seen_nonces: dict[str, float] = {}


def _error(code: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        {"detail": code},
        status_code=status_code,
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


def _shared_secret() -> bytes:
    return validated_shared_secret(os.environ.get(SCANNER_SHARED_SECRET_ENV, ""))


def _register_nonce(nonce: str) -> None:
    current = time.monotonic()
    with _nonce_lock:
        expired = [
            value
            for value, seen_at in _seen_nonces.items()
            if seen_at + NONCE_TTL_SECONDS <= current
        ]
        for value in expired:
            _seen_nonces.pop(value, None)
        if nonce in _seen_nonces:
            raise FileSecurityProtocolError("scanner_request_replayed")
        if len(_seen_nonces) >= MAX_NONCES:
            oldest = min(_seen_nonces, key=_seen_nonces.__getitem__)
            _seen_nonces.pop(oldest, None)
        _seen_nonces[nonce] = current


def _header(request: Request, name: str) -> str:
    value = request.headers.get(name, "").strip()
    if not value or len(value) > 2048:
        raise FileSecurityProtocolError("scanner_request_invalid")
    return value


@app.get("/healthz")
def scanner_health() -> JSONResponse:
    try:
        _shared_secret()
    except FileSecurityProtocolError:
        return _error("scanner_not_configured", 503)
    return JSONResponse(
        {
            "healthy": True,
            "schema_version": PROTOCOL_VERSION,
            "database_access": False,
            "object_credentials": False,
        },
        headers={"Cache-Control": "no-store"},
    )


@app.post("/scan")
async def scan_file(request: Request) -> JSONResponse:
    temporary_path: Path | None = None
    try:
        secret = _shared_secret()
        if request.headers.get("content-encoding", "identity").strip().lower() not in {
            "",
            "identity",
        }:
            return _error("scanner_content_encoding_invalid", 415)
        if (
            request.headers.get("content-type", "")
            .split(";", 1)[0]
            .strip()
            .lower()
            != "application/octet-stream"
        ):
            return _error("scanner_content_type_invalid", 415)

        protocol = _header(request, "x-kmfa-scan-protocol")
        nonce = _header(request, "x-kmfa-scan-nonce")
        expected_sha256 = _header(request, "x-kmfa-scan-sha256")
        size_text = _header(request, "x-kmfa-scan-size")
        filename_b64 = _header(request, "x-kmfa-scan-filename")
        reported_media_type = _header(request, "x-kmfa-scan-media-type")
        supplied_mac = _header(request, "x-kmfa-scan-mac")
        content_length_text = _header(request, "content-length")
        if protocol != PROTOCOL_VERSION:
            return _error("scanner_protocol_invalid", 400)
        try:
            expected_size = int(size_text)
            content_length = int(content_length_text)
        except ValueError:
            return _error("scanner_size_invalid", 400)
        if (
            expected_size != content_length
            or expected_size < 0
            or expected_size > MAX_SCAN_BYTES
        ):
            return _error("scanner_size_invalid", 413)
        verify_request_mac(
            secret,
            supplied_mac=supplied_mac,
            nonce=nonce,
            expected_sha256=expected_sha256,
            size_bytes=expected_size,
            filename_b64=filename_b64,
            reported_media_type=reported_media_type,
        )
        original_name = decode_filename(filename_b64)
        _register_nonce(nonce)

        descriptor, temporary_name = tempfile.mkstemp(
            prefix="kmfa-scan-",
            suffix=".part",
        )
        temporary_path = Path(temporary_name)
        os.fchmod(descriptor, 0o600)
        digest = hashlib.sha256()
        received = 0
        with os.fdopen(descriptor, "wb") as output:
            async for chunk in request.stream():
                if not chunk:
                    continue
                received += len(chunk)
                if received > expected_size or received > MAX_SCAN_BYTES:
                    return _error("scanner_size_invalid", 413)
                digest.update(chunk)
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        if received != expected_size or digest.hexdigest() != expected_sha256:
            return _error("scanner_source_identity_invalid", 422)

        decision = inspect_file(
            temporary_path,
            original_name=original_name,
            reported_media_type=reported_media_type,
            expected_size=expected_size,
            expected_sha256=expected_sha256,
        )
        payload = signed_response(
            secret,
            nonce=nonce,
            verdict=decision.verdict,
            reason_code=decision.reason_code,
            detected_media_type=decision.detected_media_type,
            scanner_engine=ENGINE_NAME,
            scanner_version=ENGINE_VERSION,
            policy_version=POLICY_VERSION,
            risk_flags=decision.risk_flags,
            archive_entries=decision.archive_entries,
            expanded_bytes=decision.expanded_bytes,
        )
        return JSONResponse(
            payload,
            headers={
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )
    except ClientDisconnect:
        return _error("scanner_client_disconnected", 400)
    except FileSecurityProtocolError:
        return _error("scanner_request_invalid", 401)
    except FileSecurityPolicyError:
        return _error("scanner_policy_error", 500)
    except (OSError, RuntimeError):
        return _error("scanner_internal_error", 500)
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
