"""Authenticated, bounded protocol shared by app and isolated scanner."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
from collections.abc import Mapping
from typing import Any

PROTOCOL_VERSION = "kmfa-file-security-v1"
FILE_SECURITY_POLICY_VERSION = "kmfa-upload-security-v1"
SCANNER_ENGINE = "kmfa-bounded-content-firewall"
SCANNER_VERSION = "1.0"
MAX_RESPONSE_BYTES = 64 * 1024
MAX_RISK_FLAGS = 16

_NONCE_RE = re.compile(r"^[A-Za-z0-9_-]{24}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{2,79}$")
_IDENTITY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
_MEDIA_TYPE_RE = re.compile(
    r"^[a-z0-9][a-z0-9!#$&^_.+-]{0,126}/"
    r"[a-z0-9][a-z0-9!#$&^_.+-]{0,126}$"
)
_VERDICTS = frozenset({"clean", "attachment_only", "rejected"})
_RESPONSE_KEYS = frozenset(
    {
        "schema_version",
        "nonce",
        "verdict",
        "reason_code",
        "detected_media_type",
        "scanner_engine",
        "scanner_version",
        "policy_version",
        "risk_flags",
        "archive_entries",
        "expanded_bytes",
        "response_mac",
    }
)


class FileSecurityProtocolError(RuntimeError):
    """Static protocol failure with no secret or private file data."""


def validated_shared_secret(value: str) -> bytes:
    if not (32 <= len(value) <= 256):
        raise FileSecurityProtocolError("scanner_shared_secret_invalid")
    try:
        encoded = value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise FileSecurityProtocolError(
            "scanner_shared_secret_invalid"
        ) from exc
    if any(byte < 33 or byte > 126 for byte in encoded):
        raise FileSecurityProtocolError("scanner_shared_secret_invalid")
    return encoded


def encode_filename(value: str) -> str:
    encoded = base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii")
    return encoded.rstrip("=")


def decode_filename(value: str) -> str:
    if (
        not value
        or len(value) > 1024
        or re.fullmatch(r"[A-Za-z0-9_-]+", value) is None
    ):
        raise FileSecurityProtocolError("scanner_filename_invalid")
    try:
        decoded = base64.urlsafe_b64decode(
            value + ("=" * (-len(value) % 4))
        ).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise FileSecurityProtocolError("scanner_filename_invalid") from exc
    if encode_filename(decoded) != value:
        raise FileSecurityProtocolError("scanner_filename_invalid")
    return decoded


def _validated_request_fields(
    *,
    nonce: str,
    expected_sha256: str,
    size_bytes: int,
    filename_b64: str,
    reported_media_type: str,
) -> tuple[str, str, int, str, str]:
    if _NONCE_RE.fullmatch(nonce) is None:
        raise FileSecurityProtocolError("scanner_nonce_invalid")
    if _SHA256_RE.fullmatch(expected_sha256) is None:
        raise FileSecurityProtocolError("scanner_checksum_invalid")
    if size_bytes < 0 or size_bytes > 64 * 1024 * 1024:
        raise FileSecurityProtocolError("scanner_size_invalid")
    decode_filename(filename_b64)
    if _MEDIA_TYPE_RE.fullmatch(reported_media_type) is None:
        raise FileSecurityProtocolError("scanner_media_type_invalid")
    return (
        nonce,
        expected_sha256,
        size_bytes,
        filename_b64,
        reported_media_type,
    )


def request_mac(
    secret: bytes,
    *,
    nonce: str,
    expected_sha256: str,
    size_bytes: int,
    filename_b64: str,
    reported_media_type: str,
) -> str:
    fields = _validated_request_fields(
        nonce=nonce,
        expected_sha256=expected_sha256,
        size_bytes=size_bytes,
        filename_b64=filename_b64,
        reported_media_type=reported_media_type,
    )
    payload = ("\n".join((PROTOCOL_VERSION, *(str(field) for field in fields))))
    return hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_request_mac(
    secret: bytes,
    *,
    supplied_mac: str,
    nonce: str,
    expected_sha256: str,
    size_bytes: int,
    filename_b64: str,
    reported_media_type: str,
) -> None:
    if _SHA256_RE.fullmatch(supplied_mac) is None:
        raise FileSecurityProtocolError("scanner_request_auth_invalid")
    expected = request_mac(
        secret,
        nonce=nonce,
        expected_sha256=expected_sha256,
        size_bytes=size_bytes,
        filename_b64=filename_b64,
        reported_media_type=reported_media_type,
    )
    if not hmac.compare_digest(expected, supplied_mac):
        raise FileSecurityProtocolError("scanner_request_auth_invalid")


def _canonical_response(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def signed_response(
    secret: bytes,
    *,
    nonce: str,
    verdict: str,
    reason_code: str,
    detected_media_type: str,
    scanner_engine: str,
    scanner_version: str,
    policy_version: str,
    risk_flags: tuple[str, ...],
    archive_entries: int,
    expanded_bytes: int,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": PROTOCOL_VERSION,
        "nonce": nonce,
        "verdict": verdict,
        "reason_code": reason_code,
        "detected_media_type": detected_media_type,
        "scanner_engine": scanner_engine,
        "scanner_version": scanner_version,
        "policy_version": policy_version,
        "risk_flags": list(risk_flags),
        "archive_entries": archive_entries,
        "expanded_bytes": expanded_bytes,
    }
    _validate_response_fields(payload)
    payload["response_mac"] = hmac.new(
        secret,
        _canonical_response(payload),
        hashlib.sha256,
    ).hexdigest()
    return payload


def _validate_response_fields(payload: Mapping[str, Any]) -> None:
    if payload.get("schema_version") != PROTOCOL_VERSION:
        raise FileSecurityProtocolError("scanner_response_invalid")
    if _NONCE_RE.fullmatch(str(payload.get("nonce", ""))) is None:
        raise FileSecurityProtocolError("scanner_response_invalid")
    if payload.get("verdict") not in _VERDICTS:
        raise FileSecurityProtocolError("scanner_response_invalid")
    for key in ("reason_code",):
        if _CODE_RE.fullmatch(str(payload.get(key, ""))) is None:
            raise FileSecurityProtocolError("scanner_response_invalid")
    if (
        _MEDIA_TYPE_RE.fullmatch(
            str(payload.get("detected_media_type", ""))
        )
        is None
    ):
        raise FileSecurityProtocolError("scanner_response_invalid")
    for key in ("scanner_engine", "scanner_version", "policy_version"):
        if _IDENTITY_RE.fullmatch(str(payload.get(key, ""))) is None:
            raise FileSecurityProtocolError("scanner_response_invalid")
    flags = payload.get("risk_flags")
    if (
        type(flags) is not list
        or len(flags) > MAX_RISK_FLAGS
        or any(
            type(flag) is not str or _CODE_RE.fullmatch(flag) is None
            for flag in flags
        )
        or len(set(flags)) != len(flags)
    ):
        raise FileSecurityProtocolError("scanner_response_invalid")
    for key in ("archive_entries", "expanded_bytes"):
        value = payload.get(key)
        if type(value) is not int or value < 0 or value > 2**40:
            raise FileSecurityProtocolError("scanner_response_invalid")


def validate_signed_response(
    secret: bytes,
    body: bytes,
    *,
    expected_nonce: str,
) -> dict[str, Any]:
    if not body or len(body) > MAX_RESPONSE_BYTES:
        raise FileSecurityProtocolError("scanner_response_invalid")
    try:
        parsed = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FileSecurityProtocolError("scanner_response_invalid") from exc
    if type(parsed) is not dict or frozenset(parsed) != _RESPONSE_KEYS:
        raise FileSecurityProtocolError("scanner_response_invalid")
    supplied_mac = parsed.pop("response_mac")
    if (
        type(supplied_mac) is not str
        or _SHA256_RE.fullmatch(supplied_mac) is None
    ):
        raise FileSecurityProtocolError("scanner_response_invalid")
    _validate_response_fields(parsed)
    if parsed["nonce"] != expected_nonce:
        raise FileSecurityProtocolError("scanner_response_invalid")
    expected_mac = hmac.new(
        secret,
        _canonical_response(parsed),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_mac, supplied_mac):
        raise FileSecurityProtocolError("scanner_response_invalid")
    parsed["response_mac_verified"] = True
    return parsed
