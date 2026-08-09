"""Strict, values-free helpers for one Cloudflare Access history-probe bridge.

This module deliberately does not make HTTP requests.  The GitHub Actions
runner owns the short-lived credential, while this code only validates the
provider replies held in mode-0600 temporary files.  Its public output is a
small finite vocabulary; no Access identifier, host, credential, cursor or
source value is ever written to stdout.
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit


ACCESS_BRIDGE_SCHEMA = "kmfa.daily_funds.cloudflare_access_bridge.v1"
PROBE_PATH = "/ops/api/daily-funds/history-probe"
SERVICE_TOKEN_DURATION = "60m"
_MAX_RESPONSE_BYTES = 512 * 1024
_AUD_RE = re.compile(r"^[a-f0-9]{64}$")
# Cloudflare describes these opaque identifiers as UUIDs but does not promise
# an RFC-version nibble.  Keep the route-safe canonical 36-character shape
# without needlessly rejecting a valid provider-generated identifier.
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_HOST_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_RUN_TAG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_CREDENTIAL_RE = re.compile(r"^[A-Za-z0-9._-]{1,256}$")
_BRIDGE_RESOURCE_PREFIX = "kmfa-daily-funds-history-probe-"

_PROBE_STATES = frozenset({"NOT_REQUESTED", "REQUESTED", "RUNNING", "COMPLETED", "FAILED", "EXPIRED"})
_CONTINUATION_STATES = frozenset({
    "NOT_STARTED",
    "FIRST_PAGE_TERMINAL",
    "SECOND_PAGE_TERMINAL",
    "SECOND_PAGE_CONTINUES",
    "GROUP_HISTORY_FALLBACK_FIRST_PAGE_TERMINAL",
    "GROUP_HISTORY_FALLBACK_SECOND_PAGE_TERMINAL",
    "GROUP_HISTORY_FALLBACK_SECOND_PAGE_CONTINUES",
})
_CURSOR_TRANSCRIPTS = {
    "NOT_STARTED": "NOT_STARTED",
    "FIRST_PAGE_TERMINAL": "FIRST_PAGE_TERMINAL",
    "SECOND_PAGE_TERMINAL": "OPAQUE_CURSOR_REUSED_SECOND_PAGE_TERMINAL",
    "SECOND_PAGE_CONTINUES": "OPAQUE_CURSOR_REUSED_SECOND_PAGE_CONTINUES",
    "GROUP_HISTORY_FALLBACK_FIRST_PAGE_TERMINAL": "GROUP_HISTORY_FALLBACK_FIRST_PAGE_TERMINAL",
    "GROUP_HISTORY_FALLBACK_SECOND_PAGE_TERMINAL": "GROUP_HISTORY_FALLBACK_OPAQUE_CURSOR_REUSED_SECOND_PAGE_TERMINAL",
    "GROUP_HISTORY_FALLBACK_SECOND_PAGE_CONTINUES": "GROUP_HISTORY_FALLBACK_OPAQUE_CURSOR_REUSED_SECOND_PAGE_CONTINUES",
}
_RECORD_LIST_SHAPES = frozenset({
    "NOT_OBSERVED", "NO_DIRECT_LIST", "UNRECOGNIZED_DIRECT_LIST",
})
_RECEIPT_RECORD_LIST_SHAPES = _RECORD_LIST_SHAPES | {"UNCLASSIFIED"}
_MACHINE_CODES = frozenset({
    "DWS_HISTORY_PROBE_NOT_REQUESTED",
    "DWS_HISTORY_PROBE_QUEUED",
    "DWS_HISTORY_PROBE_RUNNING",
    "DWS_HISTORY_PROBE_COMPLETED",
    "DWS_HISTORY_PROBE_EXPIRED",
    "DWS_HISTORY_PROBE_LOCK_HELD",
    "DWS_HISTORY_PERMISSION_DENIED",
    "DWS_HISTORY_PROBE_CURSOR_MISSING",
    "DWS_PAGE_RECORDS_MISSING",
    "CONFIG_INVALID",
    "DWS_HISTORY_PROBE_UNHANDLED",
})
_HTTP_STATUS_RE = re.compile(r"^(?:[1-5][0-9]{2}|000)$")
_PROBE_ORIGIN_HEADER = b"x-kmfa-daily-funds-probe"
_PROBE_ORIGIN_VALUE = b"v1"
_MAX_RESPONSE_HEADER_BYTES = 65_536


class AccessBridgeInputError(ValueError):
    """A provider response or temporary input cannot safely drive the bridge."""


def _read_json(path: str | Path) -> Any:
    try:
        with Path(path).open("rb") as handle:
            raw = handle.read(_MAX_RESPONSE_BYTES + 1)
    except OSError as exc:
        raise AccessBridgeInputError("response unavailable") from exc
    if len(raw) > _MAX_RESPONSE_BYTES:
        raise AccessBridgeInputError("response too large")
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AccessBridgeInputError("response invalid") from exc
    return decoded


def _read_object(path: str | Path) -> Mapping[str, Any]:
    payload = _read_json(path)
    if not isinstance(payload, Mapping):
        raise AccessBridgeInputError("response object required")
    return payload


def _cloudflare_result(path: str | Path, *, expected_type: type[object]) -> object:
    payload = _read_object(path)
    result = payload.get("result")
    if payload.get("success") is not True or not isinstance(result, expected_type):
        raise AccessBridgeInputError("cloudflare result invalid")
    return result


def _cloudflare_single_page_result(path: str | Path) -> list[Mapping[str, Any]]:
    """Return a fully observed provider list, never a partial cleanup view.

    Cleanup is safe only if the runner saw every candidate resource for the
    exact run tag.  The workflow requests ``per_page=1000`` and this parser
    rejects a response that declares another page/cursor rather than silently
    declaring an orphan absent.
    """

    payload = _read_object(path)
    result = _cloudflare_result(path, expected_type=list)
    assert isinstance(result, list)
    if not all(isinstance(item, Mapping) for item in result):
        raise AccessBridgeInputError("cloudflare list invalid")
    result_info = payload.get("result_info")
    if result_info is not None:
        if not isinstance(result_info, Mapping):
            raise AccessBridgeInputError("cloudflare list invalid")
        total_pages = result_info.get("total_pages")
        cursor = result_info.get("cursor")
        if (
            total_pages not in (None, 0, 1)
            or cursor not in (None, "")
        ):
            raise AccessBridgeInputError("cloudflare list incomplete")
    return [dict(item) for item in result]


def _coolify_rows(path: str | Path) -> list[Mapping[str, Any]]:
    payload = _read_json(path)
    data = payload.get("data") if isinstance(payload, Mapping) and isinstance(payload.get("data"), list) else payload
    if not isinstance(data, list):
        raise AccessBridgeInputError("Coolify environment list required")
    rows = [item for item in data if isinstance(item, Mapping)]
    if len(rows) != len(data):
        raise AccessBridgeInputError("Coolify environment row invalid")
    return rows


def _configured_audiences(path: str | Path) -> frozenset[str]:
    values: set[str] = set()
    found = False
    for row in _coolify_rows(path):
        if row.get("key") != "KMFA_CLOUDFLARE_ACCESS_AUD":
            continue
        found = True
        value = row.get("value")
        if not isinstance(value, str) or not value.strip():
            raise AccessBridgeInputError("Cloudflare Access audience unavailable")
        candidates = tuple(part.strip() for part in value.split(","))
        if not candidates or any(_AUD_RE.fullmatch(candidate) is None for candidate in candidates):
            raise AccessBridgeInputError("Cloudflare Access audience malformed")
        values.update(candidates)
    if not found or not values:
        raise AccessBridgeInputError("Cloudflare Access audience unavailable")
    return frozenset(values)


def _parse_public_domain(value: object) -> tuple[str, str]:
    """Return an HTTPS origin plus exact configured Access path.

    Access domains can be bare host/path strings.  We intentionally reject a
    port, wildcard hostname, private host, query or fragment so the runner
    cannot be redirected to an arbitrary target by a provider response.
    """

    if not isinstance(value, str) or not value or len(value) > 256:
        raise AccessBridgeInputError("Access domain invalid")
    candidate = value.strip()
    if not candidate or "*" in candidate.split("/", 1)[0]:
        raise AccessBridgeInputError("Access domain invalid")
    try:
        parsed = urlsplit(candidate if "://" in candidate else f"https://{candidate}")
        port = parsed.port
    except ValueError as exc:
        raise AccessBridgeInputError("Access domain invalid") from exc
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.query
        or parsed.fragment
    ):
        raise AccessBridgeInputError("Access domain invalid")
    host = parsed.hostname.lower().rstrip(".")
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local") or "." not in host:
        raise AccessBridgeInputError("Access domain invalid")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        labels = host.split(".")
        if any(_HOST_LABEL_RE.fullmatch(label) is None for label in labels):
            raise AccessBridgeInputError("Access domain invalid")
    else:
        raise AccessBridgeInputError("Access domain invalid")
    path = parsed.path or "/"
    if not path.startswith("/") or "//" in path or "\\" in path:
        raise AccessBridgeInputError("Access domain invalid")
    return f"https://{host}", path


def _path_covers_probe(path: str) -> bool:
    """Accept only a specific /ops path pattern, never a host-wide catchall."""

    if path in {PROBE_PATH, f"{PROBE_PATH}/*"}:
        return True
    prefixes = ("/ops/*", "/ops/api/*", "/ops/api/daily-funds/*")
    return path in prefixes


def _path_is_narrow_ops_scope(path: str) -> bool:
    """Allow the exact ``/ops`` landing path alongside probe-capable paths.

    An exact landing path does not cover the fixed history-probe route, but it
    also cannot extend a short-lived service token outside the operational
    namespace.  Callers must separately require at least one destination that
    does cover ``PROBE_PATH``.
    """

    return path == "/ops" or _path_covers_probe(path)


def _narrow_app_origin(app: Mapping[str, Any]) -> str | None:
    """Return a validated narrow origin, or ``None`` for an unsafe app.

    Cloudflare's newer ``destinations`` field is authoritative when present.
    Some provider responses retain a stale legacy ``domain`` field after a
    path migration, so using that field as a second routing authority would
    incorrectly reject an otherwise narrow application.  We still require
    every effective destination to share one HTTPS origin and an explicit
    /ops pattern; a token can never be attached to a mixed or host-wide app.
    """

    destinations = app.get("destinations")
    if destinations is not None:
        if not isinstance(destinations, list) or not destinations:
            return None
        origin: str | None = None
        probe_covered = False
        for destination in destinations:
            if not isinstance(destination, Mapping) or destination.get("type") != "public":
                return None
            try:
                candidate_origin, candidate_path = _parse_public_domain(destination.get("uri"))
            except AccessBridgeInputError:
                return None
            if not _path_is_narrow_ops_scope(candidate_path):
                return None
            probe_covered = probe_covered or _path_covers_probe(candidate_path)
            if origin is None:
                origin = candidate_origin
            elif candidate_origin != origin:
                return None
        return origin if probe_covered else None

    try:
        origin, path = _parse_public_domain(app.get("domain"))
    except AccessBridgeInputError:
        return None
    if not _path_is_narrow_ops_scope(path):
        return None
    legacy_domains = app.get("self_hosted_domains")
    if legacy_domains is None:
        return origin if _path_covers_probe(path) else None
    if not isinstance(legacy_domains, list) or not legacy_domains:
        return None
    probe_covered = _path_covers_probe(path)
    for domain in legacy_domains:
        try:
            candidate_origin, candidate_path = _parse_public_domain(domain)
        except AccessBridgeInputError:
            return None
        if candidate_origin != origin or not _path_is_narrow_ops_scope(candidate_path):
            return None
        probe_covered = probe_covered or _path_covers_probe(candidate_path)
    return origin if probe_covered else None


def resolve_bridge_target(coolify_env_path: str | Path, access_apps_path: str | Path) -> dict[str, str]:
    """Resolve exactly one configured, narrow self-hosted Access application."""

    audiences = _configured_audiences(coolify_env_path)
    payload = _read_object(access_apps_path)
    result = payload.get("result")
    if payload.get("success") is not True or not isinstance(result, list):
        raise AccessBridgeInputError("Access application list invalid")
    result_info = payload.get("result_info")
    if result_info is not None:
        if not isinstance(result_info, Mapping):
            raise AccessBridgeInputError("Access application list invalid")
        total_pages = result_info.get("total_pages")
        if not isinstance(total_pages, int) or total_pages != 1:
            raise AccessBridgeInputError("Access application list incomplete")

    matches: list[dict[str, str]] = []
    for app in result:
        if not isinstance(app, Mapping) or app.get("type") != "self_hosted":
            continue
        app_id = app.get("id")
        audience = app.get("aud")
        if (
            not isinstance(app_id, str)
            or _UUID_RE.fullmatch(app_id.lower()) is None
            or not isinstance(audience, str)
            or audience not in audiences
        ):
            continue
        origin = _narrow_app_origin(app)
        if origin is None:
            continue
        matches.append({"app_id": app_id.lower(), "origin": origin})
    if len(matches) != 1:
        raise AccessBridgeInputError("Access history-probe application ambiguous")
    return matches[0]


def bridge_resource_name(run_tag: str) -> str:
    if _RUN_TAG_RE.fullmatch(run_tag) is None:
        raise AccessBridgeInputError("run tag invalid")
    return f"{_BRIDGE_RESOURCE_PREFIX}{run_tag}"


def service_token_payload(run_tag: str) -> dict[str, str]:
    return {
        "name": bridge_resource_name(run_tag),
        "duration": SERVICE_TOKEN_DURATION,
    }


def policy_payload(service_token_id: str, run_tag: str) -> dict[str, object]:
    if _UUID_RE.fullmatch(service_token_id.lower()) is None:
        raise AccessBridgeInputError("policy input invalid")
    return {
        "name": bridge_resource_name(run_tag),
        "decision": "non_identity",
        "include": [{"service_token": {"token_id": service_token_id.lower()}}],
    }


def _owned_resource_ids(path: str | Path, run_tag: str) -> tuple[str, ...]:
    """Find only the exact, run-scoped Access resources in one API list."""

    expected_name = bridge_resource_name(run_tag)
    identifiers: set[str] = set()
    for item in _cloudflare_single_page_result(path):
        if item.get("name") != expected_name:
            continue
        identifier = item.get("id")
        if not isinstance(identifier, str) or _UUID_RE.fullmatch(identifier.lower()) is None:
            raise AccessBridgeInputError("owned resource invalid")
        identifiers.add(identifier.lower())
    return tuple(sorted(identifiers))


def owned_bridge_resource_ids(
    service_tokens_path: str | Path,
    policies_path: str | Path,
    run_tag: str,
) -> dict[str, tuple[str, ...]]:
    """Return opaque IDs for one run only; callers must keep them private."""

    return {
        "service_token_ids": _owned_resource_ids(service_tokens_path, run_tag),
        "policy_ids": _owned_resource_ids(policies_path, run_tag),
    }


def _strict_credential(value: object) -> str:
    if not isinstance(value, str) or _CREDENTIAL_RE.fullmatch(value) is None:
        raise AccessBridgeInputError("service token response invalid")
    return value


def capture_service_token(response_path: str | Path) -> dict[str, str]:
    result = _cloudflare_result(response_path, expected_type=dict)
    assert isinstance(result, Mapping)
    service_token_id = _service_token_id(result)
    return {
        "service_token_id": service_token_id.lower(),
        "client_id": _strict_credential(result.get("client_id")),
        "client_secret": _strict_credential(result.get("client_secret")),
    }


def capture_service_token_id(response_path: str | Path) -> dict[str, str]:
    """Capture only a deletable token ID before reading credential material."""

    result = _cloudflare_result(response_path, expected_type=dict)
    assert isinstance(result, Mapping)
    return {"service_token_id": _service_token_id(result)}


def _service_token_id(result: Mapping[str, Any]) -> str:
    service_token_id = result.get("id")
    if not isinstance(service_token_id, str) or _UUID_RE.fullmatch(service_token_id.lower()) is None:
        raise AccessBridgeInputError("service token response invalid")
    return service_token_id.lower()


def capture_policy(response_path: str | Path) -> dict[str, str]:
    result = _cloudflare_result(response_path, expected_type=dict)
    assert isinstance(result, Mapping)
    policy_id = result.get("id")
    if not isinstance(policy_id, str) or _UUID_RE.fullmatch(policy_id.lower()) is None:
        raise AccessBridgeInputError("policy response invalid")
    return {"policy_id": policy_id.lower()}


def validate_success_response(response_path: str | Path) -> bool:
    try:
        return _read_object(response_path).get("success") is True
    except AccessBridgeInputError:
        return False


def _probe_origin_confirmed(response_headers_path: str | Path) -> bool:
    """Accept only the fixed marker from the final HTTP response block.

    A Cloudflare or proxy 503 may share an HTTP status with the application's
    deliberate control-volume response.  The headers stay in the runner's
    private temporary directory and this helper extracts only one constant,
    so the public receipt does not attribute an upstream failure to the app.
    """

    try:
        raw = Path(response_headers_path).read_bytes()
    except OSError:
        return False
    if len(raw) > _MAX_RESPONSE_HEADER_BYTES:
        return False
    blocks = re.split(rb"\r?\n\r?\n", raw)
    final_block = next((block for block in reversed(blocks) if block.startswith(b"HTTP/")), b"")
    if not final_block:
        return False
    values: list[bytes] = []
    for line in final_block.splitlines()[1:]:
        name, separator, value = line.partition(b":")
        if separator and name.lower() == _PROBE_ORIGIN_HEADER:
            values.append(value.strip())
    return values == [_PROBE_ORIGIN_VALUE]


def summarize_probe_response(
    response_path: str | Path,
    *,
    response_headers_path: str | Path,
    http_status: object,
    curl_exit: object,
) -> dict[str, str]:
    """Turn the fixed private API reply into a finite, values-free receipt."""

    try:
        curl_ok = int(curl_exit) == 0
    except (TypeError, ValueError):
        curl_ok = False
    status = str(http_status)
    if not curl_ok or _HTTP_STATUS_RE.fullmatch(status) is None:
        return _probe_summary("TRANSPORT_FAILED")
    if status in {"401", "403"}:
        return _probe_summary("HTTP_DENIED")
    if status != "200":
        return _probe_summary("HTTP_UNAVAILABLE")
    if not _probe_origin_confirmed(response_headers_path):
        return _probe_summary("HTTP_ORIGIN_UNVERIFIED")
    try:
        payload = _read_object(response_path)
    except AccessBridgeInputError:
        return _probe_summary("INVALID_RESPONSE")
    if set(payload) != {
        "state", "machine_code", "updated_at", "expires_at", "continuation_state", "cursor_transcript",
        "record_list_shape",
    }:
        return _probe_summary("INVALID_RESPONSE")
    state = payload.get("state")
    continuation_state = payload.get("continuation_state")
    cursor_transcript = payload.get("cursor_transcript")
    machine_code = payload.get("machine_code")
    record_list_shape = payload.get("record_list_shape")
    if (
        state not in _PROBE_STATES
        or continuation_state not in _CONTINUATION_STATES
        or cursor_transcript != _CURSOR_TRANSCRIPTS.get(continuation_state)
        or machine_code not in _MACHINE_CODES
        or record_list_shape not in _RECORD_LIST_SHAPES
        or not isinstance(payload.get("updated_at"), str)
        or (payload.get("expires_at") is not None and not isinstance(payload.get("expires_at"), str))
    ):
        return _probe_summary("INVALID_RESPONSE")
    assert isinstance(state, str)
    assert isinstance(continuation_state, str)
    assert isinstance(cursor_transcript, str)
    assert isinstance(machine_code, str)
    assert isinstance(record_list_shape, str)
    result = "HISTORY_PROBE_COMPLETED" if (
        state == "COMPLETED"
        and continuation_state in {
            "FIRST_PAGE_TERMINAL",
            "SECOND_PAGE_TERMINAL",
            "GROUP_HISTORY_FALLBACK_FIRST_PAGE_TERMINAL",
            "GROUP_HISTORY_FALLBACK_SECOND_PAGE_TERMINAL",
        }
        and machine_code == "DWS_HISTORY_PROBE_COMPLETED"
    ) else "NOT_MET"
    return {
        "schema_version": ACCESS_BRIDGE_SCHEMA,
        "transport": "OK",
        "probe_state": state,
        "continuation_state": continuation_state,
        "cursor_transcript": cursor_transcript,
        "record_list_shape": record_list_shape,
        "machine_code": machine_code,
        "result": result,
    }


def summarize_probe_start_response(
    response_path: str | Path,
    *,
    response_headers_path: str | Path,
    http_status: object,
    curl_exit: object,
) -> dict[str, str]:
    """Classify the fixed no-body start request without exposing its reply.

    The bridge must not print an Access deny page, an API error body, or the
    backend's opaque request ID.  It only emits enough finite state to decide
    whether a GET poll is safe.  A 409 is deliberately pollable: it means the
    fixed request was already live, so issuing a second start would add no
    value and risks racing the single-flight guard.
    """

    try:
        curl_ok = int(curl_exit) == 0
    except (TypeError, ValueError):
        curl_ok = False
    status = str(http_status)
    if not curl_ok or _HTTP_STATUS_RE.fullmatch(status) is None:
        return _probe_start_summary("TRANSPORT_FAILED", "HISTORY_PROBE_START_TRANSPORT_FAILED")
    if status in {"401", "403"}:
        return _probe_start_summary("HTTP_DENIED", "HISTORY_PROBE_START_ACCESS_OR_ORIGIN_DENIED")
    origin_confirmed = _probe_origin_confirmed(response_headers_path)
    if status == "409":
        return _probe_start_summary(
            "HTTP_CONFLICT" if origin_confirmed else "HTTP_UPSTREAM_UNAVAILABLE",
            "HISTORY_PROBE_ALREADY_PENDING" if origin_confirmed else "HISTORY_PROBE_START_UPSTREAM_UNAVAILABLE",
        )
    if status == "422":
        return _probe_start_summary(
            "HTTP_BODY_REJECTED" if origin_confirmed else "HTTP_UPSTREAM_UNAVAILABLE",
            "HISTORY_PROBE_START_BODY_REJECTED" if origin_confirmed else "HISTORY_PROBE_START_UPSTREAM_UNAVAILABLE",
        )
    if status == "503":
        return _probe_start_summary(
            "HTTP_CONTROL_UNAVAILABLE" if origin_confirmed else "HTTP_UPSTREAM_UNAVAILABLE",
            "HISTORY_PROBE_START_CONTROL_UNAVAILABLE" if origin_confirmed else "HISTORY_PROBE_START_UPSTREAM_UNAVAILABLE",
        )
    if status != "202":
        return _probe_start_summary("HTTP_UNAVAILABLE", "HISTORY_PROBE_START_HTTP_UNAVAILABLE")
    if not origin_confirmed:
        return _probe_start_summary("HTTP_ORIGIN_UNVERIFIED", "HISTORY_PROBE_START_ORIGIN_UNVERIFIED")
    try:
        payload = _read_object(response_path)
    except AccessBridgeInputError:
        return _probe_start_summary("INVALID_RESPONSE", "HISTORY_PROBE_START_INVALID_RESPONSE")
    if set(payload) != {
        "state", "machine_code", "updated_at", "expires_at", "continuation_state", "cursor_transcript",
        "record_list_shape",
    }:
        return _probe_start_summary("INVALID_RESPONSE", "HISTORY_PROBE_START_INVALID_RESPONSE")
    if (
        payload.get("state") != "REQUESTED"
        or payload.get("machine_code") != "DWS_HISTORY_PROBE_QUEUED"
        or payload.get("continuation_state") != "NOT_STARTED"
        or payload.get("cursor_transcript") != "NOT_STARTED"
        or payload.get("record_list_shape") != "NOT_OBSERVED"
        or not isinstance(payload.get("updated_at"), str)
        or not isinstance(payload.get("expires_at"), str)
    ):
        return _probe_start_summary("INVALID_RESPONSE", "HISTORY_PROBE_START_INVALID_RESPONSE")
    return _probe_start_summary("OK", "HISTORY_PROBE_REQUESTED")


def _probe_start_summary(transport: str, result: str) -> dict[str, str]:
    return {
        "schema_version": ACCESS_BRIDGE_SCHEMA,
        "transport": transport,
        "result": result,
    }


def probe_start_poll_state(receipt_path: str | Path) -> str:
    """Return whether a values-free start receipt permits the fixed GET poll."""

    try:
        payload = _read_object(receipt_path)
    except AccessBridgeInputError:
        return "TERMINAL_NOT_MET"
    if set(payload) != {"schema_version", "transport", "result"} or payload.get("schema_version") != ACCESS_BRIDGE_SCHEMA:
        return "TERMINAL_NOT_MET"
    if payload.get("result") in {"HISTORY_PROBE_REQUESTED", "HISTORY_PROBE_ALREADY_PENDING"}:
        return "POLL"
    return "TERMINAL_NOT_MET"


def _probe_summary(transport: str) -> dict[str, str]:
    return {
        "schema_version": ACCESS_BRIDGE_SCHEMA,
        "transport": transport,
        "probe_state": "UNCLASSIFIED",
        "continuation_state": "UNCLASSIFIED",
        "cursor_transcript": "UNCLASSIFIED",
        "record_list_shape": "UNCLASSIFIED",
        "machine_code": "UNCLASSIFIED",
        "result": "NOT_MET",
    }


def probe_poll_state(receipt_path: str | Path) -> str:
    """Return a finite polling decision from a locally-produced receipt."""

    try:
        payload = _read_object(receipt_path)
    except AccessBridgeInputError:
        return "TERMINAL_NOT_MET"
    expected = {
        "schema_version", "transport", "probe_state", "continuation_state",
        "cursor_transcript", "record_list_shape", "machine_code", "result",
    }
    if set(payload) != expected or payload.get("schema_version") != ACCESS_BRIDGE_SCHEMA:
        return "TERMINAL_NOT_MET"
    if payload.get("record_list_shape") not in _RECEIPT_RECORD_LIST_SHAPES:
        return "TERMINAL_NOT_MET"
    if payload.get("result") == "HISTORY_PROBE_COMPLETED":
        return "COMPLETED"
    if payload.get("transport") != "OK":
        return "TERMINAL_NOT_MET"
    if payload.get("probe_state") in {"REQUESTED", "RUNNING"}:
        return "PENDING"
    return "TERMINAL_NOT_MET"


def write_private_json(path: str | Path, payload: Mapping[str, object]) -> None:
    """Atomically write runner-only material without inheriting an unsafe mode."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(encoded)
        os.replace(temporary, target)
        os.chmod(target, 0o600)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
