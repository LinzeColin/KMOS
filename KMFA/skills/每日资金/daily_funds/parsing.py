"""Deterministic parsers for the two required daily-funds fact families.

There is deliberately no heuristic OCR in this module.  PDFs/images, unknown
column shapes, MIME/magic mismatches and unsupported identifiers are rejected
with machine codes.  A later approved parser must bring its own real-sample
evidence and regression corpus rather than silently inventing financial facts.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Iterable, Mapping

from .contracts import ContractError, parse_amount_to_fen
from .models import AccountSnapshot, ParsedFacts, ParserEvidence, SourceRef, Transaction

ACCOUNT_FAMILY = "资金账户明细表"
TRANSACTION_FAMILIES = frozenset({"资金流水明细", "资金明细"})
PARSER_VERSION = "kmfa.daily_funds.parser.v2"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_OCCURRENCE_PATH = re.compile(
    r"^Private-KMDatabase/KMFA/daily_funds/raw/occurrences/"
    r"(?P<year>20\d{2})/(?P<month>0[1-9]|1[0-2])/"
    r"(?P<day>0[1-9]|[12]\d|3[01])/"
    r"(?P<message>[0-9a-f]{64})/(?P<index>0|[1-9]\d*)\.json$"
)
_MIME_TOKEN = re.compile(r"^[a-z0-9!#$&^_.+-]+/[a-z0-9!#$&^_.+-]+$")
_ZIP_MAGICS = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
_TEXT_SUFFIXES = frozenset({".csv", ".txt"})
_WORKBOOK_SUFFIXES = frozenset({".xlsx", ".xlsm"})
_ALLOWED_SUFFIXES = _TEXT_SUFFIXES | _WORKBOOK_SUFFIXES
_CSV_MIME = frozenset({
    "text/csv",
    "application/csv",
    "text/plain",
    "application/vnd.ms-excel",
    "application/octet-stream",
})
_XLSX_MIME = frozenset({
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",
})
_XLSM_MIME = frozenset({
    "application/vnd.ms-excel.sheet.macroenabled.12",
    "application/octet-stream",
})


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


def _is_blank(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _trim_trailing_blank(values: Iterable[object]) -> list[object]:
    materialized = list(values)
    while materialized and _is_blank(materialized[-1]):
        materialized.pop()
    return materialized


def _validated_headers(headers: Iterable[object]) -> list[str]:
    validated: list[str] = []
    seen: set[str] = set()
    for raw_header in headers:
        header = str(raw_header or "").strip()
        normalized = normalize_header(header)
        if not header or not normalized:
            raise ParseError("COLUMN_HEADER_EMPTY")
        if normalized in seen:
            raise ParseError("COLUMN_HEADER_DUPLICATE")
        seen.add(normalized)
        validated.append(header)
    if not validated:
        raise ParseError("COLUMN_MAPPING_EMPTY")
    return validated


def _column_map(headers: Iterable[object]) -> dict[str, str]:
    validated = _validated_headers(headers)
    normalized = {normalize_header(header): header for header in validated}
    mapped: dict[str, str] = {}
    for field, aliases in ALIASES.items():
        matches = [
            normalized[normalized_alias]
            for alias in aliases
            if (normalized_alias := normalize_header(alias)) in normalized
        ]
        if len(matches) > 1:
            raise ParseError("COLUMN_MAPPING_AMBIGUOUS_" + field.upper())
        if matches:
            mapped[field] = matches[0]
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
    if _is_blank(value):
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


def _required_identifier(row: Mapping[str, object], column: str, missing_code: str, non_text_code: str) -> str:
    value = row.get(column)
    if _is_blank(value):
        raise ParseError(missing_code)
    # Account and transaction identifiers can legally begin with zero.  An
    # Excel numeric cell has already lost that information, so it is not safe
    # to stringify and guess it back.
    if not isinstance(value, str):
        raise ParseError(non_text_code)
    text = value.strip()
    if not text:
        raise ParseError(missing_code)
    return text


def _optional_identifier(row: Mapping[str, object], column: str, non_text_code: str) -> str | None:
    value = row.get(column)
    if _is_blank(value):
        return None
    if not isinstance(value, str):
        raise ParseError(non_text_code)
    text = value.strip()
    return text or None


def _amount_to_fen(value: object) -> int:
    # XLSX numeric cells are exposed by openpyxl as Python floats.  Convert
    # their canonical decimal spelling before the integer-fen contract; never
    # perform binary float arithmetic or display-format rounding.
    if isinstance(value, float):
        return parse_amount_to_fen(str(value))
    return parse_amount_to_fen(value)


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


def _declared_mime(mime: str | None) -> str | None:
    if mime is None or not str(mime).strip():
        return None
    normalized = str(mime).split(";", 1)[0].strip().lower()
    if not _MIME_TOKEN.fullmatch(normalized):
        raise ParseError("MIME_DECLARATION_INVALID")
    return normalized


def inspect_attachment_format(*, filename: str, payload: bytes, mime: str | None = None) -> ParserEvidence:
    """Validate filename, declared MIME and byte magic before parser-open.

    This returns only values-free metadata.  It is deliberately not a global
    support claim: production support is recorded only after the private-Git
    readback byte subsequently opens and parses successfully.
    """

    suffix = Path(filename).suffix.lower()
    if suffix not in _ALLOWED_SUFFIXES:
        raise ParseError("UNSUPPORTED_ATTACHMENT")
    declared_mime = _declared_mime(mime)
    if suffix in _TEXT_SUFFIXES:
        if payload.startswith(_ZIP_MAGICS) or b"\x00" in payload:
            raise ParseError("FORMAT_MAGIC_MISMATCH")
        if declared_mime is not None and declared_mime not in _CSV_MIME:
            raise ParseError("MIME_SUFFIX_MISMATCH")
        return ParserEvidence("CSV", suffix, declared_mime, "TEXT", PARSER_VERSION)
    if not payload.startswith(_ZIP_MAGICS):
        raise ParseError("FORMAT_MAGIC_MISMATCH")
    allowed_mime = _XLSX_MIME if suffix == ".xlsx" else _XLSM_MIME
    if declared_mime is not None and declared_mime not in allowed_mime:
        raise ParseError("MIME_SUFFIX_MISMATCH")
    return ParserEvidence("XLSX" if suffix == ".xlsx" else "XLSM", suffix, declared_mime, "ZIP", PARSER_VERSION)


def _csv_delimiter(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            counts = {delimiter: line.count(delimiter) for delimiter in (",", "\t", ";")}
            maximum = max(counts.values())
            if maximum == 0:
                return ","
            winners = [delimiter for delimiter, count in counts.items() if count == maximum]
            if len(winners) != 1:
                raise ParseError("CSV_DELIMITER_AMBIGUOUS")
            return winners[0]
    raise ParseError("COLUMN_MAPPING_EMPTY")


def _csv_rows(payload: bytes) -> list[dict[str, object]]:
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = payload.decode("gb18030")
        except UnicodeDecodeError as exc:
            raise ParseError("CORRUPT_ATTACHMENT") from exc
    delimiter = _csv_delimiter(text)
    try:
        reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
        headers = _validated_headers(next(reader))
        rows: list[dict[str, object]] = []
        for raw_row in reader:
            if not raw_row or all(_is_blank(value) for value in raw_row):
                continue
            if len(raw_row) != len(headers):
                raise ParseError("CSV_ROW_WIDTH_INVALID")
            rows.append(dict(zip(headers, raw_row)))
        return rows
    except StopIteration as exc:
        raise ParseError("COLUMN_MAPPING_EMPTY") from exc
    except csv.Error as exc:
        raise ParseError("CORRUPT_ATTACHMENT") from exc


def _xlsx_rows(payload: bytes) -> list[dict[str, object]]:
    try:
        import openpyxl  # type: ignore[import-not-found]
    except ImportError as exc:  # container has a locked dependency
        raise ParseError("XLSX_RUNTIME_DEPENDENCY_MISSING") from exc
    formula_book = value_book = None
    try:
        # Cached formula values must not be treated as an independently
        # verified financial source.  Open the same workbook in formula view
        # first, then only read values if its active sheet contains no formula.
        formula_book = openpyxl.load_workbook(io.BytesIO(payload), read_only=True, data_only=False, keep_vba=False)
        formula_sheet = formula_book.active
        for formula_row in formula_sheet.iter_rows():
            if any(cell.data_type == "f" for cell in formula_row):
                raise ParseError("XLSX_FORMULA_UNSUPPORTED")
        value_book = openpyxl.load_workbook(io.BytesIO(payload), read_only=True, data_only=True, keep_vba=False)
        sheet = value_book.active
        iterator = sheet.iter_rows(values_only=True)
        headers = _validated_headers(_trim_trailing_blank(next(iterator)))
        rows: list[dict[str, object]] = []
        for raw_row in iterator:
            values = list(raw_row)
            if any(not _is_blank(value) for value in values[len(headers):]):
                raise ParseError("XLSX_ROW_WIDTH_INVALID")
            values = values[:len(headers)]
            if not values or all(_is_blank(value) for value in values):
                continue
            rows.append({header: values[index] if index < len(values) else None for index, header in enumerate(headers)})
        return rows
    except ParseError:
        raise
    except StopIteration as exc:
        raise ParseError("COLUMN_MAPPING_EMPTY") from exc
    except Exception as exc:  # openpyxl has many format-specific exceptions
        raise ParseError("CORRUPT_ATTACHMENT") from exc
    finally:
        if formula_book is not None:
            formula_book.close()
        if value_book is not None:
            value_book.close()


def _rows_from_bytes(filename: str, payload: bytes, mime: str | None) -> tuple[list[dict[str, object]], ParserEvidence]:
    evidence = inspect_attachment_format(filename=filename, payload=payload, mime=mime)
    if evidence.format == "CSV":
        return _csv_rows(payload), evidence
    return _xlsx_rows(payload), evidence


def _validate_source(source: SourceRef, payload: bytes) -> None:
    if not all(isinstance(value, str) and _SHA256.fullmatch(value) for value in (
        source.attachment_sha256,
        source.message_id_hash,
        source.source_version,
    )):
        raise ParseError("SOURCE_LINEAGE_INVALID")
    if source.source_version != source.attachment_sha256:
        raise ParseError("SOURCE_VERSION_MISMATCH")
    if sha256(payload).hexdigest() != source.attachment_sha256:
        raise ParseError("SOURCE_PAYLOAD_HASH_MISMATCH")
    match = _OCCURRENCE_PATH.fullmatch(source.occurrence_path)
    if match is None or match.group("message") != source.message_id_hash:
        raise ParseError("SOURCE_LINEAGE_INVALID")
    try:
        date(int(match.group("year")), int(match.group("month")), int(match.group("day")))
    except ValueError as exc:
        raise ParseError("SOURCE_LINEAGE_INVALID") from exc


def _business_date(rows: list[dict[str, object]], mapped: Mapping[str, str], filename: str) -> date:
    filename_date = _date_from_filename(filename)
    if "business_date" in mapped:
        values = {_parse_date(row.get(mapped["business_date"])) for row in rows}
        if len(values) != 1:
            raise ParseError("BUSINESS_DATE_AMBIGUOUS")
        business_date = next(iter(values))
        if filename_date is not None and filename_date != business_date:
            raise ParseError("BUSINESS_DATE_FILENAME_MISMATCH")
        return business_date
    if filename_date is None:
        raise ParseError("BUSINESS_DATE_MISSING")
    return filename_date


def parse_attachment(
    *,
    family: str,
    filename: str,
    payload: bytes,
    source: SourceRef,
    mime: str | None = None,
) -> ParsedFacts:
    """Open and parse one source file into exactly one fact family.

    A file named as one family cannot silently become the other.  Callers must
    supply the source-gated family from the DWS message selection step.
    """

    if family not in TRANSACTION_FAMILIES | {ACCOUNT_FAMILY}:
        raise ParseError("DOCUMENT_FAMILY_UNSUPPORTED")
    if not payload:
        raise ParseError("CORRUPT_ATTACHMENT")
    _validate_source(source, payload)
    rows, parser_evidence = _rows_from_bytes(filename, payload, mime)
    if not rows:
        raise ParseError("SOURCE_ROWS_EMPTY")
    mapped = _column_map(rows[0].keys())
    business_date = _business_date(rows, mapped, filename)
    if family == ACCOUNT_FAMILY:
        _required(mapped, ("company", "bank", "account", "ending"))
        accounts: list[AccountSnapshot] = []
        seen_accounts: set[tuple[date, str, str, str]] = set()
        for row in rows:
            company = _required_text(row, mapped["company"], "ACCOUNT_COMPANY_MISSING")
            bank = _required_text(row, mapped["bank"], "ACCOUNT_BANK_MISSING")
            account = _required_identifier(
                row,
                mapped["account"],
                "ACCOUNT_NUMBER_MISSING",
                "ACCOUNT_NUMBER_NON_TEXT",
            )
            key = (business_date, company, bank, account)
            if key in seen_accounts:
                raise ParseError("ACCOUNT_SNAPSHOT_DUPLICATE")
            seen_accounts.add(key)
            ending = _amount_to_fen(row.get(mapped["ending"]))
            opening = _amount_to_fen(row.get(mapped["opening"])) if mapped.get("opening") and not _is_blank(row.get(mapped["opening"])) else None
            currency = str(row.get(mapped.get("currency", "")) or "CNY").strip().upper() or "CNY"
            if currency != "CNY":
                raise ParseError("CURRENCY_UNSUPPORTED")
            accounts.append(AccountSnapshot(business_date, company, bank, account, ending, opening, currency, source))
        return ParsedFacts(business_date, family, tuple(accounts), tuple(), source.source_version, parser_evidence)

    _required(mapped, ("company", "bank", "account", "transaction_id"))
    if "inflow" not in mapped and "outflow" not in mapped and not ({"amount", "direction"} <= set(mapped)):
        raise ParseError("TRANSACTION_AMOUNT_MAPPING_MISSING")
    transactions: list[Transaction] = []
    seen_transactions: set[tuple[date, str, str, str, str]] = set()
    for row in rows:
        company = _required_text(row, mapped["company"], "TRANSACTION_COMPANY_MISSING")
        bank = _required_text(row, mapped["bank"], "TRANSACTION_BANK_MISSING")
        account = _required_identifier(
            row,
            mapped["account"],
            "TRANSACTION_ACCOUNT_MISSING",
            "TRANSACTION_ACCOUNT_NON_TEXT",
        )
        transaction_id = _required_identifier(
            row,
            mapped["transaction_id"],
            "TRANSACTION_ID_MISSING",
            "TRANSACTION_ID_NON_TEXT",
        )
        key = (business_date, company, bank, account, transaction_id)
        if key in seen_transactions:
            raise ParseError("TRANSACTION_DUPLICATE")
        seen_transactions.add(key)
        if "inflow" in mapped or "outflow" in mapped:
            inflow = _amount_to_fen(row.get(mapped["inflow"])) if "inflow" in mapped and not _is_blank(row.get(mapped["inflow"])) else 0
            outflow = _amount_to_fen(row.get(mapped["outflow"])) if "outflow" in mapped and not _is_blank(row.get(mapped["outflow"])) else 0
        else:
            amount = _amount_to_fen(row.get(mapped["amount"]))
            direction = normalize_header(row.get(mapped["direction"]))
            if direction in {"收入", "流入", "贷", "贷方", "in", "inflow"}:
                inflow, outflow = amount, 0
            elif direction in {"支出", "流出", "借", "借方", "out", "outflow"}:
                inflow, outflow = 0, amount
            else:
                raise ParseError("TRANSACTION_DIRECTION_INVALID")
        if inflow < 0 or outflow < 0 or (inflow and outflow):
            raise ParseError("TRANSACTION_FLOW_INVALID")
        adjustment = _amount_to_fen(row.get(mapped["adjustment"])) if mapped.get("adjustment") and not _is_blank(row.get(mapped["adjustment"])) else 0
        internal = _bool(row.get(mapped["internal"])) if "internal" in mapped else False
        transfer_id = _optional_identifier(row, mapped["transfer_id"], "TRANSFER_ID_NON_TEXT") if "transfer_id" in mapped else None
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
    return ParsedFacts(business_date, family, tuple(), tuple(transactions), source.source_version, parser_evidence)
