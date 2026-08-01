"""Zero-fen reconciliation and lineage-preserving aggregation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from hashlib import sha256
from typing import Iterable, Mapping

from .contracts import ContractError
from .models import AccountSnapshot, ParsedFacts, Transaction


class ReconciliationError(ContractError):
    pass


def account_key(company: str, bank: str, account: str) -> tuple[str, str, str]:
    return company.strip(), bank.strip(), account.strip()


def account_key_hash(key: tuple[str, str, str]) -> str:
    return sha256("\x1f".join(key).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AccountReconciliation:
    account_key_hash: str
    opening_fen: int
    external_inflow_fen: int
    external_outflow_fen: int
    internal_inflow_fen: int
    internal_outflow_fen: int
    adjustment_fen: int
    ending_fen: int
    difference_fen: int
    source_versions: tuple[str, ...]


@dataclass(frozen=True)
class ReconciliationReport:
    business_date: date
    account_reports: tuple[AccountReconciliation, ...]
    total_opening_fen: int
    total_external_inflow_fen: int
    total_external_outflow_fen: int
    total_adjustment_fen: int
    total_ending_fen: int
    difference_fen: int
    by_company_ending_fen: Mapping[str, int]
    by_bank_ending_fen: Mapping[str, int]
    source_versions: tuple[str, ...]
    by_company_difference_fen: Mapping[str, int] = field(default_factory=dict)
    by_bank_difference_fen: Mapping[str, int] = field(default_factory=dict)

    @property
    def valid(self) -> bool:
        return (
            self.difference_fen == 0
            and all(row.difference_fen == 0 for row in self.account_reports)
            and all(value == 0 for value in self.by_company_difference_fen.values())
            and all(value == 0 for value in self.by_bank_difference_fen.values())
        )


def _collect_facts(facts: Iterable[ParsedFacts]) -> tuple[date, list[AccountSnapshot], list[Transaction], set[str]]:
    frozen = list(facts)
    account_facts = [fact for fact in frozen if fact.accounts]
    transaction_facts = [fact for fact in frozen if fact.transactions]
    if not account_facts:
        raise ReconciliationError("ACCOUNT_FACT_MISSING")
    if not transaction_facts:
        raise ReconciliationError("TRANSACTION_FACT_MISSING")
    dates = {fact.business_date for fact in frozen if fact.accounts or fact.transactions}
    if len(dates) != 1:
        raise ReconciliationError("BUSINESS_DATE_MISMATCH")
    accounts = [row for fact in account_facts for row in fact.accounts]
    transactions = [row for fact in transaction_facts for row in fact.transactions]
    versions = {fact.source_version for fact in frozen if fact.accounts or fact.transactions}
    if len(versions) < 2:
        raise ReconciliationError("SOURCE_VERSION_PAIR_MISSING")
    return next(iter(dates)), accounts, transactions, versions


def _unique_accounts(accounts: Iterable[AccountSnapshot]) -> dict[tuple[str, str, str], AccountSnapshot]:
    indexed: dict[tuple[str, str, str], AccountSnapshot] = {}
    for account in accounts:
        key = account_key(account.company, account.bank, account.account)
        if key in indexed:
            raise ReconciliationError("DUPLICATE_ACCOUNT_SNAPSHOT")
        indexed[key] = account
    return indexed


def _dedupe_transactions(transactions: Iterable[Transaction]) -> list[Transaction]:
    seen: set[tuple[str, str, str, str]] = set()
    unique: list[Transaction] = []
    for transaction in transactions:
        key = (*account_key(transaction.company, transaction.bank, transaction.account), transaction.transaction_id)
        if key not in seen:
            unique.append(transaction)
            seen.add(key)
    return unique


def _validate_internal_transfer_pairs(transactions: Iterable[Transaction]) -> None:
    groups: dict[str, list[Transaction]] = {}
    for transaction in transactions:
        if transaction.is_internal_transfer:
            if not transaction.transfer_id:
                raise ReconciliationError("INTERNAL_TRANSFER_ID_MISSING")
            groups.setdefault(transaction.transfer_id, []).append(transaction)
    for transfer_id, rows in groups.items():
        inbound = sum(row.inflow_fen for row in rows)
        outbound = sum(row.outflow_fen for row in rows)
        if not inbound or not outbound or inbound != outbound:
            raise ReconciliationError(f"INTERNAL_TRANSFER_UNPAIRED:{sha256(transfer_id.encode()).hexdigest()[:12]}")


def reconcile(
    facts: Iterable[ParsedFacts],
    *,
    previous_ending_by_account: Mapping[tuple[str, str, str] | str, int] | None = None,
) -> ReconciliationReport:
    """Reconcile one business date without mixing incompatible versions.

    ``previous_ending_by_account`` comes only from a previous VALID publication.
    A first publication must carry an explicit opening balance in its account
    source rather than guessing it from transactions.
    """

    business_date, accounts, transactions, source_versions = _collect_facts(facts)
    indexed_accounts = _unique_accounts(accounts)
    unique_transactions = _dedupe_transactions(transactions)
    _validate_internal_transfer_pairs(unique_transactions)
    previous = dict(previous_ending_by_account or {})
    by_account: dict[tuple[str, str, str], list[Transaction]] = {key: [] for key in indexed_accounts}
    for transaction in unique_transactions:
        key = account_key(transaction.company, transaction.bank, transaction.account)
        if key not in by_account:
            raise ReconciliationError("TRANSACTION_ACCOUNT_NOT_IN_SNAPSHOT")
        by_account[key].append(transaction)

    reports: list[AccountReconciliation] = []
    company_total: dict[str, int] = {}
    bank_total: dict[str, int] = {}
    company_difference: dict[str, int] = {}
    bank_difference: dict[str, int] = {}
    for key, snapshot in sorted(indexed_accounts.items()):
        opening = snapshot.opening_available_fen
        if opening is None:
            opening = previous.get(key)
            if opening is None:
                opening = previous.get(account_key_hash(key))
        if opening is None:
            raise ReconciliationError("OPENING_BALANCE_MISSING")
        external = [row for row in by_account[key] if not row.is_internal_transfer]
        internal = [row for row in by_account[key] if row.is_internal_transfer]
        inflow = sum(row.inflow_fen for row in external)
        outflow = sum(row.outflow_fen for row in external)
        internal_inflow = sum(row.inflow_fen for row in internal)
        internal_outflow = sum(row.outflow_fen for row in internal)
        adjustment = sum(row.adjustment_fen for row in external)
        difference = (
            opening + inflow + internal_inflow - outflow - internal_outflow
            + adjustment - snapshot.ending_available_fen
        )
        versions = tuple(sorted({snapshot.source.source_version, *(row.source.source_version for row in by_account[key])}))
        reports.append(AccountReconciliation(
            account_key_hash(key),
            opening,
            inflow,
            outflow,
            internal_inflow,
            internal_outflow,
            adjustment,
            snapshot.ending_available_fen,
            difference,
            versions,
        ))
        company_total[snapshot.company] = company_total.get(snapshot.company, 0) + snapshot.ending_available_fen
        bank_total[snapshot.bank] = bank_total.get(snapshot.bank, 0) + snapshot.ending_available_fen
        company_difference[snapshot.company] = company_difference.get(snapshot.company, 0) + difference
        bank_difference[snapshot.bank] = bank_difference.get(snapshot.bank, 0) + difference

    total_opening = sum(row.opening_fen for row in reports)
    total_inflow = sum(row.external_inflow_fen for row in reports)
    total_outflow = sum(row.external_outflow_fen for row in reports)
    total_adjustment = sum(row.adjustment_fen for row in reports)
    total_ending = sum(row.ending_fen for row in reports)
    return ReconciliationReport(
        business_date,
        tuple(reports),
        total_opening,
        total_inflow,
        total_outflow,
        total_adjustment,
        total_ending,
        sum(row.difference_fen for row in reports),
        dict(sorted(company_total.items())),
        dict(sorted(bank_total.items())),
        tuple(sorted(source_versions)),
        dict(sorted(company_difference.items())),
        dict(sorted(bank_difference.items())),
    )
