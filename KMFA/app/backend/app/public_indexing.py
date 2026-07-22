"""Fail-closed search-index boundary for the anonymous public surface.

Only paths in PUBLIC_INDEX_PATHS may become search-index candidates. This
module is deliberately independent from the later Publication Gate: until that
gate emits an approved public snapshot, adding a route elsewhere cannot
silently add it to robots or the sitemap.
"""

from __future__ import annotations

import os

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

CANONICAL_ORIGIN = "https://kmfa.linzezhang.com"
PUBLIC_INDEX_PATHS = ("/",)
CONTROL_PATHS = frozenset({"/robots.txt", "/sitemap.xml"})
NO_INDEX = "noindex, nofollow, noarchive"
TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def public_indexing_enabled() -> bool:
    """Return whether the approved public-root index candidate is promoted.

    The production-safe default is hold (0). Promotion is an explicit,
    reversible deployment decision after the privacy and crawler canaries pass.
    """

    return (
        os.environ.get("KMFA_PUBLIC_INDEXING_ENABLED", "0").strip().lower()
        in TRUE_VALUES
    )


def index_mode() -> str:
    return "public-root" if public_indexing_enabled() else "hold"


def robots_body() -> str:
    if not public_indexing_enabled():
        return "User-agent: *\nDisallow: /\n"
    return (
        "User-agent: *\n"
        "Disallow: /\n"
        "Allow: /$\n"
        "Allow: /assets/\n"
        "Allow: /robots.txt\n"
        "Allow: /sitemap.xml\n"
        f"Sitemap: {CANONICAL_ORIGIN}/sitemap.xml\n"
    )


def sitemap_body() -> str:
    locations = PUBLIC_INDEX_PATHS if public_indexing_enabled() else ()
    rows = "".join(
        f"  <url><loc>{CANONICAL_ORIGIN}{path}</loc></url>\n" for path in locations
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{rows}"
        "</urlset>\n"
    )


def control_headers() -> dict[str, str]:
    return {
        "Cache-Control": "public, no-cache, must-revalidate",
        "X-KMFA-Index-Mode": index_mode(),
    }


class PublicIndexBoundaryMiddleware:
    """Attach crawler and cache controls to every response, including errors."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = str(scope.get("path") or "")
        indexing_enabled = public_indexing_enabled()

        async def send_with_boundary(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                status = int(message.get("status", 500))
                response_ok = 200 <= status < 300
                headers["X-KMFA-Index-Mode"] = (
                    "public-root" if indexing_enabled else "hold"
                )
                is_indexable_root = (
                    path in PUBLIC_INDEX_PATHS and indexing_enabled and response_ok
                )
                is_successful_control = path in CONTROL_PATHS and response_ok
                if not is_indexable_root and not is_successful_control:
                    headers["X-Robots-Tag"] = NO_INDEX
                    # Hashed assets remain publicly immutable so the approved
                    # root can render. Only a successful asset response may
                    # retain that cache policy; every error and every other
                    # non-public response is fail-closed no-store.
                    if not (path.startswith("/assets/") and response_ok):
                        existing_cache = headers.get("Cache-Control", "").lower()
                        if "no-store" not in existing_cache:
                            headers["Cache-Control"] = "private, no-store"
            await send(message)

        await self.app(scope, receive, send_with_boundary)
