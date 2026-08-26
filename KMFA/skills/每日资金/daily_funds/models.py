"""Strict in-memory records.  Raw source remains outside these projections."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class SourceRef:
    attachment_sha256: str
    message_id_hash: str
    occurrence_path: str
    source_version: str


@dataclass(frozen=True)
class ParserEvidence:
    """Values-free parser-open evidence for one raw attachment.

    The source SHA remains in ``SourceRef`` / the private runtime journal.  A
    fact never gains this evidence until the declared type, byte magic and
    parser-open gate have all succeeded.
    """

    format: str
    suffix: str
    declared_mime: str | None
    magic: str
    parser_version: str


@dataclass(frozen=True)
class AccountSnapshot:
    business_date: date
    company: str
    bank: str
    account: str
    ending_available_fen: int
    opening_available_fen: int | None
    currency: str
    source: SourceRef


@dataclass(frozen=True)
class Transaction:
    business_date: date
    company: str
    # The frozen transaction schema makes bank_id optional.  A transaction
    # without it may still be joined only when its company/account alias maps
    # to exactly one account snapshot; reconciliation owns that check.
    bank: str | None
    account: str
    transaction_id: str
    occurred_at: datetime | None
    inflow_fen: int
    outflow_fen: int
    adjustment_fen: int
    is_internal_transfer: bool
    transfer_id: str | None
    source: SourceRef


@dataclass(frozen=True)
class ParsedFacts:
    business_date: date
    family: str
    accounts: tuple[AccountSnapshot, ...]
    transactions: tuple[Transaction, ...]
    source_version: str
    parser_evidence: ParserEvidence

    def public_shape(self) -> dict[str, Any]:
        """A values-free shape used only in status diagnostics."""

        return {
            "business_date": self.business_date.isoformat(),
            "family": self.family,
            "account_rows": len(self.accounts),
            "transaction_rows": len(self.transactions),
            "source_version": self.source_version,
        }


@dataclass(frozen=True)
class CashflowObservation:
    """A bounded daily inflow/outflow observation from one source document.

    This is intentionally *not* a ``Transaction`` and cannot enter the
    account-balance reconciliation or the formal publication pointer.  The
    source screenshot format carries daily receipt/payment totals but no
    account identity or ending available balance.  Keeping this type separate
    prevents a useful operational chart from being misrepresented as a cash
    balance fact.
    """

    business_date: date
    inflow_fen: int
    outflow_fen: int
    source: SourceRef
    parser_evidence: ParserEvidence
    layout_fingerprint: str


@dataclass(frozen=True)
class PaymentRequestObservation:
    """A daily payment-request total, separate from cash and bank balances.

    This evidence reports the verified total on a payment-request sheet.  It
    is neither a completed payment nor an available-balance fact, so it never
    enters the account/transaction reconciliation or publication pointer.
    """

    business_date: date
    # ``DOCUMENT_DAY`` comes from a visible document date. ``MESSAGE_DAY``
    # comes from the exact DWS message day when the approved horizontal
    # summary profile has no visible date cell.
    date_basis: str
    request_total_fen: int
    source: SourceRef
    parser_evidence: ParserEvidence
    layout_fingerprint: str


def jsonable(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "__dataclass_fields__"):
        return {key: jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonable(item) for item in value]
    return value
