"""Projection, mirrors, cold backup, publication pointer and restore oracle."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Protocol

from .config import DailyFundsConfig
from .contracts import (
    DailyBalance,
    FloatingLine,
    HARD_THRESHOLD_FEN,
    SOFT_THRESHOLD_FEN,
    dynamic_flag,
    effective_risk,
    fixed_risk,
    floating_month_lines,
)
from .ingestion import SPARSE_PATH, DownloadedAttachment, GitCommit
from .reconcile import ReconciliationReport
from .state import StatusWriter, atomic_json_write, iso_now

UTC = timezone.utc


class PublicationError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _canonical_bytes(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _jsonable_lines(lines: Iterable[FloatingLine]) -> list[dict[str, Any]]:
    return [
        {
            "name": line.name,
            "threshold_fen": line.threshold_fen,
            "start": line.start.isoformat(),
            "end": line.end.isoformat(),
            "days": line.days,
            "direct_observations": line.direct_observations,
            "covered_days": line.covered_days,
            "carried_forward_days": line.carried_forward_days,
            "coverage": str(line.coverage),
            "active": line.active,
            "reason": line.reason,
        }
        for line in lines
    ]


_PUBLICATION_FIELDS = frozenset({
    "publication_id",
    "business_date",
    "status",
    "source_versions",
    "reconciliation_difference_fen",
    "threshold_snapshot",
    "created_at",
    "git_commit_sha",
    "d1_projection_version",
    "r2_manifest_sha256",
    "oci_backup_state",
})
_R2_MANIFEST_FIELDS = frozenset({"schema_version", "git_commit_sha", "objects", "created_at"})
_OCI_MANIFEST_FIELDS = frozenset({
    "schema_version",
    "publication_id",
    "publication_sha256",
    "git_publication_commit_sha",
    "artifacts",
    "created_at",
})
_THRESHOLD_SNAPSHOT_FIELDS = frozenset({"currency", "fixed", "floating", "fixed_risk", "dynamic_flag"})
_FIXED_THRESHOLD_FIELDS = frozenset({"hard_fen", "soft_fen"})
_FLOATING_LINE_FIELDS = frozenset({
    "name",
    "threshold_fen",
    "start",
    "end",
    "days",
    "direct_observations",
    "covered_days",
    "carried_forward_days",
    "coverage",
    "active",
    "reason",
})
_FLOATING_LINE_NAMES = frozenset({"three_month", "six_month", "custom_date_range", "custom_numeric"})
_FIXED_RISK_LABELS = frozenset({"正常", "关注", "高风险"})
_DYNAMIC_FLAGS = frozenset({"动态偏低", "动态明显偏低"})


def _is_lower_hex(value: object, length: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and all(character in "0123456789abcdef" for character in value)
    )


def _require_lower_hex(value: object, length: int, code: str) -> str:
    if not _is_lower_hex(value, length):
        raise PublicationError(code)
    return str(value)


def _require_integer(value: object, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PublicationError(code)
    return value


def _require_boolean(value: object, code: str) -> bool:
    if not isinstance(value, bool):
        raise PublicationError(code)
    return value


def _require_text(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PublicationError(code)
    return value


def _require_iso_day(value: object, code: str) -> date:
    text = _require_text(value, code)
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise PublicationError(code) from exc


def _require_iso_timestamp(value: object, code: str) -> str:
    text = _require_text(value, code)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PublicationError(code) from exc
    if parsed.tzinfo is None:
        raise PublicationError(code)
    return text


def _validate_threshold_snapshot(snapshot: object) -> dict[str, Any]:
    """Accept only a self-contained, replay-safe threshold decision record.

    The threshold snapshot crosses the private Git, D1, R2, OCI and pointer
    boundaries.  Permissively accepting an arbitrary mapping would let a
    recovered projection retain its amounts but silently lose the decision
    rule that classified them.  Keep this validator independent of the live
    control file: it validates the frozen record, not today's configuration.
    """

    if not isinstance(snapshot, Mapping) or set(snapshot) != _THRESHOLD_SNAPSHOT_FIELDS:
        raise PublicationError("PUBLICATION_INVALID")
    normalized = dict(snapshot)
    if normalized["currency"] != "CNY":
        raise PublicationError("PUBLICATION_INVALID")
    fixed = normalized["fixed"]
    if not isinstance(fixed, Mapping) or set(fixed) != _FIXED_THRESHOLD_FIELDS:
        raise PublicationError("PUBLICATION_INVALID")
    if (
        _require_integer(fixed.get("hard_fen"), "PUBLICATION_INVALID") != HARD_THRESHOLD_FEN
        or _require_integer(fixed.get("soft_fen"), "PUBLICATION_INVALID") != SOFT_THRESHOLD_FEN
    ):
        raise PublicationError("PUBLICATION_INVALID")
    if normalized["fixed_risk"] not in _FIXED_RISK_LABELS:
        raise PublicationError("PUBLICATION_INVALID")
    if normalized["dynamic_flag"] is not None and normalized["dynamic_flag"] not in _DYNAMIC_FLAGS:
        raise PublicationError("PUBLICATION_INVALID")
    floating = normalized["floating"]
    if not isinstance(floating, list):
        raise PublicationError("PUBLICATION_INVALID")
    names: set[str] = set()
    for item in floating:
        if not isinstance(item, Mapping) or set(item) != _FLOATING_LINE_FIELDS:
            raise PublicationError("PUBLICATION_INVALID")
        name = item.get("name")
        if not isinstance(name, str) or name not in _FLOATING_LINE_NAMES or name in names:
            raise PublicationError("PUBLICATION_INVALID")
        names.add(name)
        start = _require_iso_day(item.get("start"), "PUBLICATION_INVALID")
        end = _require_iso_day(item.get("end"), "PUBLICATION_INVALID")
        days = _require_integer(item.get("days"), "PUBLICATION_INVALID")
        if days <= 0 or end < start or days != (end - start).days + 1:
            raise PublicationError("PUBLICATION_INVALID")
        direct = _require_integer(item.get("direct_observations"), "PUBLICATION_INVALID")
        covered = _require_integer(item.get("covered_days"), "PUBLICATION_INVALID")
        carried = _require_integer(item.get("carried_forward_days"), "PUBLICATION_INVALID")
        if min(direct, covered, carried) < 0 or direct + carried != covered or covered > days:
            raise PublicationError("PUBLICATION_INVALID")
        coverage_text = item.get("coverage")
        if not isinstance(coverage_text, str) or not coverage_text:
            raise PublicationError("PUBLICATION_INVALID")
        try:
            coverage = Decimal(coverage_text)
        except InvalidOperation as exc:
            raise PublicationError("PUBLICATION_INVALID") from exc
        if not coverage.is_finite() or coverage < 0 or coverage > 1 or coverage != Decimal(covered) / Decimal(days):
            raise PublicationError("PUBLICATION_INVALID")
        active = _require_boolean(item.get("active"), "PUBLICATION_INVALID")
        threshold = item.get("threshold_fen")
        reason = item.get("reason")
        if active:
            if _require_integer(threshold, "PUBLICATION_INVALID") < 0 or reason is not None:
                raise PublicationError("PUBLICATION_INVALID")
        elif threshold is not None or not isinstance(reason, str) or not reason.strip():
            raise PublicationError("PUBLICATION_INVALID")
    return normalized


def _d1_parameters(params: Iterable[object]) -> list[str]:
    """Serialize Cloudflare D1 REST bindings to its documented string array.

    Integer-fen values remain exact decimal strings; SQLite INTEGER affinity
    restores them as integers at rest.  SQL NULL is emitted only as a fixed
    statement literal by the account projection below, never as an ambiguous
    JSON `null` parameter.
    """

    values: list[str] = []
    for value in params:
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, bool) or not isinstance(value, int):
            raise PublicationError("D1_PARAMETER_INVALID")
        else:
            values.append(str(value))
    return values


def _validate_publication(publication: Mapping[str, Any]) -> dict[str, Any]:
    """Reject an ambiguous publication before it reaches any read model.

    The private Git snapshot is immutable evidence.  D1, R2 and OCI must all
    carry the same canonical shape rather than accepting a permissive mapping
    that happens to contain a few familiar keys.
    """

    if not isinstance(publication, Mapping) or set(publication) != _PUBLICATION_FIELDS:
        raise PublicationError("PUBLICATION_INVALID")
    normalized = dict(publication)
    _require_lower_hex(normalized["publication_id"], 64, "PUBLICATION_INVALID")
    _require_iso_day(normalized["business_date"], "PUBLICATION_INVALID")
    if normalized["status"] != "VALID":
        raise PublicationError("PUBLICATION_NOT_PUBLISHABLE")
    difference = _require_integer(normalized["reconciliation_difference_fen"], "PUBLICATION_INVALID")
    if difference != 0:
        raise PublicationError("PUBLICATION_NOT_PUBLISHABLE")
    source_versions = normalized["source_versions"]
    if not isinstance(source_versions, list) or len(source_versions) != 2:
        raise PublicationError("PUBLICATION_INVALID")
    seen_versions: set[str] = set()
    for source in source_versions:
        if not isinstance(source, Mapping) or set(source) != {"source_version"}:
            raise PublicationError("PUBLICATION_INVALID")
        source_version = _require_lower_hex(source.get("source_version"), 64, "PUBLICATION_INVALID")
        if source_version in seen_versions:
            raise PublicationError("PUBLICATION_INVALID")
        seen_versions.add(source_version)
    normalized["threshold_snapshot"] = _validate_threshold_snapshot(normalized["threshold_snapshot"])
    _require_iso_timestamp(normalized["created_at"], "PUBLICATION_INVALID")
    _require_lower_hex(normalized["git_commit_sha"], 40, "PUBLICATION_INVALID")
    if normalized["d1_projection_version"] != "kmfa.daily_funds.d1.v1":
        raise PublicationError("PUBLICATION_INVALID")
    _require_lower_hex(normalized["r2_manifest_sha256"], 64, "PUBLICATION_INVALID")
    if normalized["oci_backup_state"] != "PENDING":
        # OCI is deliberately runtime state after publication.  Mutating the
        # canonical Git/D1 payload to claim a later backup result would break
        # content-addressed restore proofs.
        raise PublicationError("PUBLICATION_INVALID")
    return normalized


def _validate_daily_balances(
    balances: Iterable[DailyBalance],
    *,
    publication_day: date,
) -> tuple[DailyBalance, ...]:
    indexed: dict[date, DailyBalance] = {}
    for balance in balances:
        if not isinstance(balance, DailyBalance):
            raise PublicationError("PROJECTION_BALANCE_INVALID")
        day = balance.business_day
        if isinstance(day, datetime) or not isinstance(day, date) or day > publication_day:
            raise PublicationError("PROJECTION_BALANCE_INVALID")
        _require_integer(balance.ending_available_fen, "PROJECTION_BALANCE_NOT_INTEGER_FEN")
        direct = _require_boolean(balance.direct_observation, "PROJECTION_BALANCE_FLAG_INVALID")
        gap = _require_boolean(balance.coverage_gap, "PROJECTION_BALANCE_FLAG_INVALID")
        carried = _require_boolean(balance.carried_forward, "PROJECTION_BALANCE_FLAG_INVALID")
        if (direct and (gap or carried)) or (gap and carried) or (not direct and not gap and not carried):
            raise PublicationError("PROJECTION_BALANCE_CLASSIFICATION_INVALID")
        if day in indexed:
            raise PublicationError("PROJECTION_BALANCE_DUPLICATE")
        indexed[day] = balance
    current = indexed.get(publication_day)
    if current is None or not current.direct_observation or current.coverage_gap or current.carried_forward:
        raise PublicationError("PROJECTION_CURRENT_BALANCE_MISSING")
    return tuple(indexed[day] for day in sorted(indexed))


def _validate_transaction_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    publication_day: date,
) -> tuple[dict[str, Any], ...]:
    required = {
        "transaction_key_hash", "business_date", "inflow_fen", "outflow_fen", "adjustment_fen",
        "internal_transfer", "source_version", "message_id_hash",
    }
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != required:
            raise PublicationError("PROJECTION_TRANSACTION_INVALID")
        item = dict(row)
        key = _require_lower_hex(item["transaction_key_hash"], 64, "PROJECTION_TRANSACTION_INVALID")
        if key in seen:
            raise PublicationError("PROJECTION_TRANSACTION_DUPLICATE")
        seen.add(key)
        if _require_iso_day(item["business_date"], "PROJECTION_TRANSACTION_INVALID") != publication_day:
            raise PublicationError("PROJECTION_TRANSACTION_DATE_INVALID")
        inflow = _require_integer(item["inflow_fen"], "PROJECTION_TRANSACTION_NOT_INTEGER_FEN")
        outflow = _require_integer(item["outflow_fen"], "PROJECTION_TRANSACTION_NOT_INTEGER_FEN")
        _require_integer(item["adjustment_fen"], "PROJECTION_TRANSACTION_NOT_INTEGER_FEN")
        if inflow < 0 or outflow < 0 or (inflow and outflow):
            raise PublicationError("PROJECTION_TRANSACTION_FLOW_INVALID")
        _require_boolean(item["internal_transfer"], "PROJECTION_TRANSACTION_FLAG_INVALID")
        _require_lower_hex(item["source_version"], 64, "PROJECTION_TRANSACTION_INVALID")
        _require_lower_hex(item["message_id_hash"], 64, "PROJECTION_TRANSACTION_INVALID")
        normalized.append(item)
    if not normalized:
        raise PublicationError("PROJECTION_TRANSACTION_MISSING")
    return tuple(sorted(normalized, key=lambda item: str(item["transaction_key_hash"])))


def _validate_account_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    publication_day: date,
) -> tuple[dict[str, Any], ...]:
    required = {
        "account_key_hash", "business_date", "company_id", "bank_id", "account_alias",
        "opening_available_fen", "ending_available_fen", "source_version", "message_id_hash",
    }
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != required:
            raise PublicationError("PROJECTION_ACCOUNT_INVALID")
        item = dict(row)
        key = _require_lower_hex(item["account_key_hash"], 64, "PROJECTION_ACCOUNT_INVALID")
        if key in seen:
            raise PublicationError("PROJECTION_ACCOUNT_DUPLICATE")
        seen.add(key)
        if _require_iso_day(item["business_date"], "PROJECTION_ACCOUNT_INVALID") != publication_day:
            raise PublicationError("PROJECTION_ACCOUNT_DATE_INVALID")
        _require_text(item["company_id"], "PROJECTION_ACCOUNT_INVALID")
        _require_text(item["bank_id"], "PROJECTION_ACCOUNT_INVALID")
        if item["account_alias"] != key:
            raise PublicationError("PROJECTION_ACCOUNT_ALIAS_INVALID")
        opening = item["opening_available_fen"]
        if opening is not None:
            _require_integer(opening, "PROJECTION_ACCOUNT_NOT_INTEGER_FEN")
        _require_integer(item["ending_available_fen"], "PROJECTION_ACCOUNT_NOT_INTEGER_FEN")
        _require_lower_hex(item["source_version"], 64, "PROJECTION_ACCOUNT_INVALID")
        _require_lower_hex(item["message_id_hash"], 64, "PROJECTION_ACCOUNT_INVALID")
        normalized.append(item)
    if not normalized:
        raise PublicationError("PROJECTION_ACCOUNT_MISSING")
    return tuple(sorted(normalized, key=lambda item: str(item["account_key_hash"])))


def _validate_projection_inputs(
    publication: Mapping[str, Any],
    balances: Iterable[DailyBalance],
    transactions: Iterable[Mapping[str, Any]],
    accounts: Iterable[Mapping[str, Any]],
) -> tuple[dict[str, Any], tuple[DailyBalance, ...], tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    normalized_publication = _validate_publication(publication)
    publication_day = _require_iso_day(normalized_publication["business_date"], "PUBLICATION_INVALID")
    normalized_balances = _validate_daily_balances(balances, publication_day=publication_day)
    normalized_transactions = _validate_transaction_rows(transactions, publication_day=publication_day)
    normalized_accounts = _validate_account_rows(accounts, publication_day=publication_day)
    declared_versions = {str(row["source_version"]) for row in normalized_publication["source_versions"]}
    transaction_versions = {str(row["source_version"]) for row in normalized_transactions}
    account_versions = {str(row["source_version"]) for row in normalized_accounts}
    if len(transaction_versions) != 1 or len(account_versions) != 1 or transaction_versions == account_versions:
        raise PublicationError("PROJECTION_SOURCE_VERSION_PAIR_INVALID")
    projected_versions = transaction_versions | account_versions
    if projected_versions != declared_versions:
        raise PublicationError("PROJECTION_SOURCE_VERSION_MISMATCH")
    expected_ending = sum(int(row["ending_available_fen"]) for row in normalized_accounts)
    current_balance = next(balance for balance in normalized_balances if balance.business_day == publication_day)
    if current_balance.ending_available_fen != expected_ending:
        raise PublicationError("PROJECTION_RECONCILIATION_FAILED")
    threshold = normalized_publication["threshold_snapshot"]
    if threshold["fixed_risk"] != fixed_risk(expected_ending):
        raise PublicationError("PROJECTION_THRESHOLD_MISMATCH")
    active_thresholds = [
        int(line["threshold_fen"])
        for line in threshold["floating"]
        if line["active"]
    ]
    if threshold["dynamic_flag"] != dynamic_flag(expected_ending, active_thresholds):
        raise PublicationError("PROJECTION_THRESHOLD_MISMATCH")
    return normalized_publication, normalized_balances, normalized_transactions, normalized_accounts


def _validate_report_matches_projection(
    report: ReconciliationReport,
    *,
    publication: Mapping[str, Any],
    account_rows: Iterable[Mapping[str, Any]],
) -> None:
    """Bind UI summary totals to the exact D1 account projection.

    ``ReconciliationReport`` is the user-facing aggregate and D1 receives
    independent projection rows.  They originate from the same parser in the
    runtime, but this boundary must fail closed for direct callers, fakes and
    future refactors so a valid-looking pointer can never publish a different
    set of account totals from the one queryable in D1.
    """

    accounts = tuple(account_rows)
    publication_day = _require_iso_day(publication.get("business_date"), "PROJECTION_REPORT_MISMATCH")
    if report.business_date != publication_day:
        raise PublicationError("PROJECTION_REPORT_MISMATCH")
    expected_accounts = {
        _require_lower_hex(row.get("account_key_hash"), 64, "PROJECTION_REPORT_MISMATCH"):
        _require_integer(row.get("ending_available_fen"), "PROJECTION_REPORT_MISMATCH")
        for row in accounts
    }
    if len(expected_accounts) != len(accounts):
        # `_validate_projection_inputs` has already rejected duplicate rows;
        # retain a local fail-closed guard in case this helper is reused.
        raise PublicationError("PROJECTION_REPORT_MISMATCH")
    expected_total = sum(expected_accounts.values())
    if _require_integer(report.total_ending_fen, "PROJECTION_REPORT_MISMATCH") != expected_total:
        raise PublicationError("PROJECTION_REPORT_MISMATCH")
    report_accounts: dict[str, int] = {}
    for item in report.account_reports:
        account_hash = _require_lower_hex(item.account_key_hash, 64, "PROJECTION_REPORT_MISMATCH")
        if account_hash in report_accounts:
            raise PublicationError("PROJECTION_REPORT_MISMATCH")
        report_accounts[account_hash] = _require_integer(item.ending_fen, "PROJECTION_REPORT_MISMATCH")
    if report_accounts != expected_accounts:
        raise PublicationError("PROJECTION_REPORT_MISMATCH")

    def expected_totals(key: str) -> dict[str, int]:
        totals: dict[str, int] = {}
        for row in accounts:
            value = _require_text(row.get(key), "PROJECTION_REPORT_MISMATCH")
            ending = _require_integer(row.get("ending_available_fen"), "PROJECTION_REPORT_MISMATCH")
            totals[value] = totals.get(value, 0) + ending
        return totals

    def report_totals(value: object) -> dict[str, int]:
        if not isinstance(value, Mapping):
            raise PublicationError("PROJECTION_REPORT_MISMATCH")
        normalized: dict[str, int] = {}
        for key, amount in value.items():
            normalized[_require_text(key, "PROJECTION_REPORT_MISMATCH")] = _require_integer(
                amount,
                "PROJECTION_REPORT_MISMATCH",
            )
        return normalized

    if report_totals(report.by_company_ending_fen) != expected_totals("company_id"):
        raise PublicationError("PROJECTION_REPORT_MISMATCH")
    if report_totals(report.by_bank_ending_fen) != expected_totals("bank_id"):
        raise PublicationError("PROJECTION_REPORT_MISMATCH")


class D1Projection:
    """Small Cloudflare D1 REST client; no raw attachment bytes enter D1."""

    def __init__(self, config: DailyFundsConfig):
        self.config = config
        self.url = (
            f"https://api.cloudflare.com/client/v4/accounts/{config.cf_account_id}"
            f"/d1/database/{config.d1_database_id}/query"
        )

    def _query(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        decoded = self._request({"sql": sql, "params": _d1_parameters(params or [])})
        result = decoded.get("result")
        if isinstance(result, list) and result:
            first = result[0]
            if isinstance(first, Mapping) and isinstance(first.get("results"), list):
                return [dict(row) for row in first["results"] if isinstance(row, Mapping)]
        return []

    def _request(self, payload: object) -> Mapping[str, Any]:
        body = _canonical_bytes(payload)
        request = urllib.request.Request(
            self.url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.config.cf_api_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                decoded = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            raise PublicationError("D1_FAILED") from exc
        if not isinstance(decoded, Mapping) or decoded.get("success") is not True:
            raise PublicationError("D1_FAILED")
        # Cloudflare wraps a multi-statement request in a successful outer API
        # response even when an individual statement reports failure.  A
        # publication may not treat that partial result as a D1 transaction.
        result = decoded.get("result")
        if not isinstance(result, list) or any(
            not isinstance(item, Mapping) or item.get("success") is not True
            for item in result
        ):
            raise PublicationError("D1_FAILED")
        return decoded

    def _batch(self, statements: Iterable[tuple[str, list[Any]]]) -> None:
        # Cloudflare D1 executes a query batch as one transaction.  If a D1
        # endpoint rejects the batch shape, the method fails closed before the
        # public pointer is touched; it never degrades to partial row writes.
        statements_payload = [{"sql": sql, "params": _d1_parameters(params)} for sql, params in statements]
        if not statements_payload:
            return
        # Cloudflare's REST API accepts ``{batch:[...]}``, not a bare JSON
        # array.  Keep this explicitly shaped and tested because a rejected
        # batch must fail before any publication pointer can move.
        self._request({"batch": statements_payload})

    def ensure_schema(self) -> None:
        statements = (
            """CREATE TABLE IF NOT EXISTS daily_funds_publications (
                publication_id TEXT PRIMARY KEY, business_date TEXT NOT NULL,
                status TEXT NOT NULL, reconciliation_difference_fen INTEGER NOT NULL,
                git_commit_sha TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS daily_funds_daily_balances (
                publication_id TEXT NOT NULL, business_date TEXT NOT NULL, scope TEXT NOT NULL,
                ending_available_fen INTEGER NOT NULL, direct_observation INTEGER NOT NULL,
                coverage_gap INTEGER NOT NULL, carried_forward INTEGER NOT NULL,
                PRIMARY KEY (publication_id, business_date, scope)
            )""",
            """CREATE TABLE IF NOT EXISTS daily_funds_transactions (
                publication_id TEXT NOT NULL, transaction_key_hash TEXT NOT NULL,
                business_date TEXT NOT NULL, inflow_fen INTEGER NOT NULL, outflow_fen INTEGER NOT NULL,
                adjustment_fen INTEGER NOT NULL, internal_transfer INTEGER NOT NULL,
                source_version TEXT NOT NULL, message_id_hash TEXT NOT NULL,
                PRIMARY KEY (publication_id, transaction_key_hash)
            )""",
            """CREATE TABLE IF NOT EXISTS daily_funds_account_snapshots (
                publication_id TEXT NOT NULL, account_key_hash TEXT NOT NULL,
                business_date TEXT NOT NULL, company_id TEXT NOT NULL,
                bank_id TEXT NOT NULL, account_alias TEXT NOT NULL,
                opening_available_fen INTEGER, ending_available_fen INTEGER NOT NULL,
                source_version TEXT NOT NULL, message_id_hash TEXT NOT NULL,
                PRIMARY KEY (publication_id, account_key_hash)
            )""",
        )
        for statement in statements:
            self._query(statement)

    def project(
        self,
        publication: Mapping[str, Any],
        daily_balances: Iterable[DailyBalance],
        transaction_rows: Iterable[Mapping[str, Any]],
        account_rows: Iterable[Mapping[str, Any]],
    ) -> None:
        publication, balances, transactions, accounts = _validate_projection_inputs(
            publication,
            daily_balances,
            transaction_rows,
            account_rows,
        )
        self.ensure_schema()
        publication_id = str(publication["publication_id"])
        statements: list[tuple[str, list[Any]]] = [
            ("DELETE FROM daily_funds_daily_balances WHERE publication_id=?", [publication_id]),
            ("DELETE FROM daily_funds_transactions WHERE publication_id=?", [publication_id]),
            ("DELETE FROM daily_funds_account_snapshots WHERE publication_id=?", [publication_id]),
            (
                """INSERT INTO daily_funds_publications
                (publication_id,business_date,status,reconciliation_difference_fen,git_commit_sha,payload_json,created_at)
                VALUES(?,?,?,?,?,?,?)""",
                [
                    publication_id,
                    publication["business_date"],
                    publication["status"],
                    publication["reconciliation_difference_fen"],
                    publication["git_commit_sha"],
                    _canonical_bytes(publication).decode("utf-8"),
                    publication["created_at"],
                ],
            ),
        ]
        for balance in balances:
            statements.append((
                """INSERT INTO daily_funds_daily_balances
                (publication_id,business_date,scope,ending_available_fen,direct_observation,coverage_gap,carried_forward)
                VALUES(?,?,?,?,?,?,?)""",
                [
                    publication_id,
                    balance.business_day.isoformat(),
                    "global",
                    balance.ending_available_fen,
                    int(balance.direct_observation),
                    int(balance.coverage_gap),
                    int(balance.carried_forward),
                ],
            ))
        for row in transactions:
            statements.append((
                """INSERT INTO daily_funds_transactions
                (publication_id,transaction_key_hash,business_date,inflow_fen,outflow_fen,adjustment_fen,internal_transfer,source_version,message_id_hash)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                [
                    publication_id,
                    row["transaction_key_hash"],
                    row["business_date"],
                    row["inflow_fen"],
                    row["outflow_fen"],
                    row["adjustment_fen"],
                    int(bool(row["internal_transfer"])),
                    row["source_version"],
                    row["message_id_hash"],
                ],
            ))
        for row in accounts:
            if row.get("opening_available_fen") is None:
                statements.append((
                    """INSERT INTO daily_funds_account_snapshots
                    (publication_id,account_key_hash,business_date,company_id,bank_id,account_alias,
                     opening_available_fen,ending_available_fen,source_version,message_id_hash)
                    VALUES(?,?,?,?,?,?,NULL,?,?,?)""",
                    [
                        publication_id,
                        row["account_key_hash"],
                        row["business_date"],
                        row["company_id"],
                        row["bank_id"],
                        row["account_alias"],
                        row["ending_available_fen"],
                        row["source_version"],
                        row["message_id_hash"],
                    ],
                ))
            else:
                statements.append((
                    """INSERT INTO daily_funds_account_snapshots
                    (publication_id,account_key_hash,business_date,company_id,bank_id,account_alias,
                     opening_available_fen,ending_available_fen,source_version,message_id_hash)
                    VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    [
                        publication_id,
                        row["account_key_hash"],
                        row["business_date"],
                        row["company_id"],
                        row["bank_id"],
                        row["account_alias"],
                        row["opening_available_fen"],
                        row["ending_available_fen"],
                        row["source_version"],
                        row["message_id_hash"],
                    ],
                ))
        self._batch(statements)

    def oracle(self, publication_id: str) -> Mapping[str, Any]:
        _require_lower_hex(publication_id, 64, "D1_ORACLE_PUBLICATION_INVALID")
        rows = self._query(
            """SELECT publication_id,business_date,status,reconciliation_difference_fen,
               git_commit_sha,payload_json,created_at
               FROM daily_funds_publications WHERE publication_id=?""",
            [publication_id],
        )
        if len(rows) != 1:
            raise PublicationError("D1_ORACLE_MISSING")
        row = rows[0]
        if row.get("status") != "VALID" or _require_integer(row.get("reconciliation_difference_fen"), "D1_ORACLE_RECONCILIATION_FAILED") != 0:
            raise PublicationError("D1_ORACLE_RECONCILIATION_FAILED")
        try:
            payload_json = _require_text(row["payload_json"], "D1_ORACLE_PUBLICATION_INVALID")
            publication = _validate_publication(json.loads(payload_json))
            business_date = str(publication["business_date"])
        except (KeyError, TypeError, json.JSONDecodeError, PublicationError) as exc:
            raise PublicationError("D1_ORACLE_PUBLICATION_INVALID") from exc
        if (
            _canonical_bytes(publication).decode("utf-8") != payload_json
            or publication.get("publication_id") != publication_id
            or row.get("business_date") != publication.get("business_date")
            or row.get("status") != publication.get("status")
            or row.get("git_commit_sha") != publication.get("git_commit_sha")
            or row.get("created_at") != publication.get("created_at")
        ):
            raise PublicationError("D1_ORACLE_PUBLICATION_INVALID")
        # Receipt success says D1 accepted the batch, not that every critical
        # projection row is queryable or coherent.  This read-back Oracle
        # proves both fact families arrived and that their account total equals
        # the daily-balance read model that will feed the owner UI.
        checks = self._query(
            """SELECT
                 (SELECT COUNT(*) FROM daily_funds_account_snapshots
                   WHERE publication_id=? AND business_date=?) AS account_count,
                 (SELECT COUNT(*) FROM daily_funds_transactions
                   WHERE publication_id=? AND business_date=?) AS transaction_count,
                 (SELECT COALESCE(SUM(ending_available_fen),0) FROM daily_funds_account_snapshots
                   WHERE publication_id=? AND business_date=?) AS account_ending_fen,
                 (SELECT COUNT(*) FROM daily_funds_daily_balances
                   WHERE publication_id=? AND business_date=? AND scope='global') AS balance_count,
                 (SELECT ending_available_fen FROM daily_funds_daily_balances
                   WHERE publication_id=? AND business_date=? AND scope='global') AS balance_ending_fen""",
            [publication_id, business_date, publication_id, business_date, publication_id, business_date,
             publication_id, business_date, publication_id, business_date],
        )
        if len(checks) != 1:
            raise PublicationError("D1_ORACLE_PROJECTION_MISSING")
        check = checks[0]
        try:
            account_count = _require_integer(check["account_count"], "D1_ORACLE_PROJECTION_MISSING")
            transaction_count = _require_integer(check["transaction_count"], "D1_ORACLE_PROJECTION_MISSING")
            balance_count = _require_integer(check["balance_count"], "D1_ORACLE_PROJECTION_MISSING")
            account_ending = _require_integer(check["account_ending_fen"], "D1_ORACLE_PROJECTION_MISSING")
            balance_ending = _require_integer(check["balance_ending_fen"], "D1_ORACLE_PROJECTION_MISSING")
        except (KeyError, PublicationError) as exc:
            raise PublicationError("D1_ORACLE_PROJECTION_MISSING") from exc
        if account_count < 1 or transaction_count < 1 or balance_count != 1:
            raise PublicationError("D1_ORACLE_PROJECTION_MISSING")
        if account_ending != balance_ending:
            raise PublicationError("D1_ORACLE_RECONCILIATION_FAILED")
        return row

    def export(self, publication_id: str) -> bytes:
        row = self.oracle(publication_id)
        balances = self._query(
            "SELECT business_date,scope,ending_available_fen,direct_observation,coverage_gap,carried_forward FROM daily_funds_daily_balances WHERE publication_id=? ORDER BY business_date",
            [publication_id],
        )
        transactions = self._query(
            "SELECT transaction_key_hash,business_date,inflow_fen,outflow_fen,adjustment_fen,internal_transfer,source_version,message_id_hash FROM daily_funds_transactions WHERE publication_id=? ORDER BY transaction_key_hash",
            [publication_id],
        )
        accounts = self._query(
            "SELECT account_key_hash,business_date,company_id,bank_id,account_alias,opening_available_fen,ending_available_fen,source_version,message_id_hash FROM daily_funds_account_snapshots WHERE publication_id=? ORDER BY account_key_hash",
            [publication_id],
        )
        return _canonical_bytes({"publication": row, "daily_balances": balances, "transactions": transactions, "account_snapshots": accounts})


class ObjectStore(Protocol):
    def put_bytes(self, key: str, payload: bytes, *, metadata: Mapping[str, str] | None = None) -> None: ...
    def get_bytes(self, key: str) -> bytes: ...


class S3CompatibleStore:
    """Used for both Cloudflare R2 and OCI Object Storage endpoints."""

    def __init__(self, *, endpoint_url: str, bucket: str, access_key_id: str, secret_access_key: str, region: str):
        try:
            import boto3  # type: ignore[import-not-found]
            from botocore.config import Config  # type: ignore[import-not-found]
        except ImportError as exc:
            raise PublicationError("OBJECT_STORE_RUNTIME_DEPENDENCY_MISSING") from exc
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
            config=Config(s3={"addressing_style": "path"}),
        )

    def put_bytes(self, key: str, payload: bytes, *, metadata: Mapping[str, str] | None = None) -> None:
        try:
            self.client.put_object(Bucket=self.bucket, Key=key, Body=payload, Metadata=dict(metadata or {}))
            head = self.client.head_object(Bucket=self.bucket, Key=key)
        except Exception as exc:
            raise PublicationError("OBJECT_STORE_FAILED") from exc
        if int(head.get("ContentLength", -1)) != len(payload):
            raise PublicationError("OBJECT_STORE_READBACK_FAILED")
        expected_sha = str((metadata or {}).get("sha256") or "")
        actual_sha = str((head.get("Metadata") or {}).get("sha256") or "")
        if expected_sha and actual_sha != expected_sha:
            raise PublicationError("OBJECT_STORE_READBACK_FAILED")

    def get_bytes(self, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except Exception as exc:
            raise PublicationError("OBJECT_STORE_FAILED") from exc


class OciParStore:
    """Bucket-scoped OCI Pre-Authenticated Request object store.

    This avoids distributing a user-level OCI HMAC key to the container.  The
    supplied PAR must be an HTTPS ``AnyObjectReadWrite`` URI rooted at its
    ``/o/`` object prefix; every write is still read back and hash-verified by
    :class:`OciColdBackup` before it can be considered a recovery artifact.
    """

    def __init__(self, *, par_url: str):
        parsed = urllib.parse.urlsplit(par_url)
        path = parsed.path
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or not path.endswith("/o/")
            or not all(marker in path for marker in ("/p/", "/n/", "/b/", "/o/"))
        ):
            raise PublicationError("OCI_PAR_URL_INVALID")
        self._base_url = par_url.rstrip("/") + "/"

    def _object_url(self, key: str) -> str:
        if (
            not isinstance(key, str)
            or not key
            or key.startswith("/")
            or any(part in {"", ".", ".."} for part in key.split("/"))
        ):
            raise PublicationError("OBJECT_STORE_FAILED")
        return self._base_url + urllib.parse.quote(key, safe="/")

    @staticmethod
    def _response_status(response: object) -> int:
        status = getattr(response, "status", None)
        if isinstance(status, int):
            return status
        getcode = getattr(response, "getcode", None)
        return int(getcode()) if callable(getcode) else 0

    def put_bytes(self, key: str, payload: bytes, *, metadata: Mapping[str, str] | None = None) -> None:
        if not isinstance(payload, bytes):
            raise PublicationError("OBJECT_STORE_FAILED")
        headers = {"Content-Type": "application/octet-stream"}
        for name, value in dict(metadata or {}).items():
            if (
                not isinstance(name, str)
                or not isinstance(value, str)
                or not name.replace("-", "").isalnum()
                or any(character in value for character in ("\r", "\n"))
            ):
                raise PublicationError("OBJECT_STORE_FAILED")
            headers[f"opc-meta-{name}"] = value
        try:
            request = urllib.request.Request(
                self._object_url(key),
                data=payload,
                method="PUT",
                headers=headers,
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                if self._response_status(response) not in {200, 201, 204}:
                    raise PublicationError("OBJECT_STORE_FAILED")
        except PublicationError:
            raise
        except Exception as exc:
            raise PublicationError("OBJECT_STORE_FAILED") from exc

    def get_bytes(self, key: str) -> bytes:
        try:
            with urllib.request.urlopen(self._object_url(key), timeout=30) as response:
                if self._response_status(response) != 200:
                    raise PublicationError("OBJECT_STORE_FAILED")
                payload = response.read()
        except PublicationError:
            raise
        except Exception as exc:
            raise PublicationError("OBJECT_STORE_FAILED") from exc
        if not isinstance(payload, bytes):
            raise PublicationError("OBJECT_STORE_FAILED")
        return payload


class R2Mirror:
    def __init__(self, store: ObjectStore):
        self.store = store

    @staticmethod
    def _attachment_hashes(attachments: Iterable[DownloadedAttachment]) -> tuple[DownloadedAttachment, ...]:
        unique: dict[str, DownloadedAttachment] = {}
        for attachment in attachments:
            if not isinstance(attachment, DownloadedAttachment) or not isinstance(attachment.payload, bytes):
                raise PublicationError("R2_ATTACHMENT_INVALID")
            digest = _require_lower_hex(attachment.sha256, 64, "R2_ATTACHMENT_INVALID")
            if sha256(attachment.payload).hexdigest() != digest:
                raise PublicationError("R2_ATTACHMENT_HASH_MISMATCH")
            existing = unique.get(digest)
            if existing is not None and existing.payload != attachment.payload:
                raise PublicationError("R2_ATTACHMENT_HASH_MISMATCH")
            unique.setdefault(digest, attachment)
        return tuple(unique[digest] for digest in sorted(unique))

    @staticmethod
    def validate_manifest_payload(
        manifest_sha: str,
        payload: bytes,
        *,
        expected_git_commit_sha: str,
        expected_attachment_hashes: Iterable[str] | None = None,
    ) -> Mapping[str, Any]:
        _require_lower_hex(manifest_sha, 64, "R2_MANIFEST_INVALID")
        _require_lower_hex(expected_git_commit_sha, 40, "R2_MANIFEST_INVALID")
        if not isinstance(payload, bytes) or sha256(payload).hexdigest() != manifest_sha:
            raise PublicationError("R2_MANIFEST_HASH_MISMATCH")
        try:
            manifest = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PublicationError("R2_MANIFEST_INVALID") from exc
        if not isinstance(manifest, Mapping) or set(manifest) != _R2_MANIFEST_FIELDS:
            raise PublicationError("R2_MANIFEST_INVALID")
        if manifest.get("schema_version") != "kmfa.daily_funds.r2_manifest.v1":
            raise PublicationError("R2_MANIFEST_INVALID")
        if manifest.get("git_commit_sha") != expected_git_commit_sha:
            raise PublicationError("R2_MANIFEST_GIT_MISMATCH")
        _require_iso_timestamp(manifest.get("created_at"), "R2_MANIFEST_INVALID")
        objects = manifest.get("objects")
        if not isinstance(objects, list):
            raise PublicationError("R2_MANIFEST_INVALID")
        seen: set[str] = set()
        normalized: list[tuple[str, int]] = []
        for row in objects:
            if not isinstance(row, Mapping) or set(row) != {"key", "sha256", "size_bytes"}:
                raise PublicationError("R2_MANIFEST_INVALID")
            digest = _require_lower_hex(row.get("sha256"), 64, "R2_MANIFEST_INVALID")
            key = row.get("key")
            size = _require_integer(row.get("size_bytes"), "R2_MANIFEST_INVALID")
            if key != f"daily-funds/sha256/{digest}" or size < 0 or digest in seen:
                raise PublicationError("R2_MANIFEST_INVALID")
            seen.add(digest)
            normalized.append((digest, size))
        if normalized != sorted(normalized, key=lambda item: item[0]):
            raise PublicationError("R2_MANIFEST_INVALID")
        if expected_attachment_hashes is not None:
            expected = {_require_lower_hex(digest, 64, "R2_ATTACHMENT_INVALID") for digest in expected_attachment_hashes}
            if seen != expected:
                raise PublicationError("R2_MANIFEST_ATTACHMENT_MISMATCH")
        return manifest

    def _put_and_verify(self, key: str, payload: bytes, *, digest: str) -> bytes:
        try:
            self.store.put_bytes(key, payload, metadata={"sha256": digest})
            readback = self.store.get_bytes(key)
        except Exception as exc:
            raise PublicationError("R2_READBACK_FAILED") from exc
        if not isinstance(readback, bytes) or len(readback) != len(payload) or sha256(readback).hexdigest() != digest:
            raise PublicationError("R2_READBACK_FAILED")

    def mirror(self, attachments: Iterable[DownloadedAttachment], *, git_commit_sha: str) -> tuple[str, bytes]:
        git_commit_sha = _require_lower_hex(git_commit_sha, 40, "R2_MANIFEST_INVALID")
        verified_attachments = self._attachment_hashes(attachments)
        rows: list[dict[str, Any]] = []
        for attachment in verified_attachments:
            key = f"daily-funds/sha256/{attachment.sha256}"
            self._put_and_verify(key, attachment.payload, digest=attachment.sha256)
            rows.append({"key": key, "sha256": attachment.sha256, "size_bytes": len(attachment.payload)})
        manifest = {
            "schema_version": "kmfa.daily_funds.r2_manifest.v1",
            "git_commit_sha": git_commit_sha,
            "objects": sorted(rows, key=lambda row: str(row["sha256"])),
            "created_at": iso_now(),
        }
        payload = _canonical_bytes(manifest)
        manifest_sha = sha256(payload).hexdigest()
        self._put_and_verify(f"daily-funds/manifests/{manifest_sha}.json", payload, digest=manifest_sha)
        self.validate_manifest_payload(
            manifest_sha,
            payload,
            expected_git_commit_sha=git_commit_sha,
            expected_attachment_hashes=(attachment.sha256 for attachment in verified_attachments),
        )
        return manifest_sha, payload

    def verify_manifest(
        self,
        manifest_sha: str,
        *,
        expected_git_commit_sha: str,
        expected_attachment_hashes: Iterable[str] | None = None,
    ) -> bytes:
        _require_lower_hex(manifest_sha, 64, "R2_MANIFEST_INVALID")
        try:
            payload = self.store.get_bytes(f"daily-funds/manifests/{manifest_sha}.json")
        except Exception as exc:
            raise PublicationError("R2_READBACK_FAILED") from exc
        manifest = self.validate_manifest_payload(
            manifest_sha,
            payload,
            expected_git_commit_sha=expected_git_commit_sha,
            expected_attachment_hashes=expected_attachment_hashes,
        )
        for row in manifest["objects"]:
            try:
                object_payload = self.store.get_bytes(str(row["key"]))
            except Exception as exc:
                raise PublicationError("R2_READBACK_FAILED") from exc
            if (
                not isinstance(object_payload, bytes)
                or len(object_payload) != row["size_bytes"]
                or sha256(object_payload).hexdigest() != row["sha256"]
            ):
                raise PublicationError("R2_READBACK_FAILED")
        return payload


class OciColdBackup:
    def __init__(self, store: ObjectStore):
        self.store = store

    def _put_and_verify(self, key: str, payload: bytes, *, digest: str) -> None:
        try:
            self.store.put_bytes(key, payload, metadata={"sha256": digest})
            readback = self.store.get_bytes(key)
        except Exception as exc:
            raise PublicationError("OCI_BACKUP_READBACK_FAILED") from exc
        if not isinstance(readback, bytes) or len(readback) != len(payload) or sha256(readback).hexdigest() != digest:
            raise PublicationError("OCI_BACKUP_READBACK_FAILED")
        return readback

    def backup(
        self,
        *,
        publication_id: str,
        publication_sha256: str,
        publication_created_at: str,
        git_publication_commit_sha: str,
        git_bundle: bytes,
        d1_export: bytes,
        r2_inventory: bytes,
    ) -> str:
        publication_id = _require_lower_hex(publication_id, 64, "OCI_BACKUP_INVALID")
        publication_sha256 = _require_lower_hex(publication_sha256, 64, "OCI_BACKUP_INVALID")
        publication_created_at = _require_iso_timestamp(publication_created_at, "OCI_BACKUP_INVALID")
        git_publication_commit_sha = _require_lower_hex(git_publication_commit_sha, 40, "OCI_BACKUP_INVALID")
        if not all(isinstance(payload, bytes) and payload for payload in (git_bundle, d1_export, r2_inventory)):
            raise PublicationError("OCI_BACKUP_INVALID")
        artifacts = {
            "git_bundle": git_bundle,
            "d1_export": d1_export,
            "r2_inventory": r2_inventory,
        }
        inventory = {
            name: {"key": f"daily-funds/{publication_id}/{name}", "sha256": sha256(payload).hexdigest(), "size_bytes": len(payload)}
            for name, payload in artifacts.items()
        }
        manifest = {
            "schema_version": "kmfa.daily_funds.oci_restore_manifest.v1",
            "publication_id": publication_id,
            "publication_sha256": publication_sha256,
            "git_publication_commit_sha": git_publication_commit_sha,
            "artifacts": inventory,
            # The restore manifest is content-addressed by a specific
            # immutable publication.  Reusing the publication timestamp,
            # rather than backup-attempt time, makes a retry with the same
            # artifacts byte-identical instead of mutating its recovery set.
            "created_at": publication_created_at,
        }
        manifest_payload = _canonical_bytes(manifest)
        inventory["restore_manifest"] = {
            "key": f"daily-funds/{publication_id}/restore_manifest.json",
            "sha256": sha256(manifest_payload).hexdigest(),
            "size_bytes": len(manifest_payload),
        }
        verified_artifacts = {
            name: self._put_and_verify(inventory[name]["key"], payload, digest=inventory[name]["sha256"])
            for name, payload in artifacts.items()
        }
        # Do not write a restore manifest (and therefore do not report a
        # successful cold backup) until the just-read-back artifacts can prove
        # the complete private publication chain.  A raw-source commit alone
        # is insufficient: the canonical publication file must be present in
        # the bundle and byte-identical to the D1 export.
        try:
            restored_publication, _, _, _ = RestoreOracle.decode_d1_export(
                verified_artifacts["d1_export"],
                publication_id=publication_id,
                expected_publication_sha=publication_sha256,
            )
            R2Mirror.validate_manifest_payload(
                str(restored_publication["r2_manifest_sha256"]),
                verified_artifacts["r2_inventory"],
                expected_git_commit_sha=str(restored_publication["git_commit_sha"]),
            )
            RestoreOracle.verify_private_publication_bundle(
                verified_artifacts["git_bundle"],
                expected_raw_commit_sha=str(restored_publication["git_commit_sha"]),
                expected_publication_commit_sha=git_publication_commit_sha,
                publication=restored_publication,
            )
        except (KeyError, PublicationError) as exc:
            raise PublicationError("OCI_BACKUP_INVALID") from exc
        self._put_and_verify(
            inventory["restore_manifest"]["key"],
            manifest_payload,
            digest=inventory["restore_manifest"]["sha256"],
        )
        return inventory["restore_manifest"]["sha256"]

    def restore_artifacts(self, publication_id: str) -> tuple[Mapping[str, Any], Mapping[str, bytes]]:
        """Fetch and hash-verify the immutable OCI restore set.

        This method does not mutate D1 or the UI pointer.  Callers can run it
        in an empty environment, then make the pointer swap only after the D1
        rebuild Oracle succeeds.
        """

        publication_id = _require_lower_hex(publication_id, 64, "RESTORE_MANIFEST_INVALID")
        key = f"daily-funds/{publication_id}/restore_manifest.json"
        try:
            manifest_payload = self.store.get_bytes(key)
        except Exception as exc:
            raise PublicationError("RESTORE_MANIFEST_UNAVAILABLE") from exc
        if not isinstance(manifest_payload, bytes):
            raise PublicationError("RESTORE_MANIFEST_UNAVAILABLE")
        try:
            manifest = json.loads(manifest_payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PublicationError("RESTORE_MANIFEST_UNAVAILABLE") from exc
        if (
            not isinstance(manifest, Mapping)
            or set(manifest) != _OCI_MANIFEST_FIELDS
            or _canonical_bytes(manifest) != manifest_payload
            or manifest.get("schema_version") != "kmfa.daily_funds.oci_restore_manifest.v1"
            or manifest.get("publication_id") != publication_id
        ):
            raise PublicationError("RESTORE_MANIFEST_INVALID")
        _require_lower_hex(manifest.get("publication_sha256"), 64, "RESTORE_MANIFEST_INVALID")
        _require_lower_hex(manifest.get("git_publication_commit_sha"), 40, "RESTORE_MANIFEST_INVALID")
        _require_iso_timestamp(manifest.get("created_at"), "RESTORE_MANIFEST_INVALID")
        inventory = manifest.get("artifacts")
        if not isinstance(inventory, Mapping) or set(inventory) != {"git_bundle", "d1_export", "r2_inventory"}:
            raise PublicationError("RESTORE_MANIFEST_INVALID")
        recovered: dict[str, bytes] = {}
        for name in ("git_bundle", "d1_export", "r2_inventory"):
            descriptor = inventory.get(name)
            if not isinstance(descriptor, Mapping):
                raise PublicationError("RESTORE_MANIFEST_INVALID")
            object_key = descriptor.get("key")
            expected_sha = descriptor.get("sha256")
            expected_size = descriptor.get("size_bytes")
            if (
                object_key != f"daily-funds/{publication_id}/{name}"
                or not _is_lower_hex(expected_sha, 64)
                or isinstance(expected_size, bool)
                or not isinstance(expected_size, int)
                or expected_size <= 0
            ):
                raise PublicationError("RESTORE_MANIFEST_INVALID")
            try:
                payload = self.store.get_bytes(object_key)
            except Exception as exc:
                raise PublicationError("RESTORE_ARTIFACT_UNAVAILABLE") from exc
            if (
                not isinstance(payload, bytes)
                or len(payload) != expected_size
                or sha256(payload).hexdigest() != expected_sha
            ):
                raise PublicationError("RESTORE_ARTIFACT_HASH_MISMATCH")
            recovered[name] = payload
        return manifest, recovered


@dataclass(frozen=True)
class PublishedProjection:
    publication: Mapping[str, Any]
    snapshot: Mapping[str, Any]
    oci_backup_state: str
    oci_restore_manifest_sha: str | None


class PublicationCoordinator:
    """Implements the no-premature-pointer publication protocol."""

    def __init__(
        self,
        *,
        publication_dir: str | Path,
        status: StatusWriter,
        d1: D1Projection,
        r2: R2Mirror,
        oci: OciColdBackup,
    ):
        self.publication_dir = Path(publication_dir)
        self.status = status
        self.d1 = d1
        self.r2 = r2
        self.oci = oci
        self.current_path = self.publication_dir / "current.json"

    def _make_publication(
        self,
        *,
        report: ReconciliationReport,
        git_commit: GitCommit,
        r2_manifest_sha: str,
        floating_lines: tuple[FloatingLine, ...],
    ) -> dict[str, Any]:
        if not report.valid:
            raise PublicationError("RECONCILIATION_FAILED")
        if len(report.source_versions) < 2:
            raise PublicationError("SOURCE_VERSION_PAIR_MISSING")
        _require_lower_hex(git_commit.commit_sha, 40, "GIT_COMMIT_INVALID")
        _require_lower_hex(r2_manifest_sha, 64, "R2_MANIFEST_INVALID")
        active_lines = [line.threshold_fen for line in floating_lines if line.active and line.threshold_fen is not None]
        risk, dynamic = effective_risk(report.total_ending_fen, active_lines)
        # A publication ID is immutable, so a retry must never reuse the same
        # ID while changing `created_at` or its threshold snapshot.  Include a
        # microsecond UTC creation value in the identity and use plain INSERT
        # in D1; a collision fails closed instead of overwriting history.
        created_at = datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
        identity = "|".join((report.business_date.isoformat(), created_at, git_commit.commit_sha, *report.source_versions, r2_manifest_sha))
        publication_id = sha256(identity.encode("utf-8")).hexdigest()
        return {
            "publication_id": publication_id,
            "business_date": report.business_date.isoformat(),
            "status": "VALID",
            "source_versions": [{"source_version": version} for version in report.source_versions],
            "reconciliation_difference_fen": report.difference_fen,
            "threshold_snapshot": {
                "currency": "CNY",
                "fixed": {"hard_fen": HARD_THRESHOLD_FEN, "soft_fen": SOFT_THRESHOLD_FEN},
                "floating": _jsonable_lines(floating_lines),
                "fixed_risk": risk if risk in {"正常", "关注", "高风险"} else "正常",
                "dynamic_flag": dynamic,
            },
            "created_at": created_at,
            "git_commit_sha": git_commit.commit_sha,
            "d1_projection_version": "kmfa.daily_funds.d1.v1",
            "r2_manifest_sha256": r2_manifest_sha,
            "oci_backup_state": "PENDING",
        }

    def publish(
        self,
        *,
        report: ReconciliationReport,
        git_commit: GitCommit,
        attachments: Iterable[DownloadedAttachment],
        daily_balances: Iterable[DailyBalance],
        transaction_rows: Iterable[Mapping[str, Any]],
        account_rows: Iterable[Mapping[str, Any]] = (),
        private_publication_sink: Callable[[Mapping[str, Any]], str] | None = None,
        git_bundle_sink: Callable[[], bytes] | None = None,
        advance_pointer: bool = True,
        extra_floating_lines: Iterable[FloatingLine] = (),
        pre_mirrored: tuple[str, bytes] | None = None,
    ) -> PublishedProjection:
        balances = tuple(daily_balances)
        transactions = tuple(transaction_rows)
        accounts = tuple(account_rows)
        attachments = tuple(attachments)
        if not report.valid:
            raise PublicationError("RECONCILIATION_FAILED")
        if private_publication_sink is None:
            raise PublicationError("GIT_PUBLICATION_SINK_REQUIRED")
        if git_bundle_sink is None:
            raise PublicationError("GIT_BUNDLE_SINK_REQUIRED")
        _require_lower_hex(git_commit.commit_sha, 40, "GIT_COMMIT_INVALID")
        attachment_hashes = tuple(attachment.sha256 for attachment in R2Mirror._attachment_hashes(attachments))
        # R2 must be complete before parsing/reconciliation can produce a user
        # visible pointer; a controlled OCI lag is the sole asynchronous stage.
        if pre_mirrored is None:
            try:
                r2_sha, r2_inventory = self.r2.mirror(attachments, git_commit_sha=git_commit.commit_sha)
            except PublicationError as exc:
                raise PublicationError("R2_FAILED") from exc
        else:
            if (
                not isinstance(pre_mirrored, tuple)
                or len(pre_mirrored) != 2
                or not isinstance(pre_mirrored[0], str)
                or not isinstance(pre_mirrored[1], bytes)
            ):
                raise PublicationError("R2_FAILED")
            r2_sha, r2_inventory = pre_mirrored
            try:
                verified_inventory = self.r2.verify_manifest(
                    r2_sha,
                    expected_git_commit_sha=git_commit.commit_sha,
                    expected_attachment_hashes=attachment_hashes,
                )
                R2Mirror.validate_manifest_payload(
                    r2_sha,
                    r2_inventory,
                    expected_git_commit_sha=git_commit.commit_sha,
                    expected_attachment_hashes=attachment_hashes,
                )
            except PublicationError as exc:
                raise PublicationError("R2_FAILED") from exc
            if verified_inventory != r2_inventory:
                raise PublicationError("R2_FAILED")
        as_of = report.business_date + timedelta(days=1)
        floating_lines = (*floating_month_lines(as_of, balances), *tuple(extra_floating_lines))
        publication = self._make_publication(
            report=report,
            git_commit=git_commit,
            r2_manifest_sha=r2_sha,
            floating_lines=floating_lines,
        )
        # Validate the exact canonical candidate before trusting a D1 adapter.
        # The production adapter repeats this check, but the coordinator is the
        # atomic-publication boundary and must fail closed even with a future
        # adapter, a test double, or a partially implemented recovery target.
        publication, balances, transactions, accounts = _validate_projection_inputs(
            publication,
            balances,
            transactions,
            accounts,
        )
        _validate_report_matches_projection(
            report,
            publication=publication,
            account_rows=accounts,
        )
        try:
            self.d1.project(publication, balances, transactions, accounts)
            self.d1.oracle(str(publication["publication_id"]))
        except PublicationError as exc:
            raise PublicationError("D1_FAILED") from exc
        try:
            private_commit_sha = private_publication_sink(publication)
        except Exception as exc:
            raise PublicationError("GIT_WRITE_FAILED") from exc
        _require_lower_hex(private_commit_sha, 40, "GIT_WRITE_FAILED")
        try:
            offsite_bundle = git_bundle_sink()
        except Exception as exc:
            raise PublicationError("GIT_WRITE_FAILED") from exc
        if not isinstance(offsite_bundle, bytes) or not offsite_bundle:
            raise PublicationError("GIT_BUNDLE_EMPTY")
        # A non-empty bundle is not proof of recoverability.  The private
        # Git authority and the OCI copy must both be bound to the exact
        # raw-source commit and canonical publication before the UI pointer
        # is allowed to advance.  OCI transport failures remain a controlled
        # post-publication lag; an invalid local bundle is a publication
        # failure and must retain the prior trusted pointer.
        try:
            RestoreOracle.verify_private_publication_bundle(
                offsite_bundle,
                expected_raw_commit_sha=git_commit.commit_sha,
                expected_publication_commit_sha=private_commit_sha,
                publication=publication,
            )
        except PublicationError as exc:
            raise PublicationError("GIT_BUNDLE_INVALID") from exc
        active_lines = [line.threshold_fen for line in floating_lines if line.active and line.threshold_fen is not None]
        risk, dynamic = effective_risk(report.total_ending_fen, active_lines)
        snapshot: dict[str, Any] = {
            "schema_version": "kmfa.daily_funds.current_projection.v1",
            "publication": publication,
            "summary": {
                "total_available_fen": report.total_ending_fen,
                "risk_label": risk,
                "dynamic_flag": dynamic,
                "by_company_ending_fen": report.by_company_ending_fen,
                "by_bank_ending_fen": report.by_bank_ending_fen,
                "account_ending_by_hash": {
                    row.account_key_hash: row.ending_fen for row in report.account_reports
                },
            },
            "daily_balances": [
                {
                    "business_date": item.business_day.isoformat(),
                    "ending_available_fen": item.ending_available_fen,
                    "direct_observation": item.direct_observation,
                    "coverage_gap": item.coverage_gap,
                    "carried_forward": item.carried_forward,
                }
                for item in balances
            ],
            "transactions": [dict(row) for row in transactions],
        }
        # This is the only pointer swap.  Historical backfill validates and
        # projects its own publication but is not allowed to replace a newer
        # live day in the UI.
        if advance_pointer:
            atomic_json_write(self.current_path, snapshot)
            self.status.write(
                "已更新",
                "VALID_PUBLISHED",
                effective_business_date=report.business_date.isoformat(),
                last_verified_at=publication["created_at"],
                publication_id=str(publication["publication_id"]),
                backup_state="PENDING",
            )
        oci_state = "OK"
        oci_restore_manifest_sha: str | None = None
        try:
            d1_export = self.d1.export(str(publication["publication_id"]))
            oci_restore_manifest_sha = self.oci.backup(
                publication_id=str(publication["publication_id"]),
                publication_sha256=sha256(_canonical_bytes(publication)).hexdigest(),
                publication_created_at=str(publication["created_at"]),
                git_publication_commit_sha=private_commit_sha,
                git_bundle=offsite_bundle,
                d1_export=d1_export,
                r2_inventory=r2_inventory,
            )
        except PublicationError:
            # F-011: OCI lag cannot destroy a valid live publication; it is
            # visible and retried by the independent cold-backup schedule.
            oci_state = "LAG"
        # ``publication`` is immutable and is written byte-identically to D1,
        # private Git and the pointer.  OCI state is operational status, not a
        # late mutation of the canonical publication record.
        snapshot["runtime"] = {
            "oci_backup_state": oci_state,
            **({"oci_restore_manifest_sha": oci_restore_manifest_sha} if oci_restore_manifest_sha else {}),
            "git_publication_commit_sha": private_commit_sha,
        }
        if advance_pointer:
            atomic_json_write(self.current_path, snapshot)
            self.status.write(
                "已更新",
                "VALID_PUBLISHED",
                effective_business_date=report.business_date.isoformat(),
                last_verified_at=publication["created_at"],
                publication_id=str(publication["publication_id"]),
                backup_state=oci_state,
            )
        return PublishedProjection(snapshot["publication"], snapshot, oci_state, oci_restore_manifest_sha)


class RestoreOracle:
    """Verify a rebuilt projection before a caller exposes it to KMFA."""

    @staticmethod
    def verify(*, restored_publication: Mapping[str, Any], expected_publication_sha: str, expected_difference_fen: int = 0) -> None:
        _require_lower_hex(expected_publication_sha, 64, "RESTORE_HASH_MISMATCH")
        _require_integer(expected_difference_fen, "RESTORE_RECONCILIATION_FAILED")
        try:
            publication = _validate_publication(restored_publication)
        except PublicationError as exc:
            raise PublicationError("RESTORE_PUBLICATION_INVALID") from exc
        actual_sha = sha256(_canonical_bytes(publication)).hexdigest()
        if actual_sha != expected_publication_sha:
            raise PublicationError("RESTORE_HASH_MISMATCH")
        if publication.get("reconciliation_difference_fen") != expected_difference_fen:
            raise PublicationError("RESTORE_RECONCILIATION_FAILED")

    @staticmethod
    def verify_git_bundle(bundle: bytes, *, expected_commit_sha: str) -> None:
        """Prove that the OCI Git artifact is a usable complete bundle.

        A hash only proves that the bytes OCI returned are the bytes it stored.
        Recovery also needs to know that Git can import those bytes and that the
        raw-source commit cited by the canonical publication is actually in the
        bundle.  Do this in a throw-away bare repository, so no local checkout
        or existing Git state can make a bad bundle appear valid.
        """

        if len(expected_commit_sha) != 40 or any(char not in "0123456789abcdef" for char in expected_commit_sha):
            raise PublicationError("RESTORE_GIT_BUNDLE_INVALID")
        if not bundle:
            raise PublicationError("RESTORE_GIT_BUNDLE_INVALID")
        try:
            with tempfile.TemporaryDirectory(prefix="daily-funds-restore-git-") as temp:
                root = Path(temp)
                bundle_path = root / "private-db.bundle"
                bare_repo = root / "verify.git"
                bundle_path.write_bytes(bundle)
                commands = (
                    (["git", "init", "--bare", "--quiet", str(bare_repo)], None),
                    (["git", "bundle", "verify", str(bundle_path)], bare_repo),
                    (["git", "bundle", "unbundle", str(bundle_path)], bare_repo),
                    (["git", "cat-file", "-e", f"{expected_commit_sha}^{{commit}}"], bare_repo),
                )
                for command, cwd in commands:
                    result = subprocess.run(
                        command,
                        cwd=str(cwd) if cwd is not None else None,
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=60,
                    )
                    if result.returncode != 0:
                        raise PublicationError("RESTORE_GIT_BUNDLE_INVALID")
        except (OSError, subprocess.TimeoutExpired):
            raise PublicationError("RESTORE_GIT_BUNDLE_INVALID") from None

    @staticmethod
    def verify_private_publication_bundle(
        bundle: bytes,
        *,
        expected_raw_commit_sha: str,
        expected_publication_commit_sha: str,
        publication: Mapping[str, Any],
    ) -> None:
        """Bind an OCI bundle to the exact private canonical publication.

        The raw-source commit proves input lineage, but it cannot by itself
        prove that the formal publication which D1 is rebuilding was committed
        to the private authority.  Restore therefore verifies the raw commit,
        the later publication commit, their ancestry, and the canonical file
        bytes in a disposable bare repository before D1 can be mutated.
        """

        try:
            normalized = _validate_publication(publication)
            raw_commit = _require_lower_hex(
                expected_raw_commit_sha,
                40,
                "RESTORE_PRIVATE_PUBLICATION_INVALID",
            )
            publication_commit = _require_lower_hex(
                expected_publication_commit_sha,
                40,
                "RESTORE_PRIVATE_PUBLICATION_INVALID",
            )
            publication_id = _require_lower_hex(
                normalized["publication_id"],
                64,
                "RESTORE_PRIVATE_PUBLICATION_INVALID",
            )
            business_date = _require_iso_day(
                normalized["business_date"],
                "RESTORE_PRIVATE_PUBLICATION_INVALID",
            ).isoformat()
            expected_payload = _canonical_bytes(normalized)
            if not isinstance(bundle, bytes) or not bundle:
                raise PublicationError("RESTORE_PRIVATE_PUBLICATION_INVALID")
            publication_path = (
                SPARSE_PATH / "publications" / business_date / f"{publication_id}.json"
            ).as_posix()
            with tempfile.TemporaryDirectory(prefix="daily-funds-restore-publication-") as temp:
                root = Path(temp)
                bundle_path = root / "private-db.bundle"
                bare_repo = root / "verify.git"
                bundle_path.write_bytes(bundle)
                commands = (
                    (["git", "init", "--bare", "--quiet", str(bare_repo)], None),
                    (["git", "bundle", "verify", str(bundle_path)], bare_repo),
                    (["git", "bundle", "unbundle", str(bundle_path)], bare_repo),
                    (["git", "cat-file", "-e", f"{raw_commit}^{{commit}}"], bare_repo),
                    (["git", "cat-file", "-e", f"{publication_commit}^{{commit}}"], bare_repo),
                    (["git", "merge-base", "--is-ancestor", raw_commit, publication_commit], bare_repo),
                )
                for command, cwd in commands:
                    result = subprocess.run(
                        command,
                        cwd=str(cwd) if cwd is not None else None,
                        capture_output=True,
                        check=False,
                        timeout=60,
                    )
                    if result.returncode != 0:
                        raise PublicationError("RESTORE_PRIVATE_PUBLICATION_INVALID")
                result = subprocess.run(
                    ["git", "show", f"{publication_commit}:{publication_path}"],
                    cwd=str(bare_repo),
                    capture_output=True,
                    check=False,
                    timeout=60,
                )
                if result.returncode != 0 or result.stdout != expected_payload:
                    raise PublicationError("RESTORE_PRIVATE_PUBLICATION_INVALID")
        except (OSError, subprocess.TimeoutExpired, PublicationError):
            raise PublicationError("RESTORE_PRIVATE_PUBLICATION_INVALID") from None

    @staticmethod
    def decode_d1_export(
        payload: bytes,
        *,
        publication_id: str,
        expected_publication_sha: str,
    ) -> tuple[Mapping[str, Any], tuple[DailyBalance, ...], tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
        """Validate the OCI D1 export and return only rebuild-safe records."""

        _require_lower_hex(publication_id, 64, "RESTORE_D1_EXPORT_INVALID")
        _require_lower_hex(expected_publication_sha, 64, "RESTORE_D1_EXPORT_INVALID")
        try:
            if not isinstance(payload, bytes):
                raise TypeError
            decoded = json.loads(payload.decode("utf-8"))
            if not isinstance(decoded, Mapping) or set(decoded) != {"publication", "daily_balances", "transactions", "account_snapshots"}:
                raise TypeError
            row = decoded["publication"]
            if not isinstance(row, Mapping) or set(row) != {
                "publication_id", "business_date", "status", "reconciliation_difference_fen",
                "git_commit_sha", "payload_json", "created_at",
            }:
                raise TypeError
            payload_json = _require_text(row["payload_json"], "RESTORE_D1_EXPORT_INVALID")
            publication = _validate_publication(json.loads(payload_json))
            raw_balances = decoded["daily_balances"]
            raw_transactions = decoded["transactions"]
            raw_accounts = decoded["account_snapshots"]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, PublicationError) as exc:
            raise PublicationError("RESTORE_D1_EXPORT_INVALID") from exc
        if (
            publication.get("publication_id") != publication_id
            or _canonical_bytes(publication).decode("utf-8") != payload_json
            or row.get("business_date") != publication.get("business_date")
            or row.get("status") != publication.get("status")
            or row.get("reconciliation_difference_fen") != publication.get("reconciliation_difference_fen")
            or row.get("git_commit_sha") != publication.get("git_commit_sha")
            or row.get("created_at") != publication.get("created_at")
        ):
            raise PublicationError("RESTORE_D1_EXPORT_INVALID")
        RestoreOracle.verify(restored_publication=publication, expected_publication_sha=expected_publication_sha)
        if not isinstance(raw_balances, list) or not isinstance(raw_transactions, list) or not isinstance(raw_accounts, list):
            raise PublicationError("RESTORE_D1_EXPORT_INVALID")
        balances: list[DailyBalance] = []
        try:
            for balance_row in raw_balances:
                if not isinstance(balance_row, Mapping) or set(balance_row) != {
                    "business_date", "scope", "ending_available_fen", "direct_observation", "coverage_gap", "carried_forward",
                } or balance_row["scope"] != "global":
                    raise TypeError
                balances.append(DailyBalance(
                    _require_iso_day(balance_row["business_date"], "RESTORE_D1_EXPORT_INVALID"),
                    _require_integer(balance_row["ending_available_fen"], "RESTORE_D1_EXPORT_INVALID"),
                    _require_boolean(balance_row["direct_observation"], "RESTORE_D1_EXPORT_INVALID"),
                    _require_boolean(balance_row["coverage_gap"], "RESTORE_D1_EXPORT_INVALID"),
                    _require_boolean(balance_row["carried_forward"], "RESTORE_D1_EXPORT_INVALID"),
                ))
            _, normalized_balances, transactions, accounts = _validate_projection_inputs(
                publication,
                balances,
                raw_transactions,
                raw_accounts,
            )
        except (KeyError, TypeError, ValueError, PublicationError) as exc:
            raise PublicationError("RESTORE_D1_EXPORT_INVALID") from exc
        return publication, normalized_balances, transactions, accounts


@dataclass(frozen=True)
class RestoredProjection:
    publication: Mapping[str, Any]
    daily_balances: tuple[DailyBalance, ...]
    transaction_rows: tuple[dict[str, Any], ...]
    account_rows: tuple[dict[str, Any], ...]


class RestoreCoordinator:
    """Rebuild D1 from OCI's verified copy without trusting local runtime state."""

    def __init__(self, *, d1: D1Projection, oci: OciColdBackup):
        self.d1 = d1
        self.oci = oci

    def restore(self, publication_id: str) -> RestoredProjection:
        manifest, artifacts = self.oci.restore_artifacts(publication_id)
        publication, balances, transactions, accounts = RestoreOracle.decode_d1_export(
            artifacts["d1_export"],
            publication_id=publication_id,
            expected_publication_sha=str(manifest["publication_sha256"]),
        )
        expected_r2 = str(publication.get("r2_manifest_sha256") or "")
        try:
            R2Mirror.validate_manifest_payload(
                expected_r2,
                artifacts["r2_inventory"],
                expected_git_commit_sha=str(publication.get("git_commit_sha") or ""),
            )
        except PublicationError as exc:
            raise PublicationError("RESTORE_R2_INVENTORY_MISMATCH") from exc
        RestoreOracle.verify_git_bundle(
            artifacts["git_bundle"],
            expected_commit_sha=str(publication.get("git_commit_sha") or ""),
        )
        RestoreOracle.verify_private_publication_bundle(
            artifacts["git_bundle"],
            expected_raw_commit_sha=str(publication.get("git_commit_sha") or ""),
            expected_publication_commit_sha=str(manifest.get("git_publication_commit_sha") or ""),
            publication=publication,
        )
        self.d1.project(publication, balances, transactions, accounts)
        self.d1.oracle(publication_id)
        return RestoredProjection(publication, balances, transactions, accounts)
