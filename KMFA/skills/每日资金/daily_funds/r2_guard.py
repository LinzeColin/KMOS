"""Fail-closed Cloudflare R2 zero-charge guard for the daily-funds slice."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from .config import DailyFundsConfig, r2_worst_case_is_within_free_tier
from .state import atomic_json_write, iso_now

UTC = timezone.utc
RECEIPT_SCHEMA = "kmfa.daily_funds.r2_free_tier_guard.v1"
MAX_RECEIPT_AGE = timedelta(hours=6)


class R2GuardError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _require_text(value: object, code: str) -> str:
    if not isinstance(value, str) or not value:
        raise R2GuardError(code)
    return value


def _parse_timestamp(value: object, code: str) -> datetime:
    text = _require_text(value, code)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise R2GuardError(code) from exc
    if parsed.tzinfo is None:
        raise R2GuardError(code)
    return parsed.astimezone(UTC)


def _zero_metric_tree(value: object) -> bool:
    """Accept only a fully-known zero-valued infrequent-access metrics tree."""

    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return value == 0
    if isinstance(value, Mapping):
        return bool(value) and all(_zero_metric_tree(child) for child in value.values())
    return False


class R2FreeTierGuard:
    """Prove the account-wide R2 state before this periodic writer may run.

    The API calls are Cloudflare control-plane reads: they check every bucket
    default, every lifecycle rule, and the account-wide IA metric aggregate.
    The normal 15-minute publication path only reads the short values-free
    receipt, so the guard itself does not multiply hot-object operations.
    """

    def __init__(self, config: DailyFundsConfig):
        self.config = config
        self.base_url = (
            "https://api.cloudflare.com/client/v4/accounts/"
            + urllib.parse.quote(config.cf_account_id, safe="")
        )

    @property
    def receipt_path(self) -> Path:
        return self.config.state_dir / "r2_free_tier_guard.json"

    def _request(self, path: str) -> Mapping[str, Any]:
        request = urllib.request.Request(
            self.base_url + path,
            headers={
                "Authorization": f"Bearer {self.config.cf_api_token}",
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                decoded = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise R2GuardError("R2_ZERO_CHARGE_GUARD_API_FAILED") from exc
        if not isinstance(decoded, Mapping) or decoded.get("success") is not True:
            raise R2GuardError("R2_ZERO_CHARGE_GUARD_API_FAILED")
        return dict(decoded)

    def _buckets(self) -> tuple[Mapping[str, Any], ...]:
        buckets: list[Mapping[str, Any]] = []
        cursor: str | None = None
        seen_cursors: set[str] = set()
        while True:
            query = "?per_page=1000"
            if cursor is not None:
                query += "&cursor=" + urllib.parse.quote(cursor, safe="")
            payload = self._request("/r2/buckets" + query)
            result = payload.get("result")
            if not isinstance(result, Mapping) or not isinstance(result.get("buckets"), list):
                raise R2GuardError("R2_ZERO_CHARGE_GUARD_API_INVALID")
            page = result["buckets"]
            if not all(isinstance(bucket, Mapping) for bucket in page):
                raise R2GuardError("R2_ZERO_CHARGE_GUARD_API_INVALID")
            buckets.extend(dict(bucket) for bucket in page)
            result_info = payload.get("result_info")
            next_cursor = result_info.get("cursor") if isinstance(result_info, Mapping) else None
            if next_cursor is None:
                return tuple(buckets)
            if not isinstance(next_cursor, str) or not next_cursor or next_cursor in seen_cursors:
                raise R2GuardError("R2_ZERO_CHARGE_GUARD_API_INVALID")
            seen_cursors.add(next_cursor)
            cursor = next_cursor

    def _assert_bucket_defaults_and_lifecycle(self) -> None:
        buckets = self._buckets()
        if not buckets:
            raise R2GuardError("R2_ZERO_CHARGE_GUARD_BUCKETS_EMPTY")
        for bucket in buckets:
            name = _require_text(bucket.get("name"), "R2_ZERO_CHARGE_GUARD_API_INVALID")
            if bucket.get("storage_class") != "Standard":
                raise R2GuardError("R2_ZERO_CHARGE_GUARD_NONSTANDARD_BUCKET")
            lifecycle = self._request(
                "/r2/buckets/" + urllib.parse.quote(name, safe="") + "/lifecycle"
            )
            result = lifecycle.get("result")
            if not isinstance(result, Mapping) or not isinstance(result.get("rules"), list):
                raise R2GuardError("R2_ZERO_CHARGE_GUARD_API_INVALID")
            rules = result["rules"]
            for rule in rules:
                if not isinstance(rule, Mapping):
                    raise R2GuardError("R2_ZERO_CHARGE_GUARD_API_INVALID")
                transitions = rule.get("storageClassTransitions", [])
                if not isinstance(transitions, list):
                    raise R2GuardError("R2_ZERO_CHARGE_GUARD_API_INVALID")
                if any(
                    isinstance(transition, Mapping)
                    and transition.get("storageClass") == "InfrequentAccess"
                    for transition in transitions
                ):
                    # Reject disabled rules too: enabling a latent IA rule
                    # later must not turn a previously green receipt into an
                    # unsafe authorization for automatic writes.
                    raise R2GuardError("R2_ZERO_CHARGE_GUARD_IA_LIFECYCLE")

    def _assert_no_infrequent_access_objects(self) -> None:
        payload = self._request("/r2/metrics")
        result = payload.get("result")
        if not isinstance(result, Mapping) or not _zero_metric_tree(result.get("infrequentAccess")):
            raise R2GuardError("R2_ZERO_CHARGE_GUARD_IA_METRICS")

    def verify(self, *, now: datetime | None = None) -> dict[str, Any]:
        if not r2_worst_case_is_within_free_tier(
            max_new_objects_per_poll=self.config.r2_max_new_objects_per_poll,
            max_new_bytes_per_poll=self.config.r2_max_new_bytes_per_poll,
        ):
            raise R2GuardError("R2_ZERO_CHARGE_GUARD_BUDGET")
        self._assert_bucket_defaults_and_lifecycle()
        self._assert_no_infrequent_access_objects()
        observed_at = now or datetime.now(UTC)
        if observed_at.tzinfo is None:
            raise R2GuardError("R2_ZERO_CHARGE_GUARD_CLOCK_INVALID")
        observed_at = observed_at.astimezone(UTC)
        return {
            "schema_version": RECEIPT_SCHEMA,
            "verified_at": observed_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "config_fingerprint": self.config.redacted_fingerprint(),
            "bucket_default_state": "ALL_STANDARD",
            "lifecycle_state": "NO_IA_TRANSITION",
            "infrequent_access_state": "ZERO",
            "worst_case_state": "UNDER_FREE_TIER_40_PERCENT",
        }

    def verify_and_write(self, *, now: datetime | None = None) -> dict[str, Any]:
        receipt = self.verify(now=now)
        atomic_json_write(self.receipt_path, receipt)
        return receipt

    def require_fresh_receipt(self, *, now: datetime | None = None) -> Mapping[str, Any]:
        try:
            decoded = json.loads(self.receipt_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise R2GuardError("R2_ZERO_CHARGE_GUARD_REQUIRED") from exc
        if (
            not isinstance(decoded, Mapping)
            or set(decoded) != {
                "schema_version",
                "verified_at",
                "config_fingerprint",
                "bucket_default_state",
                "lifecycle_state",
                "infrequent_access_state",
                "worst_case_state",
            }
            or decoded.get("schema_version") != RECEIPT_SCHEMA
            or decoded.get("config_fingerprint") != self.config.redacted_fingerprint()
            or decoded.get("bucket_default_state") != "ALL_STANDARD"
            or decoded.get("lifecycle_state") != "NO_IA_TRANSITION"
            or decoded.get("infrequent_access_state") != "ZERO"
            or decoded.get("worst_case_state") != "UNDER_FREE_TIER_40_PERCENT"
        ):
            raise R2GuardError("R2_ZERO_CHARGE_GUARD_REQUIRED")
        verified_at = _parse_timestamp(decoded.get("verified_at"), "R2_ZERO_CHARGE_GUARD_REQUIRED")
        current = now or datetime.now(UTC)
        if current.tzinfo is None:
            raise R2GuardError("R2_ZERO_CHARGE_GUARD_REQUIRED")
        current = current.astimezone(UTC)
        if verified_at > current or current - verified_at > MAX_RECEIPT_AGE:
            raise R2GuardError("R2_ZERO_CHARGE_GUARD_REQUIRED")
        return dict(decoded)
