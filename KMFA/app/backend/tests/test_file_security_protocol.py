"""Authenticated scanner protocol, tamper, and replay contracts."""

from __future__ import annotations

import hashlib
import http.client
import json
import secrets
import socket
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from app.file_security import (
    FileSecurityClient,
    FileSecurityConfig,
    FileSecurityTimeoutError,
)
from app.file_security_protocol import (
    PROTOCOL_VERSION,
    FileSecurityProtocolError,
    encode_filename,
    request_mac,
    signed_response,
    validate_signed_response,
    validated_shared_secret,
)
from app.file_security_scanner_service import app
from fastapi.testclient import TestClient

SECRET_TEXT = "p62-test-shared-secret-32-bytes-minimum"
SECRET = validated_shared_secret(SECRET_TEXT)


@pytest.fixture
def scanner_server(monkeypatch):
    monkeypatch.setenv("KMFA_FILE_SCANNER_SHARED_SECRET", SECRET_TEXT)
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = int(probe.getsockname()[1])
    probe.close()
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_level="critical",
            access_log=False,
            lifespan="off",
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.01)
    assert server.started
    try:
        yield port
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        assert not thread.is_alive()


def _request_headers(
    payload: bytes,
    *,
    nonce: str,
    request_secret: bytes = SECRET,
) -> dict[str, str]:
    digest = hashlib.sha256(payload).hexdigest()
    filename = encode_filename("legal-fixture.txt")
    media_type = "text/plain"
    return {
        "Content-Type": "application/octet-stream",
        "Content-Length": str(len(payload)),
        "X-KMFA-Scan-Protocol": PROTOCOL_VERSION,
        "X-KMFA-Scan-Nonce": nonce,
        "X-KMFA-Scan-SHA256": digest,
        "X-KMFA-Scan-Size": str(len(payload)),
        "X-KMFA-Scan-Filename": filename,
        "X-KMFA-Scan-Media-Type": media_type,
        "X-KMFA-Scan-MAC": request_mac(
            request_secret,
            nonce=nonce,
            expected_sha256=digest,
            size_bytes=len(payload),
            filename_b64=filename,
            reported_media_type=media_type,
        ),
    }


def test_signed_response_rejects_tamper_and_nonce_substitution():
    nonce = secrets.token_urlsafe(18)
    response = signed_response(
        SECRET,
        nonce=nonce,
        verdict="clean",
        reason_code="security_scan_clean",
        detected_media_type="text/plain",
        scanner_engine="kmfa-bounded-content-firewall",
        scanner_version="1.0",
        policy_version="kmfa-upload-security-v1",
        risk_flags=(),
        archive_entries=0,
        expanded_bytes=0,
    )
    encoded = json.dumps(response, sort_keys=True).encode()
    assert validate_signed_response(
        SECRET,
        encoded,
        expected_nonce=nonce,
    )["response_mac_verified"]

    tampered = dict(response)
    tampered["verdict"] = "rejected"
    try:
        validate_signed_response(
            SECRET,
            json.dumps(tampered).encode(),
            expected_nonce=nonce,
        )
    except FileSecurityProtocolError as exc:
        assert str(exc) == "scanner_response_invalid"
    else:
        raise AssertionError("tampered response was accepted")

    try:
        validate_signed_response(
            SECRET,
            encoded,
            expected_nonce=secrets.token_urlsafe(18),
        )
    except FileSecurityProtocolError as exc:
        assert str(exc) == "scanner_response_invalid"
    else:
        raise AssertionError("response nonce substitution was accepted")


def test_scanner_service_authenticates_body_and_rejects_replay(monkeypatch):
    monkeypatch.setenv("KMFA_FILE_SCANNER_SHARED_SECRET", SECRET_TEXT)
    client = TestClient(app)
    payload = b"bounded scanner legal text fixture\n"
    nonce = secrets.token_urlsafe(18)
    headers = _request_headers(payload, nonce=nonce)

    first = client.post("/scan", content=payload, headers=headers)
    assert first.status_code == 200, first.text
    parsed = validate_signed_response(
        SECRET,
        first.content,
        expected_nonce=nonce,
    )
    assert parsed["verdict"] == "clean"
    assert parsed["detected_media_type"] == "text/plain"

    replay = client.post("/scan", content=payload, headers=headers)
    assert replay.status_code == 401
    assert replay.json() == {"detail": "scanner_request_invalid"}

    new_nonce = secrets.token_urlsafe(18)
    tampered_headers = _request_headers(payload, nonce=new_nonce)
    tampered_headers["X-KMFA-Scan-SHA256"] = "0" * 64
    tampered = client.post(
        "/scan",
        content=payload,
        headers=tampered_headers,
    )
    assert tampered.status_code == 401


def test_scanner_service_has_no_public_docs_and_fails_closed_without_secret(
    monkeypatch,
):
    monkeypatch.delenv("KMFA_FILE_SCANNER_SHARED_SECRET", raising=False)
    client = TestClient(app)
    assert client.get("/healthz").status_code == 503
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/docs").status_code == 404


def test_private_client_streams_and_verifies_real_signed_response(
    scanner_server: int,
    tmp_path: Path,
):
    payload = b"real private protocol fixture\n"
    source = tmp_path / "source.bin"
    source.write_bytes(payload)
    client = FileSecurityClient(
        FileSecurityConfig(
            scanner_url=f"http://127.0.0.1:{scanner_server}/scan",
            shared_secret=SECRET,
            timeout_seconds=1,
            lease_seconds=2,
            retry_delay_seconds=0,
            max_attempts=3,
        )
    )
    result = client.scan(
        source,
        filename="protocol.txt",
        reported_media_type="text/plain",
        expected_size=len(payload),
        expected_sha256=hashlib.sha256(payload).hexdigest(),
    )
    assert result.verdict == "clean"
    assert result.reason_code == "security_scan_clean"


def test_private_client_timeout_never_returns_clean(
    scanner_server: int,
    tmp_path: Path,
    monkeypatch,
):
    payload = b"deterministic parser timeout fixture"
    digest = hashlib.sha256(payload).hexdigest()

    def inject_timeout(_connection):
        raise TimeoutError("synthetic scanner timeout")

    monkeypatch.setattr(
        http.client.HTTPConnection,
        "getresponse",
        inject_timeout,
    )
    source = tmp_path / "timeout.bin"
    source.write_bytes(payload)
    client = FileSecurityClient(
        FileSecurityConfig(
            scanner_url=f"http://127.0.0.1:{scanner_server}/scan",
            shared_secret=SECRET,
            timeout_seconds=0.05,
            lease_seconds=1,
            retry_delay_seconds=0,
            max_attempts=3,
        )
    )
    with pytest.raises(FileSecurityTimeoutError):
        client.scan(
            source,
            filename="timeout.txt",
            reported_media_type="text/plain",
            expected_size=len(payload),
            expected_sha256=digest,
        )
