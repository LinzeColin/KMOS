"""Fail-closed Cloudflare Access boundary for KMFA private operations.

The public application shell lives at the root domain.  Existing operational
APIs and diagnostics stay behind path-specific Cloudflare Access applications,
and this middleware independently verifies the Access assertion at the origin.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlsplit

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWTError
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import Headers
from starlette.responses import JSONResponse

PRIVATE_PATH_ROOTS = ("/api", "/ops")
_DISABLED = frozenset({"0", "false", "no", "off"})


class AccessConfigurationError(RuntimeError):
    """The production guard is enabled but its trusted settings are invalid."""


class AccessAssertionDenied(RuntimeError):
    """The caller did not present a valid Access assertion."""


class AccessKeyServiceUnavailable(RuntimeError):
    """The trusted Access key set could not be reached."""


@dataclass(frozen=True)
class AccessSettings:
    issuer: str
    audiences: tuple[str, ...]

    @property
    def jwks_uri(self) -> str:
        return f"{self.issuer}/cdn-cgi/access/certs"


def private_access_required() -> bool:
    """Return whether the origin guard is enabled.

    An unset value is the explicit local-development mode.  Any non-empty,
    unrecognised value enables the guard so a typo cannot silently make a
    production API public.
    """

    raw = os.environ.get("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", "").strip().lower()
    if not raw or raw in _DISABLED:
        return False
    return True


def is_private_path(path: str) -> bool:
    return any(
        path == root or path.startswith(f"{root}/") for root in PRIVATE_PATH_ROOTS
    )


def load_access_settings() -> AccessSettings:
    raw_domain = os.environ.get("KMFA_CLOUDFLARE_ACCESS_TEAM_DOMAIN", "").strip()
    if raw_domain and "://" not in raw_domain:
        raw_domain = f"https://{raw_domain}"
    try:
        parsed = urlsplit(raw_domain)
        hostname = (parsed.hostname or "").lower()
        port = parsed.port
    except ValueError as exc:
        raise AccessConfigurationError("invalid Cloudflare Access team domain") from exc
    if (
        parsed.scheme != "https"
        or not hostname.endswith(".cloudflareaccess.com")
        or hostname == ".cloudflareaccess.com"
        or parsed.username
        or parsed.password
        or port
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise AccessConfigurationError("invalid Cloudflare Access team domain")

    raw_audiences = os.environ.get("KMFA_CLOUDFLARE_ACCESS_AUD", "")
    audiences = tuple(
        dict.fromkeys(x for x in re.split(r"[,\s]+", raw_audiences.strip()) if x)
    )
    if not audiences:
        raise AccessConfigurationError("missing Cloudflare Access audience")
    if any(len(item) > 256 for item in audiences):
        raise AccessConfigurationError("invalid Cloudflare Access audience")

    return AccessSettings(
        issuer=f"https://{hostname}",
        audiences=audiences,
    )


@lru_cache(maxsize=8)
def _jwk_client(jwks_uri: str) -> PyJWKClient:
    # Access rotates signing keys.  PyJWKClient refreshes the issuer JWKS and
    # caches the set; a short timeout keeps an upstream outage from pinning a
    # request worker indefinitely.
    return PyJWKClient(jwks_uri, cache_keys=True, timeout=5)


def verify_access_assertion(token: str, settings: AccessSettings) -> dict:
    try:
        signing_key = _jwk_client(settings.jwks_uri).get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=list(settings.audiences),
            issuer=settings.issuer,
            options={"require": ["exp", "iss", "aud"]},
        )
    except PyJWKClientConnectionError as exc:
        raise AccessKeyServiceUnavailable from exc
    except (PyJWTError, ValueError, TypeError) as exc:
        raise AccessAssertionDenied from exc


def _blocked(status_code: int, code: str) -> JSONResponse:
    return JSONResponse(
        {"detail": code},
        status_code=status_code,
        headers={"Cache-Control": "no-store"},
    )


class PrivateOperationsAccessMiddleware:
    """Verify Access JWTs for ``/api`` and ``/ops`` when production enables it."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if (
            scope.get("type") != "http"
            or not private_access_required()
            or not is_private_path(scope.get("path", ""))
        ):
            await self.app(scope, receive, send)
            return

        try:
            settings = load_access_settings()
        except AccessConfigurationError:
            await _blocked(503, "private_operations_unavailable")(scope, receive, send)
            return

        assertion = Headers(scope=scope).get("cf-access-jwt-assertion", "").strip()
        if not assertion:
            await _blocked(403, "cloudflare_access_required")(scope, receive, send)
            return

        try:
            await run_in_threadpool(verify_access_assertion, assertion, settings)
        except AccessKeyServiceUnavailable:
            await _blocked(503, "private_operations_unavailable")(scope, receive, send)
            return
        except AccessAssertionDenied:
            await _blocked(403, "cloudflare_access_required")(scope, receive, send)
            return

        await self.app(scope, receive, send)
