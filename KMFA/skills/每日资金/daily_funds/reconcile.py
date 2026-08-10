"""Zero-fen reconciliation and lineage-preserving aggregation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
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


def _require_calendar_day(value: object, code: str) -> date:
    if isinstance(value, datetime) or not isinstance(value, date):
        raise ReconciliationError(code)
    return value


def _require_text(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReconciliationError(code)
    return value.strip()


def _require_fen(value: object, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ReconciliationError(code)
    return value


def _require_source_version(value: object) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ReconciliationError("SOURCE_VERSION_INVALID")
    return value


def _validate_facts(facts: Iterable[ParsedFacts]) -> list[ParsedFacts]:
    """Refuse malformed direct callers before they can make a false zero."""

    frozen = list(facts)
    for fact in frozen:
        business_date = _require_calendar_day(fact.business_date, "FACT_BUSINESS_DATE_INVALID")
        fact_source_version = _require_source_version(fact.source_version)
        if fact.accounts and fact.transactions:
            raise ReconciliationError("FACT_FAMILIES_MIXED")
        for account in fact.accounts:
            if account.business_date != business_date:
                raise ReconciliationError("FACT_BUSINESS_DATE_MISMATCH")
            _require_text(account.company, "ACCOUNT_COMPANY_INVALID")
            _require_text(account.bank, "ACCOUNT_BANK_INVALID")
            _require_text(account.account, "ACCOUNT_NUMBER_INVALID")
            _require_fen(account.ending_available_fen, "ACCOUNT_ENDING_NOT_INTEGER_FEN")
            if account.opening_available_fen is not None:
                _require_fen(account.opening_available_fen, "ACCOUNT_OPENING_NOT_INTEGER_FEN")
            if account.currency != "CNY":
                raise ReconciliationError("CURRENCY_UNSUPPORTED")
            if _require_source_version(account.source.source_version) != fact_source_version:
                raise ReconciliationError("SOURCE_VERSION_MISMATCH")
        for transaction in fact.transactions:
            if transaction.business_date != business_date:
                raise ReconciliationError("FACT_BUSINESS_DATE_MISMATCH")
            _require_text(transaction.company, "TRANSACTION_COMPANY_INVALID")
            if transaction.bank is not None:
                _require_text(transaction.bank, "TRANSACTION_BANK_INVALID")
            _require_text(transaction.account, "TRANSACTION_ACCOUNT_INVALID")
            _require_text(transaction.transaction_id, "TRANSACTION_ID_INVALID")
            inflow = _require_fen(transaction.inflow_fen, "TRANSACTION_INFLOW_NOT_INTEGER_FEN")
            outflow = _require_fen(transaction.outflow_fen, "TRANSACTION_OUTFLOW_NOT_INTEGER_FEN")
            _require_fen(transaction.adjustment_fen, "TRANSACTION_ADJUSTMENT_NOT_INTEGER_FEN")
            if inflow < 0 or outflow < 0 or (inflow and outflow):
                raise ReconciliationError("TRANSACTION_FLOW_INVALID")
            if not isinstance(transaction.is_internal_transfer, bool):
                raise ReconciliationError("INTERNAL_TRANSFER_FLAG_INVALID")
            if transaction.is_internal_transfer:
                _require_text(transaction.transfer_id, "INTERNAL_TRANSFER_ID_MISSING")
            elif transaction.transfer_id is not None:
                _require_text(transaction.transfer_id, "TRANSFER_ID_INVALID")
            if _require_source_version(transaction.source.source_version) != fact_source_version:
                raise ReconciliationError("SOURCE_VERSION_MISMATCH")
    return frozen


def _validated_prior_balances(
    values: Mapping[tuple[str, str, str] | str, int] | None,
) -> dict[tuple[str, str, str] | str, int]:
    if values is None:
        return {}
    if not isinstance(values, Mapping):
        raise ReconciliationError("PRIOR_BALANCE_MAPPING_INVALID")
    normalized: dict[tuple[str, str, str] | str, int] = {}
    for key, value in values.items():
        amount = _require_fen(value, "PRIOR_BALANCE_NOT_INTEGER_FEN")
        if isinstance(key, tuple):
            if len(key) != 3:
                raise ReconciliationError("PRIOR_BALANCE_KEY_INVALID")
            normalized_key = tuple(_require_text(part, "PRIOR_BALANCE_KEY_INVALID") for part in key)
            normalized[normalized_key] = amount
        elif isinstance(key, str):
            normalized[_require_source_version(key)] = amount
        else:
            raise ReconciliationError("PRIOR_BALANCE_KEY_INVALID")
    return normalized


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


def _collect_facts(
    facts: Iterable[ParsedFacts],
) -> tuple[date, list[AccountSnapshot], list[Transaction], set[str], tuple[int, int]]:
    frozen = _validate_facts(facts)
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
    return next(iter(dates)), accounts, transactions, versions, (len(account_facts), len(transaction_facts))


def _unique_accounts(accounts: Iterable[AccountSnapshot]) -> dict[tuple[str, str, str], AccountSnapshot]:
    indexed: dict[tuple[str, str, str], AccountSnapshot] = {}
    for account in accounts:
        key = account_key(account.company, account.bank, account.account)
        if key in indexed:
            raise ReconciliationError("DUPLICATE_ACCOUNT_SNAPSHOT")
        indexed[key] = account
    return indexed


def _transaction_account_key(
    transaction: Transaction,
    indexed_accounts: Mapping[tuple[str, str, str], AccountSnapshot],
) -> tuple[str, str, str]:
    """Resolve an optional transaction bank without guessing an account.

    The task-pack permits a transaction without ``bank_id``.  It is safe to
    join that record only when ``company + account`` selects exactly one
    account snapshot for the same business date.  Missing and ambiguous joins
    remain hard reconciliation failures rather than silently selecting a bank.
    """

    company = _require_text(transaction.company, "TRANSACTION_COMPANY_INVALID")
    account = _require_text(transaction.account, "TRANSACTION_ACCOUNT_INVALID")
    if transaction.bank is not None:
        key = account_key(company, _require_text(transaction.bank, "TRANSACTION_BANK_INVALID"), account)
        if key not in indexed_accounts:
            raise ReconciliationError("TRANSACTION_ACCOUNT_NOT_IN_SNAPSHOT")
        return key
    matches = [key for key in indexed_accounts if key[0] == company and key[2] == account]
    if not matches:
        raise ReconciliationError("TRANSACTION_ACCOUNT_NOT_IN_SNAPSHOT")
    if len(matches) != 1:
        raise ReconciliationError("TRANSACTION_ACCOUNT_AMBIGUOUS")
    return matches[0]


def _unique_transactions(
    transactions: Iterable[Transaction],
    indexed_accounts: Mapping[tuple[str, str, str], AccountSnapshot],
) -> list[Transaction]:
    seen: set[tuple[str, str, str, str]] = set()
    unique: list[Transaction] = []
    for transaction in transactions:
        key = (*_transaction_account_key(transaction, indexed_accounts), transaction.transaction_id)
        if key in seen:
            raise ReconciliationError("DUPLICATE_TRANSACTION")
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

    business_date, accounts, transactions, source_versions, fact_counts = _collect_facts(facts)
    indexed_accounts = _unique_accounts(accounts)
    unique_transactions = _unique_transactions(transactions, indexed_accounts)
    # The runtime chooses exactly one attachment per fact family before
    # reaching this function.  Preserve that invariant for direct callers as
    # well: accepting a second non-duplicate source would silently blend two
    # independently authoritative snapshots or ledgers into a fabricated
    # result.  Structural duplicate checks intentionally run first so their
    # more precise diagnostics remain available.
    if fact_counts != (1, 1):
        raise ReconciliationError("SOURCE_FACT_PAIR_AMBIGUOUS")
    _validate_internal_transfer_pairs(unique_transactions)
    previous = _validated_prior_balances(previous_ending_by_account)
    # A prior VALID publication is a complete account close, not an optional
    # hint.  If it contains an account absent from the new snapshot, silently
    # ignoring that balance could turn an omitted account into a false
    # zero-fen reconciliation.  New accounts remain valid when their source
    # supplies an explicit opening balance; only prior-only accounts block.
    snapshot_hashes = {account_key_hash(key) for key in indexed_accounts}
    prior_hashes = {
        account_key_hash(key) if isinstance(key, tuple) else key
        for key in previous
    }
    if not prior_hashes <= snapshot_hashes:
        raise ReconciliationError("PRIOR_ACCOUNT_MISSING_FROM_SNAPSHOT")
    by_account: dict[tuple[str, str, str], list[Transaction]] = {key: [] for key in indexed_accounts}
    for transaction in unique_transactions:
        key = _transaction_account_key(transaction, indexed_accounts)
        by_account[key].append(transaction)

    reports: list[AccountReconciliation] = []
    company_total: dict[str, int] = {}
    bank_total: dict[str, int] = {}
    company_difference: dict[str, int] = {}
    bank_difference: dict[str, int] = {}
    for key, snapshot in sorted(indexed_accounts.items()):
        opening = snapshot.opening_available_fen
        tuple_opening = previous.get(key)
        hashed_opening = previous.get(account_key_hash(key))
        # Check the dual key representations even if the source itself has
        # an opening balance.  Otherwise a corrupted prior journal can hide
        # behind that source value and reappear on the next date.
        if tuple_opening is not None and hashed_opening is not None and tuple_opening != hashed_opening:
            raise ReconciliationError("PRIOR_BALANCE_CONFLICT")
        if opening is None:
            opening = tuple_opening if tuple_opening is not None else hashed_opening
        if opening is None:
            raise ReconciliationError("OPENING_BALANCE_MISSING")
        external = [row for row in by_account[key] if not row.is_internal_transfer]
        internal = [row for row in by_account[key] if row.is_internal_transfer]
        inflow = sum(row.inflow_fen for row in external)
        outflow = sum(row.outflow_fen for row in external)
        internal_inflow = sum(row.inflow_fen for row in internal)
        internal_outflow = sum(row.outflow_fen for row in internal)
        # The frozen arithmetic contract applies adjustments to every ledger
        # row.  Dropping one merely because its transfer flag is internal can
        # fabricate a zero or hide a real one-fen discrepancy.
        adjustment = sum(row.adjustment_fen for row in by_account[key])
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
