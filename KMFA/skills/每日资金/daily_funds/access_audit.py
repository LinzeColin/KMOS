"""Values-free classification for a Cloudflare Access capability audit.

The daily-funds fixed history probe is intentionally protected by Cloudflare
Access.  A future controlled service-auth bridge must first prove that the
repository-held Cloudflare API credential can *read* the Access control plane.
This module processes those API replies only from temporary runner files and
returns a finite, non-sensitive result.  It never serializes a response field,
HTTP body, identifier, URL, error message, or credential.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping


ACCESS_AUDIT_SCHEMA = "kmfa.daily_funds.cloudflare_access_audit.v1"
CHECKS = (
    "token_verify",
    "apps_read",
    "service_tokens_read",
    "policies_read",
)
_EXPECTED_RESULT_TYPES: dict[str, type[object]] = {
    "token_verify": dict,
    "apps_read": list,
    "service_tokens_read": list,
    "policies_read": list,
}
_HTTP_STATUS = re.compile(r"(?:[1-5][0-9]{2}|000)\Z")
_MAX_RESPONSE_BYTES = 512 * 1024


def _safe_status(value: object) -> str | None:
    candidate = value if isinstance(value, str) else str(value)
    return candidate if _HTTP_STATUS.fullmatch(candidate) else None


def _curl_succeeded(value: object) -> bool:
    try:
        return int(value) == 0
    except (TypeError, ValueError):
        return False


def _read_payload(path: str | Path) -> tuple[Mapping[str, Any] | None, str | None]:
    """Read one bounded response without returning response text to callers."""

    try:
        with Path(path).open("rb") as handle:
            raw = handle.read(_MAX_RESPONSE_BYTES + 1)
    except OSError:
        return None, "INPUT_UNAVAILABLE"
    if len(raw) > _MAX_RESPONSE_BYTES:
        return None, "RESPONSE_TOO_LARGE"
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, "INVALID_RESPONSE"
    return (payload, None) if isinstance(payload, Mapping) else (None, "INVALID_RESPONSE")


def classify_access_response(
    check: str,
    path: str | Path,
    *,
    http_status: object,
    curl_exit: object,
) -> str:
    """Classify a single read-only API call using a finite public vocabulary."""

    if check not in _EXPECTED_RESULT_TYPES:
        raise ValueError("unsupported Cloudflare Access audit check")
    if not _curl_succeeded(curl_exit):
        return "TRANSPORT_FAILED"
    status = _safe_status(http_status)
    if status is None:
        return "TRANSPORT_FAILED"
    if status in {"401", "403"}:
        return "DENIED"
    if not status.startswith("2"):
        return "UNAVAILABLE"
    payload, read_error = _read_payload(path)
    if read_error is not None:
        return read_error
    assert payload is not None
    if payload.get("success") is not True:
        return "INVALID_RESPONSE"
    if not isinstance(payload.get("result"), _EXPECTED_RESULT_TYPES[check]):
        return "INVALID_RESPONSE"
    return "OK"


def summarize_access_audit(
    responses: Mapping[str, tuple[str | Path, object, object]],
) -> dict[str, object]:
    """Return the complete values-free result for the four GET-only checks."""

    checks: dict[str, str] = {}
    for check in CHECKS:
        path, http_status, curl_exit = responses.get(check, ("", "000", 1))
        checks[check] = classify_access_response(
            check,
            path,
            http_status=http_status,
            curl_exit=curl_exit,
        )
    return {
        "schema_version": ACCESS_AUDIT_SCHEMA,
        "checks": checks,
        "read_capability": "VERIFIED" if all(value == "OK" for value in checks.values()) else "NOT_VERIFIED",
        "request_scope": "GET_ONLY_NO_CLOUDFLARE_MUTATION",
        "service_auth_write_scope": "UNKNOWN_NOT_TESTED",
    }
