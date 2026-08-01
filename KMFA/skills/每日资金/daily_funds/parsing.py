"""Deterministic parsers for the two required daily-funds fact families.

There is deliberately no heuristic OCR in this module.  PDFs/images and an
unknown column shape are rejected with a machine code; a later approved parser
can be added with its own test corpus rather than silently inventing amounts.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Mapping

from .contracts import ContractError, parse_amount_to_fen
from .models import AccountSnapshot, ParsedFacts, SourceRef, Transaction

ACCOUNT_FAMILY = "资金账户明细表"
TRANSACTION_FAMILIES = frozenset({"资金流水明细", "资金明细"})


class ParseError(ContractError):
    pass


def normalize_header(value: object) -> str:
    return re.sub(r"[\s_\-（）()【】\[\]：:]+", "", str(value or "").strip()).lower()


ALIASES: Mapping[str, tuple[str, ...]] = {
    "business_date": ("业务日期", "数据日期", "截止日期", "日期", "统计日期"),
    "company": ("公司", "公司名称", "主体", "账户主体", "所属公司"),
    "bank": ("开户行", "银行", "银行名称", "银行机构"),
    "account": ("账号", "账户", "银行账号", "账户号"),
    "ending": ("期末可用余额", "可用余额", "账户余额", "余额", "期末余额"),
    "opening": ("期初可用余额", "期初余额", "上日余额", "前日余额"),
    "currency": ("币种", "货币", "currency"),
    "transaction_id": ("流水号", "交易流水号", "交易编号", "凭证号", "业务编号"),
    "occurred_at": ("发生时间", "交易时间", "记账时间", "时间"),
    "inflow": ("流入", "收入", "贷方发生额", "入账金额"),
    "outflow": ("流出", "支出", "借方发生额", "出账金额"),
    "amount": ("金额", "发生额", "交易金额"),
    "direction": ("收支方向", "方向", "借贷方向", "交易方向"),
    "adjustment": ("调整", "调整金额", "其他调整"),
    "internal": ("内部调拨", "是否内部调拨", "调拨标记"),
    "transfer_id": ("调拨编号", "内部调拨编号", "关联流水号", "关联交易号"),
}


def _column_map(headers: Iterable[object]) -> dict[str, str]:
    normalized = {normalize_header(header): str(header) for header in headers if str(header).strip()}
    mapped: dict[str, str] = {}
    for field, aliases in ALIASES.items():
        for alias in aliases:
            match = normalized.get(normalize_header(alias))
            if match is not None:
                mapped[field] = match
                break
    return mapped


def _required(mapped: Mapping[str, str], fields: Iterable[str]) -> None:
    missing = [field for field in fields if field not in mapped]
    if missing:
        raise ParseError("COLUMN_MAPPING_MISSING_" + "_".join(sorted(missing)).upper())


def _parse_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y年%m月%d日", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ParseError("BUSINESS_DATE_INVALID")


def _parse_datetime(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ParseError("TRANSACTION_TIME_INVALID")


def _required_text(row: Mapping[str, object], column: str, code: str) -> str:
    value = str(row.get(column) or "").strip()
    if not value:
        raise ParseError(code)
    return value


def _bool(value: object) -> bool:
    text = normalize_header(value)
    if text in {"", "否", "no", "false", "0", "n"}:
        return False
    if text in {"是", "yes", "true", "1", "y", "内部", "调拨"}:
        return True
    raise ParseError("INTERNAL_TRANSFER_FLAG_INVALID")


def _date_from_filename(filename: str) -> date | None:
    match = re.search(r"(?<!\d)(20\d{2})[-_.年]?(\d{1,2})[-_.月]?(\d{1,2})(?:日)?(?!\d)", filename)
    if not match:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def _rows_from_bytes(filename: str, payload: bytes) -> list[dict[str, object]]:
    suffix = Path(filename).suffix.lower()
    if suffix in {".csv", ".txt"}:
        try:
            text = payload.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text = payload.decode("gb18030")
            except UnicodeDecodeError as exc:
                raise ParseError("CORRUPT_ATTACHMENT") from exc
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise ParseError("COLUMN_MAPPING_EMPTY")
        return [dict(row) for row in reader]
    if suffix in {".xlsx", ".xlsm"}:
        try:
            import openpyxl  # type: ignore[import-not-found]
        except ImportError as exc:  # container has a locked dependency; tests can stay stdlib-only
            raise ParseError("XLSX_RUNTIME_DEPENDENCY_MISSING") from exc
        try:
            book = openpyxl.load_workbook(io.BytesIO(payload), read_only=True, data_only=True)
            sheet = book.active
            rows = list(sheet.iter_rows(values_only=True))
        except Exception as exc:  # openpyxl has many format-specific exceptions
            raise ParseError("CORRUPT_ATTACHMENT") from exc
        if not rows:
            raise ParseError("COLUMN_MAPPING_EMPTY")
        headers = [str(cell or "").strip() for cell in rows[0]]
        if not any(headers):
            raise ParseError("COLUMN_MAPPING_EMPTY")
        return [
            {headers[index]: row[index] if index < len(row) else None for index in range(len(headers))}
            for row in rows[1:]
            if any(cell not in (None, "") for cell in row)
        ]
    raise ParseError("UNSUPPORTED_ATTACHMENT")


def _business_date(rows: list[dict[str, object]], mapped: Mapping[str, str], filename: str) -> date:
    if "business_date" in mapped:
        values = {_parse_date(row.get(mapped["business_date"])) for row in rows}
        if len(values) != 1:
            raise ParseError("BUSINESS_DATE_AMBIGUOUS")
        return next(iter(values))
    filename_date = _date_from_filename(filename)
    if filename_date is None:
        raise ParseError("BUSINESS_DATE_MISSING")
    return filename_date


def parse_attachment(
    *,
    family: str,
    filename: str,
    payload: bytes,
    source: SourceRef,
) -> ParsedFacts:
    """Open and parse one source file into exactly one fact family.

    A file named as one family cannot silently become the other.  Callers must
    supply the source-gated family from the DWS message selection step.
    """

    if family not in TRANSACTION_FAMILIES | {ACCOUNT_FAMILY}:
        raise ParseError("DOCUMENT_FAMILY_UNSUPPORTED")
    if not payload:
        raise ParseError("CORRUPT_ATTACHMENT")
    rows = _rows_from_bytes(filename, payload)
    if not rows:
        raise ParseError("SOURCE_ROWS_EMPTY")
    mapped = _column_map(rows[0].keys())
    business_date = _business_date(rows, mapped, filename)
    if family == ACCOUNT_FAMILY:
        _required(mapped, ("company", "bank", "account", "ending"))
        accounts: list[AccountSnapshot] = []
        for row in rows:
            company = _required_text(row, mapped["company"], "ACCOUNT_COMPANY_MISSING")
            bank = _required_text(row, mapped["bank"], "ACCOUNT_BANK_MISSING")
            account = _required_text(row, mapped["account"], "ACCOUNT_NUMBER_MISSING")
            ending = parse_amount_to_fen(row.get(mapped["ending"]))
            opening = parse_amount_to_fen(row.get(mapped["opening"])) if mapped.get("opening") and str(row.get(mapped["opening"]) or "").strip() else None
            currency = str(row.get(mapped.get("currency", "")) or "CNY").strip().upper() or "CNY"
            if currency != "CNY":
                raise ParseError("CURRENCY_UNSUPPORTED")
            accounts.append(AccountSnapshot(business_date, company, bank, account, ending, opening, currency, source))
        return ParsedFacts(business_date, family, tuple(accounts), tuple(), source.source_version)

    _required(mapped, ("company", "bank", "account", "transaction_id"))
    if "inflow" not in mapped and "outflow" not in mapped and not ({"amount", "direction"} <= set(mapped)):
        raise ParseError("TRANSACTION_AMOUNT_MAPPING_MISSING")
    transactions: list[Transaction] = []
    for row in rows:
        company = _required_text(row, mapped["company"], "TRANSACTION_COMPANY_MISSING")
        bank = _required_text(row, mapped["bank"], "TRANSACTION_BANK_MISSING")
        account = _required_text(row, mapped["account"], "TRANSACTION_ACCOUNT_MISSING")
        transaction_id = _required_text(row, mapped["transaction_id"], "TRANSACTION_ID_MISSING")
        if "inflow" in mapped or "outflow" in mapped:
            inflow = parse_amount_to_fen(row.get(mapped["inflow"])) if "inflow" in mapped and str(row.get(mapped["inflow"]) or "").strip() else 0
            outflow = parse_amount_to_fen(row.get(mapped["outflow"])) if "outflow" in mapped and str(row.get(mapped["outflow"]) or "").strip() else 0
        else:
            amount = parse_amount_to_fen(row.get(mapped["amount"]))
            direction = normalize_header(row.get(mapped["direction"]))
            if direction in {"收入", "流入", "贷", "贷方", "in", "inflow"}:
                inflow, outflow = amount, 0
            elif direction in {"支出", "流出", "借", "借方", "out", "outflow"}:
                inflow, outflow = 0, amount
            else:
                raise ParseError("TRANSACTION_DIRECTION_INVALID")
        if inflow < 0 or outflow < 0 or (inflow and outflow):
            raise ParseError("TRANSACTION_FLOW_INVALID")
        adjustment = parse_amount_to_fen(row.get(mapped["adjustment"])) if mapped.get("adjustment") and str(row.get(mapped["adjustment"]) or "").strip() else 0
        internal = _bool(row.get(mapped["internal"])) if "internal" in mapped else False
        transfer_id = str(row.get(mapped.get("transfer_id", "")) or "").strip() or None
        if internal and not transfer_id:
            raise ParseError("INTERNAL_TRANSFER_ID_MISSING")
        transactions.append(Transaction(
            business_date,
            company,
            bank,
            account,
            transaction_id,
            _parse_datetime(row.get(mapped["occurred_at"])) if "occurred_at" in mapped else None,
            inflow,
            outflow,
            adjustment,
            internal,
            transfer_id,
            source,
        ))
    return ParsedFacts(business_date, family, tuple(), tuple(transactions), source.source_version)
