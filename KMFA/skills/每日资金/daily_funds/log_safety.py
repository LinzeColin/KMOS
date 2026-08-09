"""Values-free cron events and Coolify log summaries for daily funds.

The daily-funds container deliberately keeps its detailed state in its
owner-only volumes.  Cron's stdout can be exposed through a public GitHub
Actions log, so it must never become a second channel for source messages,
attachment names, identifiers, amounts, exception text, or credentials.
"""

from __future__ import annotations

from collections import Counter
import json
import re
from pathlib import Path
from typing import Any, Mapping


CRON_EVENT_SCHEMA = "kmfa.daily_funds.cron_event.v1"
LOG_SUMMARY_SCHEMA = "kmfa.daily_funds.coolify_log_summary.v1"
JOB_NAMES = frozenset(
    {
        "preflight",
        "bootstrap-dws-auth",
        "runtime-audit",
        "r2-guard",
        "raw-archive-audit",
        "poll",
        "auth-probe",
        "keepalive",
        "backfill",
        "observer",
        "cold-backup",
        "restore-drill",
        "restore",
        "healthcheck",
    }
)
OUTCOMES = frozenset({"SUCCEEDED", "NEEDS_ATTENTION", "LOCK_HELD"})
# A cron log is public-facing operational telemetry, not an exception channel.
# Keep this vocabulary deliberately finite.  New runtime codes must be
# consciously admitted here; otherwise they are represented by the fixed
# ``UNCLASSIFIED`` marker rather than being copied from a provider response.
MACHINE_CODES = frozenset(
    {
        "ARCHIVE_ONLY_POINTER_FORBIDDEN",
        "AUTH_OK",
        "AUTH_PROBE_LOCK_HELD",
        "BACKFILL_COMPLETE",
        "BACKFILL_COMPLETE_NEEDS_REVIEW",
        "BACKFILLING",
        "BACKFILLING_NEEDS_REVIEW",
        "BACKFILL_LOCK_HELD",
        "CONFIG_INVALID",
        "DWS_AUTH_REQUIRED",
        "DWS_BOOTSTRAP_READY",
        "DWS_HISTORY_PERMISSION_DENIED",
        "KEEPALIVE_OK",
        "KEEPALIVE_LOCK_HELD",
        "OBSERVER_LOCK_HELD",
        "OPERATION_RECEIPT_FAILED",
        "OPERATION_START_RECEIPT_FAILED",
        "PUBLISHER_LOCK_HELD",
        "RESTORE_OK",
        "RUNTIME_AUDIT_OK",
        "RAW_ARCHIVE_AUDITED",
        "RAW_ARCHIVE_AUDIT_LOCK_HELD",
        "RAW_ARCHIVE_AUDIT_NEEDS_REVIEW",
        "R2_GUARD_LOCK_HELD",
        "R2_ZERO_CHARGE_GUARD_API_FAILED",
        "R2_ZERO_CHARGE_GUARD_API_INVALID",
        "R2_ZERO_CHARGE_GUARD_BUCKETS_EMPTY",
        "R2_ZERO_CHARGE_GUARD_BUDGET",
        "R2_ZERO_CHARGE_GUARD_CLOCK_INVALID",
        "R2_ZERO_CHARGE_GUARD_IA_LIFECYCLE",
        "R2_ZERO_CHARGE_GUARD_IA_METRICS",
        "R2_ZERO_CHARGE_GUARD_NONSTANDARD_BUCKET",
        "R2_ZERO_CHARGE_GUARD_OK",
        "R2_ZERO_CHARGE_GUARD_REQUIRED",
        "SOURCE_MATCH_ZERO",
        "UNHANDLED",
        "VALID_PUBLISHED",
    }
)
_HTTP_STATUS = re.compile(r"(?:[1-5][0-9]{2}|000)\Z")
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_MAX_EVENT_LINE_BYTES = 1024


def safe_machine_code(code: object) -> str:
    """Return a finite code or a non-informative fail-closed marker."""

    return code if isinstance(code, str) and code in MACHINE_CODES else "UNCLASSIFIED"


def cron_event(job: str, outcome: str, machine_code: object) -> dict[str, str]:
    """Return the only cron payload that is permitted to leave the container."""

    if job not in JOB_NAMES:
        raise ValueError("invalid daily-funds cron job")
    if outcome not in OUTCOMES:
        raise ValueError("invalid daily-funds cron outcome")
    return {
        "schema_version": CRON_EVENT_SCHEMA,
        "job": job,
        "outcome": outcome,
        "machine_code": safe_machine_code(machine_code),
    }


def outcome_for_result(*, ok: bool, code: object) -> str:
    """Collapse internal detail to a fixed, non-sensitive scheduler outcome."""

    if isinstance(code, str) and code.endswith("_LOCK_HELD"):
        return "LOCK_HELD"
    return "SUCCEEDED" if ok else "NEEDS_ATTENTION"


def _bounded_payload(path: Path) -> tuple[bytes, str, bool]:
    try:
        with path.open("rb") as handle:
            payload = handle.read(_MAX_RESPONSE_BYTES + 1)
    except OSError:
        return b"", "INPUT_UNAVAILABLE", False
    if len(payload) > _MAX_RESPONSE_BYTES:
        return payload[:_MAX_RESPONSE_BYTES], "CAPTURED", True
    return payload, "CAPTURED", False


def _log_text(payload: bytes) -> tuple[str, str]:
    text = payload.decode("utf-8", errors="replace")
    try:
        decoded: Any = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return text, "TEXT"
    if isinstance(decoded, Mapping):
        logs = decoded.get("logs")
        if isinstance(logs, str):
            return logs, "JSON_LOGS_STRING"
        if isinstance(logs, list) and all(isinstance(item, str) for item in logs):
            return "\n".join(logs), "JSON_LOGS_LIST"
        return "", "JSON_WITHOUT_LOG_TEXT"
    if isinstance(decoded, list) and all(isinstance(item, str) for item in decoded):
        return "\n".join(decoded), "JSON_STRING_LIST"
    return "", "JSON_UNSUPPORTED"


def _event_from_line(line: str) -> tuple[str, str, str] | None:
    if not line or len(line.encode("utf-8")) > _MAX_EVENT_LINE_BYTES:
        return None
    try:
        payload = json.loads(line)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, Mapping) or set(payload) != {"schema_version", "job", "outcome", "machine_code"}:
        return None
    if payload.get("schema_version") != CRON_EVENT_SCHEMA:
        return None
    job = payload.get("job")
    outcome = payload.get("outcome")
    machine_code = payload.get("machine_code")
    if not isinstance(job, str) or not isinstance(outcome, str) or not isinstance(machine_code, str):
        return None
    if job not in JOB_NAMES or outcome not in OUTCOMES or machine_code not in MACHINE_CODES | {"UNCLASSIFIED"}:
        return None
    return job, outcome, machine_code


def summarize_coolify_logs(
    path: str | Path,
    *,
    http_status: str,
    curl_exit: int | str,
) -> dict[str, object]:
    """Summarize a Coolify log response without returning a single raw line.

    The response is processed only in the ephemeral Actions runner.  The
    public result consists solely of a bounded transport status, line counts,
    and fixed-schema cron event counts.  Unknown lines are counted but never
    copied, redacted, or serialized.
    """

    payload, input_state, truncated = _bounded_payload(Path(path))
    text, payload_shape = _log_text(payload) if input_state == "CAPTURED" else ("", "UNAVAILABLE")
    counts: Counter[tuple[str, str, str]] = Counter()
    nonempty_lines = 0
    unrecognized_lines = 0
    for line in text.splitlines():
        if not line:
            continue
        nonempty_lines += 1
        event = _event_from_line(line)
        if event is None:
            unrecognized_lines += 1
        else:
            counts[event] += 1

    safe_status = http_status if _HTTP_STATUS.fullmatch(http_status) else "UNKNOWN"
    try:
        curl_ok = int(curl_exit) == 0
    except (TypeError, ValueError):
        curl_ok = False
    event_counts = {
        job: {
            outcome: sum(counts[(job, outcome, code)] for code in MACHINE_CODES | {"UNCLASSIFIED"})
            for outcome in sorted(OUTCOMES)
            if sum(counts[(job, outcome, code)] for code in MACHINE_CODES | {"UNCLASSIFIED"})
        }
        for job in sorted(JOB_NAMES)
        if any(
            counts[(job, outcome, code)]
            for outcome in OUTCOMES
            for code in MACHINE_CODES | {"UNCLASSIFIED"}
        )
    }
    # The code vocabulary is fixed above, so this remains values-free while
    # distinguishing a real AUTH_OK receipt from an unrelated successful job.
    machine_code_counts = {
        code: sum(counts[(job, outcome, code)] for job in JOB_NAMES for outcome in OUTCOMES)
        for code in sorted(MACHINE_CODES | {"UNCLASSIFIED"})
        if any(counts[(job, outcome, code)] for job in JOB_NAMES for outcome in OUTCOMES)
    }
    return {
        "schema_version": LOG_SUMMARY_SCHEMA,
        "http_status": safe_status,
        "transport": "OK" if curl_ok else "NEEDS_ATTENTION",
        "input_state": input_state,
        "payload_shape": payload_shape,
        "captured_bytes": len(payload),
        "payload_truncated": truncated,
        "nonempty_line_count": nonempty_lines,
        "daily_funds_event_counts": event_counts,
        "daily_funds_machine_code_counts": machine_code_counts,
        "unrecognized_line_count": unrecognized_lines,
    }
