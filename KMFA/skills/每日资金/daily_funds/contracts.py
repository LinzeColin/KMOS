"""Frozen business contracts for the daily-funds slice.

Amounts are always integer fen.  This module has no I/O so the business rules
can be exercised with a deterministic fake clock before any cloud credential
is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Iterable, Mapping

HARD_THRESHOLD_FEN = 60_000_000
SOFT_THRESHOLD_FEN = 120_000_000
HUMAN_STATUSES = frozenset({"已更新", "处理中", "需处理"})
RISK_LABELS = frozenset({"正常", "关注", "高风险", "动态偏低", "数据不足"})
RANGE_DAYS: Mapping[str, int] = {
    "1d": 1,
    "7d": 7,
    "30d": 30,
    "90d": 90,
    "180d": 180,
    "360d": 360,
}


class ContractError(ValueError):
    """A deterministic contract failure, safe to surface as a machine code."""


def parse_amount_to_fen(value: object) -> int:
    """Convert an explicit yuan value to exact integer fen.

    Floats are deliberately refused: accepting binary floating point would make
    one-fen reconciliation and threshold boundaries non-deterministic.
    """

    if isinstance(value, bool) or isinstance(value, float):
        raise ContractError("AMOUNT_FLOAT_OR_BOOLEAN_NOT_ALLOWED")
    if isinstance(value, Decimal):
        decimal_value = value
    elif isinstance(value, int):
        decimal_value = Decimal(value)
    elif isinstance(value, str):
        text = value.strip().replace(",", "").replace("￥", "").replace("¥", "")
        if not text:
            raise ContractError("AMOUNT_EMPTY")
        try:
            decimal_value = Decimal(text)
        except InvalidOperation as exc:
            raise ContractError("AMOUNT_INVALID") from exc
    else:
        raise ContractError("AMOUNT_TYPE_INVALID")
    if not decimal_value.is_finite():
        raise ContractError("AMOUNT_NON_FINITE")
    fen = decimal_value * Decimal("100")
    if fen != fen.to_integral_value():
        raise ContractError("AMOUNT_SUB_FEN_PRECISION")
    return int(fen)


def fen_average(values: Iterable[int]) -> int:
    """Return an exact half-up integer-fen average."""

    materialized = list(values)
    if not materialized:
        raise ContractError("EMPTY_BALANCE_WINDOW")
    if any(isinstance(v, bool) or not isinstance(v, int) for v in materialized):
        raise ContractError("BALANCE_NOT_INTEGER_FEN")
    return int((Decimal(sum(materialized)) / Decimal(len(materialized))).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    ))


def fixed_risk(amount_fen: int) -> str:
    if isinstance(amount_fen, bool) or not isinstance(amount_fen, int):
        raise ContractError("THRESHOLD_AMOUNT_NOT_INTEGER_FEN")
    if amount_fen <= HARD_THRESHOLD_FEN:
        return "高风险"
    if amount_fen <= SOFT_THRESHOLD_FEN:
        return "关注"
    return "正常"


def dynamic_flag(current_fen: int, active_lines: Iterable[int]) -> str | None:
    lines = list(active_lines)
    if not lines:
        return None
    if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in lines):
        raise ContractError("DYNAMIC_THRESHOLD_INVALID")
    below = sum(current_fen <= value for value in lines)
    if below == len(lines):
        return "动态明显偏低"
    if below:
        return "动态偏低"
    return None


def effective_risk(current_fen: int, active_lines: Iterable[int]) -> tuple[str, str | None]:
    """Apply the no-downgrade precedence contract.

    Fixed hard/soft classifications stay authoritative.  Dynamic evidence can
    only raise a normal fixed result to a dynamic attention signal.
    """

    fixed = fixed_risk(current_fen)
    dynamic = dynamic_flag(current_fen, active_lines)
    if fixed in {"高风险", "关注"}:
        return fixed, dynamic
    return (dynamic or fixed), dynamic


def _month_start(day: date) -> date:
    return day.replace(day=1)


def complete_calendar_month_window(as_of: date, months: int) -> tuple[date, date]:
    """Return the last ``months`` completed calendar months before ``as_of``."""

    if months <= 0:
        raise ContractError("MONTH_WINDOW_INVALID")
    end = _month_start(as_of) - timedelta(days=1)
    start_month = end.replace(day=1)
    for _ in range(months - 1):
        start_month = (start_month - timedelta(days=1)).replace(day=1)
    return start_month, end


@dataclass(frozen=True)
class DailyBalance:
    business_day: date
    ending_available_fen: int
    direct_observation: bool
    coverage_gap: bool = False
    # A carried-forward value is permitted only for an explicitly classified
    # non-reporting day.  It participates in coverage, but never inflates the
    # direct-observation count used by the 3/6 month gates.
    carried_forward: bool = False


@dataclass(frozen=True)
class FloatingLine:
    name: str
    threshold_fen: int | None
    start: date
    end: date
    days: int
    direct_observations: int
    coverage: Decimal
    active: bool
    reason: str | None
    # Coverage must be explainable in the owner UI: direct evidence and
    # explicitly classified non-reporting carries are materially different.
    covered_days: int = 0
    carried_forward_days: int = 0


def _calendar_days(start: date, end: date) -> list[date]:
    if end < start:
        raise ContractError("DATE_RANGE_INVALID")
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def _window_line(
    name: str,
    balances: Iterable[DailyBalance],
    start: date,
    end: date,
    *,
    minimum_direct_observations: int,
    minimum_coverage: Decimal,
) -> FloatingLine:
    indexed = {row.business_day: row for row in balances}
    rows = [indexed.get(day) for day in _calendar_days(start, end)]
    present = [row for row in rows if row is not None]
    covered = [row for row in present if not row.coverage_gap]
    days = len(rows)
    coverage = Decimal(len(covered)) / Decimal(days)
    direct = sum(row.direct_observation for row in covered)
    carried = sum(row.carried_forward for row in covered)
    if coverage < minimum_coverage:
        return FloatingLine(name, None, start, end, days, direct, coverage, False, "COVERAGE_INSUFFICIENT", len(covered), carried)
    if direct < minimum_direct_observations:
        return FloatingLine(name, None, start, end, days, direct, coverage, False, "DIRECT_OBSERVATIONS_INSUFFICIENT", len(covered), carried)
    # `covered` intentionally includes non-reporting carry-forward balances;
    # expected-reporting gaps cannot enter an active line.
    return FloatingLine(
        name,
        fen_average(row.ending_available_fen for row in covered),
        start,
        end,
        days,
        direct,
        coverage,
        True,
        None,
        len(covered),
        carried,
    )


def floating_month_lines(as_of: date, balances: Iterable[DailyBalance]) -> tuple[FloatingLine, FloatingLine]:
    frozen = tuple(balances)
    three_start, three_end = complete_calendar_month_window(as_of, 3)
    six_start, six_end = complete_calendar_month_window(as_of, 6)
    return (
        _window_line(
            "three_month",
            frozen,
            three_start,
            three_end,
            minimum_direct_observations=45,
            minimum_coverage=Decimal("0.95"),
        ),
        _window_line(
            "six_month",
            frozen,
            six_start,
            six_end,
            minimum_direct_observations=90,
            minimum_coverage=Decimal("0.95"),
        ),
    )


def custom_date_line(start: date, end: date, balances: Iterable[DailyBalance]) -> FloatingLine:
    if (end - start).days + 1 < 7:
        raise ContractError("CUSTOM_RANGE_MINIMUM_SEVEN_DAYS")
    return _window_line(
        "custom_date_range",
        tuple(balances),
        start,
        end,
        # The frozen contract gives custom ranges an 80% coverage gate but no
        # extra direct-observation minimum.  Requiring one here would silently
        # change a valid, explicitly configured non-reporting-only window.
        minimum_direct_observations=0,
        minimum_coverage=Decimal("0.80"),
    )


def validate_custom_numeric(amount_fen: int) -> int:
    if isinstance(amount_fen, bool) or not isinstance(amount_fen, int):
        raise ContractError("CUSTOM_NUMERIC_NOT_INTEGER_FEN")
    if not 0 <= amount_fen <= 999_999_999_999_999:
        raise ContractError("CUSTOM_NUMERIC_OUT_OF_RANGE")
    return amount_fen
