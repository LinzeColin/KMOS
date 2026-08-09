"""Strict helpers for the Owner-approved public KMFA dashboard boundary.

The Cloudflare API replies stay in a GitHub Actions runner's private temporary
directory.  This module only selects the exact KMFA applications that cover
the dashboard's public routes and emits a fixed Bypass-policy payload.  It
never makes HTTP calls and never prints provider identifiers or credentials.
"""

from __future__ import annotations

import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit


PUBLIC_DASHBOARD_ACCESS_SCHEMA = "kmfa.public_dashboard_access.v1"
PUBLIC_DASHBOARD_HOST = "kmfa.linzezhang.com"
PUBLIC_DASHBOARD_BYPASS_POLICY_NAME = "kmfa-public-dashboard-owner-override"
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_TARGET_ROOTS = (
    "/api",
    "/ops",
    "/project-cost",
    "/项目成本",
    "/public-api/项目成本",
    "/public-api/项目成本表",
)
_MAX_RESPONSE_BYTES = 512 * 1024


class PublicDashboardAccessError(ValueError):
    """A provider response cannot safely drive the public-boundary change."""


def _read_json(path: str | Path) -> Any:
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        raise PublicDashboardAccessError("response unavailable") from exc
    if len(raw) > _MAX_RESPONSE_BYTES:
        raise PublicDashboardAccessError("response too large")
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublicDashboardAccessError("response invalid") from exc


def _single_page_result(payload: object) -> list[Mapping[str, Any]]:
    if not isinstance(payload, Mapping) or payload.get("success") is not True:
        raise PublicDashboardAccessError("provider response invalid")
    result = payload.get("result")
    if not isinstance(result, list) or not all(isinstance(item, Mapping) for item in result):
        raise PublicDashboardAccessError("provider list invalid")
    info = payload.get("result_info")
    if info is not None:
        if not isinstance(info, Mapping) or info.get("total_pages") not in (None, 0, 1):
            raise PublicDashboardAccessError("provider list incomplete")
        if info.get("cursor") not in (None, ""):
            raise PublicDashboardAccessError("provider list incomplete")
    return list(result)


def _parse_public_uri(value: object) -> tuple[str, str]:
    if not isinstance(value, str) or not value or len(value) > 256:
        raise PublicDashboardAccessError("application destination invalid")
    candidate = value.strip()
    try:
        parsed = urlsplit(candidate if "://" in candidate else f"https://{candidate}")
        port = parsed.port
    except ValueError as exc:
        raise PublicDashboardAccessError("application destination invalid") from exc
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.query
        or parsed.fragment
    ):
        raise PublicDashboardAccessError("application destination invalid")
    path = parsed.path or "/"
    if not path.startswith("/") or "//" in path or "\\" in path:
        raise PublicDashboardAccessError("application destination invalid")
    return parsed.hostname.lower().rstrip("."), path


def _application_destinations(application: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    destinations = application.get("destinations")
    if destinations is not None:
        if not isinstance(destinations, list) or not destinations:
            raise PublicDashboardAccessError("application destinations invalid")
        destinations_out: list[tuple[str, str]] = []
        for destination in destinations:
            if not isinstance(destination, Mapping) or destination.get("type") != "public":
                raise PublicDashboardAccessError("application destinations invalid")
            destinations_out.append(_parse_public_uri(destination.get("uri")))
        return tuple(destinations_out)

    legacy = application.get("self_hosted_domains")
    if legacy is not None:
        if not isinstance(legacy, list) or not legacy:
            raise PublicDashboardAccessError("application destinations invalid")
        return tuple(_parse_public_uri(value) for value in legacy)

    return (_parse_public_uri(application.get("domain")),)


def _is_public_dashboard_path(path: str) -> bool:
    return any(path == root or path.startswith(f"{root}/") for root in _TARGET_ROOTS)


def select_public_dashboard_application_ids(payload: object) -> tuple[str, ...]:
    """Return only exact-host Access apps covering the public dashboard.

    A host-wide or a different-host application is deliberately not selected.
    The narrow public routes are sufficient to make every current KMFA page
    work without changing unrelated Cloudflare applications.
    """

    selected: set[str] = set()
    for application in _single_page_result(payload):
        if application.get("type") != "self_hosted":
            continue
        app_id = application.get("id")
        if not isinstance(app_id, str) or _UUID_RE.fullmatch(app_id.lower()) is None:
            raise PublicDashboardAccessError("application identifier invalid")
        destinations = _application_destinations(application)
        matched = [path for host, path in destinations if host == PUBLIC_DASHBOARD_HOST]
        if not matched:
            continue
        if len(matched) != len(destinations):
            raise PublicDashboardAccessError("application destinations mixed")
        paths = tuple(matched)
        if any(_is_public_dashboard_path(path) for path in paths):
            selected.add(app_id.lower())
    if not selected:
        raise PublicDashboardAccessError("public dashboard applications unavailable")
    return tuple(sorted(selected))


def public_dashboard_bypass_policy_payload() -> dict[str, object]:
    return {
        "name": PUBLIC_DASHBOARD_BYPASS_POLICY_NAME,
        "decision": "bypass",
        "include": [{"everyone": {}}],
    }


def public_dashboard_bypass_policy_state(payload: object) -> str:
    """Classify a one-app policy list without emitting any policy identifier."""

    matches = []
    for policy in _single_page_result(payload):
        if policy.get("name") != PUBLIC_DASHBOARD_BYPASS_POLICY_NAME:
            continue
        policy_id = policy.get("id")
        if not isinstance(policy_id, str) or _UUID_RE.fullmatch(policy_id.lower()) is None:
            return "INVALID"
        if (
            policy.get("decision") != "bypass"
            or policy.get("include") != [{"everyone": {}}]
            or policy.get("exclude") not in (None, [])
            or policy.get("require") not in (None, [])
        ):
            return "INVALID"
        matches.append(policy_id.lower())
    if not matches:
        return "MISSING"
    return "PRESENT" if len(set(matches)) == 1 else "INVALID"


def public_origin_guard_state(payload: object) -> str:
    """Verify every configured source guard row is the public override."""

    rows = payload.get("data") if isinstance(payload, Mapping) and isinstance(payload.get("data"), list) else payload
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise PublicDashboardAccessError("Coolify environment list invalid")
    values = [row.get("value") for row in rows if row.get("key") == "KMFA_PRIVATE_OPS_REQUIRE_ACCESS"]
    return "PRESENT" if values and all(value == "0" for value in values) else "INVALID"


def public_origin_guard_entry_ids(payload: object) -> tuple[str, ...]:
    rows = payload.get("data") if isinstance(payload, Mapping) and isinstance(payload.get("data"), list) else payload
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise PublicDashboardAccessError("Coolify environment list invalid")
    identifiers: set[str] = set()
    for row in rows:
        if row.get("key") != "KMFA_PRIVATE_OPS_REQUIRE_ACCESS":
            continue
        identifier = row.get("uuid")
        if not isinstance(identifier, str) or not identifier:
            raise PublicDashboardAccessError("Coolify environment identifier invalid")
        identifiers.add(identifier)
    return tuple(sorted(identifiers))


def _write_private_lines(path: str | Path, lines: tuple[str, ...]) -> None:
    target = Path(path)
    if not target.name or target.is_symlink() or any("\n" in line or "\r" in line for line in lines):
        raise PublicDashboardAccessError("output path invalid")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + ("\n" if lines else ""))
        os.replace(temporary, target)
        target.chmod(0o600)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _write_private_json(path: str | Path, payload: object) -> None:
    target = Path(path)
    if not target.name or target.is_symlink():
        raise PublicDashboardAccessError("output path invalid")
    _write_private_lines(target, (json.dumps(payload, separators=(",", ":"), ensure_ascii=True),))


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return 2
    try:
        command = args.pop(0)
        if command == "select-apps" and len(args) == 2:
            _write_private_lines(args[1], select_public_dashboard_application_ids(_read_json(args[0])))
        elif command == "policy-payload" and len(args) == 1:
            _write_private_json(args[0], public_dashboard_bypass_policy_payload())
        elif command == "policy-state" and len(args) == 1:
            print(public_dashboard_bypass_policy_state(_read_json(args[0])))
        elif command == "origin-guard-entry-ids" and len(args) == 2:
            _write_private_lines(args[1], public_origin_guard_entry_ids(_read_json(args[0])))
        elif command == "origin-guard-state" and len(args) == 1:
            print(public_origin_guard_state(_read_json(args[0])))
        else:
            return 2
    except (OSError, PublicDashboardAccessError, ValueError, TypeError):
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through the CLI wrapper in Actions.
    raise SystemExit(main())
