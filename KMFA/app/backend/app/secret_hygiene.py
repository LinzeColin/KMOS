"""P4.3 fail-closed secret redaction and browser exfiltration boundary."""

from __future__ import annotations

import logging
import re
import threading
import traceback
from typing import Any
from urllib.parse import unquote, urlsplit

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REDACTED = "[REDACTED_KMFA_CAPABILITY]"
SECRET_HYGIENE_HEADER = "enforced"
WALKING_API_PREFIX = "/public-api/walking-skeleton/v1"
SESSION_COOKIE_NAME = "__Secure-kmfa_session"
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

_CAPABILITY_RE = re.compile(r"\bkmfa-(?:r1|a1)-[A-Za-z0-9_-]{20,128}\b")
_URL_ENCODED_CAPABILITY_RE = re.compile(
    r"(?i)kmfa(?:-|%2d)(?:r1|a1)(?:-|%2d)"
    r"(?:[A-Za-z0-9_.~-]|%[0-9a-f]{2}){20,384}"
)
_BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{16,2048}")
_COOKIE_RE = re.compile(
    r"(?i)(?P<name>__Secure-kmfa_session|__Host-kmfa_device)"
    r"=[A-Za-z0-9._~-]{16,2048}"
)
_SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"""(?ix)
    (?P<prefix>
      ["']?(?:workspace_secret|recovery_code|access_token)["']?
      \s*[:=]\s*["']?
    )
    (?P<value>[^"',}\s]{8,2048})
    """
)
_INSTALL_LOCK = threading.Lock()

CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'self'",
        "base-uri 'none'",
        "object-src 'none'",
        "frame-src 'none'",
        "frame-ancestors 'none'",
        "form-action 'self'",
        "connect-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
        "font-src 'self'",
        "media-src 'none'",
        "worker-src 'none'",
        "manifest-src 'self'",
    )
)

SECURITY_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": (
        "camera=(), microphone=(), geolocation=(), payment=(), usb=(), "
        "serial=(), bluetooth=(), browsing-topics=()"
    ),
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-KMFA-Secret-Hygiene": SECRET_HYGIENE_HEADER,
}


def redact_secrets(value: Any) -> str:
    """Return a log-safe string without KMFA capabilities or bearer material."""

    text = str(value)
    text = _URL_ENCODED_CAPABILITY_RE.sub(REDACTED, text)
    text = _CAPABILITY_RE.sub(REDACTED, text)
    # Repeated percent encoding has no safe useful logging representation.
    # If decoding still reveals a capability, discard the whole record text.
    if contains_capability(text):
        text = REDACTED
    text = _BEARER_RE.sub(f"Bearer {REDACTED}", text)
    text = _COOKIE_RE.sub(
        lambda match: f"{match.group('name')}={REDACTED}",
        text,
    )
    return _SENSITIVE_ASSIGNMENT_RE.sub(
        lambda match: f"{match.group('prefix')}{REDACTED}",
        text,
    )


def contains_capability(value: str) -> bool:
    candidate = value
    for _ in range(5):
        if _CAPABILITY_RE.search(candidate):
            return True
        decoded = unquote(candidate)
        if decoded == candidate:
            break
        candidate = decoded
    return bool(
        _CAPABILITY_RE.search(candidate)
        or _URL_ENCODED_CAPABILITY_RE.search(value)
    )


def _redact_record(record: logging.LogRecord) -> logging.LogRecord:
    try:
        message = record.getMessage()
    except Exception:
        message = str(record.msg)
    record.msg = redact_secrets(message)
    record.args = ()
    if record.exc_info:
        rendered = "".join(traceback.format_exception(*record.exc_info))
        record.exc_text = redact_secrets(rendered)
        record.exc_info = None
    elif record.exc_text:
        record.exc_text = redact_secrets(record.exc_text)
    return record


class SecretRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        _redact_record(record)
        return True


def install_secret_redaction() -> None:
    """Install one process-wide record factory before any request is logged."""

    with _INSTALL_LOCK:
        current = logging.getLogRecordFactory()
        if getattr(current, "_kmfa_secret_redaction", False):
            return

        def redacting_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
            return _redact_record(current(*args, **kwargs))

        setattr(redacting_factory, "_kmfa_secret_redaction", True)
        logging.setLogRecordFactory(redacting_factory)


def _append_vary_cookie(headers: MutableHeaders) -> None:
    values = [
        value.strip()
        for value in headers.get("Vary", "").split(",")
        if value.strip()
    ]
    if not any(value.lower() == "cookie" for value in values):
        values.append("Cookie")
    headers["Vary"] = ", ".join(values)


def _same_origin(scope: Scope, headers: Headers) -> bool:
    origin = headers.get("origin", "")
    host = headers.get("host", "")
    if not origin or not host:
        return False
    parsed = urlsplit(origin)
    return (
        parsed.scheme.lower() == str(scope.get("scheme") or "").lower()
        and parsed.netloc.lower() == host.lower()
    )


def _blocked_response(detail: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        {"detail": detail},
        status_code=status_code,
        headers={
            **SECURITY_HEADERS,
            "Cache-Control": "private, no-store",
            "Pragma": "no-cache",
            "Vary": "Cookie",
            "X-Robots-Tag": "noindex, nofollow, noarchive",
        },
    )


class SecretHygieneMiddleware:
    """Reject capability-bearing URLs/Referers and attach anti-exfiltration headers."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        install_secret_redaction()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = str(scope.get("path") or "")
        raw_path = bytes(scope.get("raw_path") or b"").decode(
            "latin-1",
            errors="replace",
        )
        raw_query = bytes(scope.get("query_string") or b"").decode(
            "latin-1",
            errors="replace",
        )
        headers = Headers(scope=scope)
        referer = headers.get("referer", "")
        if (
            contains_capability(path)
            or contains_capability(raw_path)
            or contains_capability(raw_query)
            or contains_capability(referer)
        ):
            response = _blocked_response("secret_in_url_rejected", 400)
            await response(scope, receive, send)
            return

        has_session_cookie = (
            f"{SESSION_COOKIE_NAME}=" in headers.get("cookie", "")
        )
        if (
            str(scope.get("method") or "").upper() in UNSAFE_METHODS
            and has_session_cookie
            and not _same_origin(scope, headers)
        ):
            response = _blocked_response(
                "cross_origin_session_request_rejected",
                403,
            )
            await response(scope, receive, send)
            return

        async def send_with_hygiene(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in SECURITY_HEADERS.items():
                    if name not in headers:
                        headers[name] = value
                if path.startswith(WALKING_API_PREFIX):
                    _append_vary_cookie(headers)
            await send(message)

        await self.app(scope, receive, send_with_hygiene)
