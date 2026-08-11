"""Deterministic parsers for the two required daily-funds fact families.

There is deliberately no heuristic OCR in this module.  Only a bounded,
deterministic offline OCR fallback may open a supported image or scanned PDF;
unknown column shapes, MIME/magic mismatches and unsupported identifiers are
rejected with machine codes.  OCR results remain unsupported until real-sample
layout calibration proves the source profile, rather than silently inventing
financial facts.
"""

from __future__ import annotations

import csv
import io
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from datetime import date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from .contracts import ContractError, parse_amount_to_fen
from .models import CashflowObservation, AccountSnapshot, ParsedFacts, ParserEvidence, SourceRef, Transaction

ACCOUNT_FAMILY = "资金账户明细表"
TRANSACTION_FAMILIES = frozenset({"资金流水明细", "资金明细"})
# v7 keeps the bounded deterministic OCR fallback and aligns transaction
# identity requirements to the frozen task-pack schema: bank_id is optional
# and a source-row fact identifier is used only when a source does not expose
# a transaction identifier.
#
# It retains v5's narrow source-classification rule: a generic ``资金明细``
# image may be treated as an account snapshot only when its OCR table satisfies
# the account schema *and* cannot satisfy the transaction schema.  When both
# candidates fail at the same values-free OCR phase, v7 retains that bounded
# diagnosis for the protected capability receipt.  It never turns a failed
# candidate into a fact or relaxes either schema.  Capability receipts are
# versioned, so a rule change cannot inherit a prior parser's production-
# support assertion.
PARSER_VERSION = "kmfa.daily_funds.parser.v7"
# This parser is deliberately separate from ``PARSER_VERSION``.  It can
# create a chart-only receipt from a narrow receipt/payment screenshot without
# weakening the two-fact account-balance publication contract.
CASHFLOW_OBSERVATION_PARSER_VERSION = "kmfa.daily_funds.cashflow_observation.v2"

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
_OCR_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".bmp", ".webp"})
_OCR_PDF_SUFFIXES = frozenset({".pdf"})
_OCR_SUFFIXES = _OCR_IMAGE_SUFFIXES | _OCR_PDF_SUFFIXES
_CAPABILITY_SUFFIXES = _ALLOWED_SUFFIXES | frozenset({
    ".xls", ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp",
})
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
_OCR_IMAGE_MIME = {
    ".png": frozenset({"image/png", "application/octet-stream"}),
    ".jpg": frozenset({"image/jpeg", "application/octet-stream"}),
    ".jpeg": frozenset({"image/jpeg", "application/octet-stream"}),
    ".bmp": frozenset({"image/bmp", "image/x-ms-bmp", "application/octet-stream"}),
    ".webp": frozenset({"image/webp", "application/octet-stream"}),
    ".pdf": frozenset({"application/pdf", "application/octet-stream"}),
}
_OCR_MAGIC_BY_SUFFIX = {
    ".png": "PNG",
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".bmp": "BMP",
    ".webp": "WEBP",
    ".pdf": "PDF",
}
OCR_MIN_CONFIDENCE_BPS = 9_800
OCR_MAX_ATTACHMENT_BYTES = 50 * 1024 * 1024
OCR_TIMEOUT_SECONDS = 90
OCR_LANGUAGE = "chi_sim+eng"


class ParseError(ContractError):
    pass


# A generic source label is intentionally never enough to classify a financial
# fact.  These sets describe only a uniform *parser phase* across the two
# candidate schemas; they contain no OCR text, field name, account, amount or
# source identifier.  Mixed phases remain the existing generic unresolved
# result so that a diagnostic cannot overstate what was observed.
_GENERIC_OCR_HEADER_PHASE_CODES = frozenset({
    "OCR_HEADER_MAPPING_MISSING",
    "OCR_HEADER_ROW_AMBIGUOUS",
    "OCR_COLUMN_MAPPING_AMBIGUOUS",
    "COLUMN_HEADER_DUPLICATE",
})
_GENERIC_OCR_ROW_PHASE_CODES = frozenset({
    "OCR_ROW_REQUIRED_CELL_MISSING",
    "SOURCE_ROWS_EMPTY",
})
_GENERIC_OCR_CONFIDENCE_PHASE_CODES = frozenset({"OCR_LOW_CONFIDENCE"})


@dataclass(frozen=True)
class OcrParsedAttachment:
    """A deterministic OCR result that has not yet crossed the runtime template gate.

    The layout fingerprint deliberately contains only canonical field names,
    geometry buckets and parser metadata.  It contains no OCR text, document
    identifier, amount or account value, so the runtime may retain it in its
    private journal as a calibration key without creating a second raw store.
    """

    facts: ParsedFacts
    layout_fingerprint: str


@dataclass(frozen=True)
class _OcrWord:
    text: str
    confidence_bps: int
    page: int
    block: int
    paragraph: int
    line: int
    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True)
class _OcrHeaderCell:
    label: str
    field: str | None
    left: int
    right: int
    top: int
    bottom: int
    confidence_bps: int


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
    "outflow": ("流出", "支出", "转出", "借方发生额", "出账金额"),
    "category": ("收支类别", "类别", "费用类别"),
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


def _capability_magic(payload: bytes) -> str:
    """Classify bytes for a values-free capability receipt, never parsing them.

    This deliberately stops at stable file signatures.  In particular, a
    recognised image or PDF signature is evidence that the attachment needs a
    reviewed parser, *not* permission to OCR it or treat it as financial data.
    """

    if not payload:
        return "EMPTY"
    if payload.startswith(_ZIP_MAGICS):
        return "ZIP"
    if payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if payload.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if payload.startswith((b"GIF87a", b"GIF89a")):
        return "GIF"
    if payload.startswith(b"BM"):
        return "BMP"
    if payload.startswith(b"RIFF") and payload[8:12] == b"WEBP":
        return "WEBP"
    if payload.startswith(b"%PDF-"):
        return "PDF"
    if payload.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "OLE"
    sample = payload[:4096]
    if b"\x00" in sample:
        return "BINARY"
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            sample.decode(encoding)
            return "TEXT"
        except UnicodeDecodeError:
            continue
    return "BINARY"


def attachment_capability_metadata(*, filename: str, payload: bytes, mime: str | None = None) -> tuple[str, str | None, str]:
    """Return bounded, values-free metadata for every Git-readback attachment.

    The returned tuple can safely be persisted for a supported *or* rejected
    type.  It intentionally does not inspect document text, OCR images, or
    derive a financial family from a filename.
    """

    candidate_suffix = Path(filename).suffix.lower()
    suffix = candidate_suffix if candidate_suffix in _CAPABILITY_SUFFIXES else "UNKNOWN_SUFFIX"
    try:
        declared_mime = _declared_mime(mime)
    except ParseError:
        # The parse path records MIME_DECLARATION_INVALID as the failure code;
        # retaining an arbitrary malformed string would violate the redacted
        # capability-journal contract.
        declared_mime = None
    return suffix, declared_mime, _capability_magic(payload)


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
        # first, then only read values if its sole worksheet contains no formula.
        formula_book = openpyxl.load_workbook(io.BytesIO(payload), read_only=True, data_only=False, keep_vba=False)
        # Until a target-group real sample freezes an explicit multi-sheet
        # template, selecting ``active`` would silently discard the remaining
        # worksheets.  A financial source must be complete or fail closed;
        # reject every multi-sheet workbook rather than guessing where facts
        # belong (including a hidden or auxiliary sheet).
        if len(formula_book.worksheets) != 1:
            raise ParseError("XLSX_WORKSHEET_AMBIGUOUS")
        formula_sheet = formula_book.worksheets[0]
        for formula_row in formula_sheet.iter_rows():
            if any(cell.data_type == "f" for cell in formula_row):
                raise ParseError("XLSX_FORMULA_UNSUPPORTED")
        value_book = openpyxl.load_workbook(io.BytesIO(payload), read_only=True, data_only=True, keep_vba=False)
        if len(value_book.worksheets) != 1:
            raise ParseError("XLSX_WORKSHEET_AMBIGUOUS")
        sheet = value_book.worksheets[0]
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


def _ocr_integer(value: object, *, code: str, minimum: int | None = None) -> int:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError) as exc:
        raise ParseError(code) from exc
    if minimum is not None and parsed < minimum:
        raise ParseError(code)
    return parsed


def _ocr_confidence_bps(value: object) -> int:
    try:
        score = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ParseError("OCR_CONFIDENCE_INVALID") from exc
    if not score.is_finite() or score < 0 or score > 100:
        raise ParseError("OCR_CONFIDENCE_INVALID")
    return int((score * 100).to_integral_value(rounding=ROUND_FLOOR))


def _validate_ocr_min_confidence(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1 or value > 10_000:
        raise ParseError("OCR_CONFIDENCE_THRESHOLD_INVALID")
    return value


def inspect_ocr_attachment_format(*, filename: str, payload: bytes, mime: str | None = None) -> ParserEvidence:
    """Validate one image or scanned-PDF before a deterministic OCR open.

    OCR is not a bypass around the normal attachment contract: a suffix, magic
    or declared MIME disagreement is a hard failure.  The result contains only
    format metadata and can therefore be used in the existing redacted
    capability journal.
    """

    suffix = Path(filename).suffix.lower()
    if suffix not in _OCR_SUFFIXES:
        raise ParseError("UNSUPPORTED_ATTACHMENT")
    if len(payload) > OCR_MAX_ATTACHMENT_BYTES:
        raise ParseError("OCR_ATTACHMENT_TOO_LARGE")
    magic = _capability_magic(payload)
    if magic != _OCR_MAGIC_BY_SUFFIX[suffix]:
        raise ParseError("FORMAT_MAGIC_MISMATCH")
    declared_mime = _declared_mime(mime)
    if declared_mime is not None and declared_mime not in _OCR_IMAGE_MIME[suffix]:
        raise ParseError("MIME_SUFFIX_MISMATCH")
    return ParserEvidence(
        format=f"OCR_{magic}",
        suffix=suffix,
        declared_mime=declared_mime,
        magic=magic,
        parser_version=PARSER_VERSION,
    )


def is_ocr_attachment(filename: str) -> bool:
    """Whether a filename belongs to the explicit image/scanned-PDF fallback."""

    return Path(filename).suffix.lower() in _OCR_SUFFIXES


def _run_ocr_command(
    command: list[str],
    *,
    runner: Callable[..., Any],
    failure_code: str,
) -> str:
    """Run an offline OCR utility without retaining its diagnostic stream."""

    try:
        completed = runner(
            command,
            capture_output=True,
            text=True,
            timeout=OCR_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ParseError("OCR_RUNTIME_UNAVAILABLE") from exc
    except subprocess.TimeoutExpired as exc:
        raise ParseError("OCR_TIMEOUT") from exc
    except OSError as exc:
        raise ParseError("OCR_RUNTIME_UNAVAILABLE") from exc
    if getattr(completed, "returncode", 1) != 0:
        raise ParseError(failure_code)
    stdout = getattr(completed, "stdout", "")
    return stdout if isinstance(stdout, str) else ""


def _pdf_page_count(path: Path, *, runner: Callable[..., Any]) -> int:
    output = _run_ocr_command(["pdfinfo", str(path)], runner=runner, failure_code="OCR_PDF_METADATA_FAILED")
    pages: int | None = None
    for line in output.splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip().lower() == "pages":
            if pages is not None:
                raise ParseError("OCR_PDF_METADATA_INVALID")
            pages = _ocr_integer(value.strip(), code="OCR_PDF_METADATA_INVALID", minimum=1)
    if pages is None:
        raise ParseError("OCR_PDF_METADATA_INVALID")
    return pages


def _ocr_tsv(
    *,
    payload: bytes,
    evidence: ParserEvidence,
    runner: Callable[..., Any],
) -> str:
    """Generate in-memory Tesseract TSV for exactly one bounded document page.

    The input file and rendered PDF page live only inside a temporary directory.
    Neither OCR text nor utility stderr is written to a log, status file, Git
    repository or exception message.
    """

    with tempfile.TemporaryDirectory(prefix="daily-funds-ocr-") as temporary:
        root = Path(temporary)
        source = root / f"input{evidence.suffix}"
        source.write_bytes(payload)
        image = source
        if evidence.magic == "PDF":
            if _pdf_page_count(source, runner=runner) != 1:
                raise ParseError("OCR_PDF_PAGE_AMBIGUOUS")
            prefix = root / "render"
            _run_ocr_command(
                ["pdftoppm", "-png", "-r", "300", "-f", "1", "-l", "1", str(source), str(prefix)],
                runner=runner,
                failure_code="OCR_PDF_RENDER_FAILED",
            )
            rendered = tuple(sorted(root.glob("render-*.png")))
            if len(rendered) != 1 or rendered[0].is_symlink() or not rendered[0].is_file():
                raise ParseError("OCR_PDF_RENDER_FAILED")
            image = rendered[0]
        return _run_ocr_command(
            ["tesseract", str(image), "stdout", "-l", OCR_LANGUAGE, "--psm", "6", "tsv"],
            runner=runner,
            failure_code="OCR_ENGINE_FAILED",
        )


def _parse_tesseract_tsv(text: str) -> tuple[_OcrWord, ...]:
    expected = {
        "level", "page_num", "block_num", "par_num", "line_num", "word_num",
        "left", "top", "width", "height", "conf", "text",
    }
    try:
        reader = csv.DictReader(io.StringIO(text, newline=""), delimiter="\t", strict=True)
    except csv.Error as exc:
        raise ParseError("OCR_TSV_INVALID") from exc
    if reader.fieldnames is None or set(reader.fieldnames) != expected or len(reader.fieldnames) != len(expected):
        raise ParseError("OCR_TSV_INVALID")
    words: list[_OcrWord] = []
    try:
        for raw in reader:
            if raw.get("level") != "5":
                continue
            token = str(raw.get("text") or "").strip()
            if not token:
                continue
            if len(token) > 512:
                raise ParseError("OCR_TOKEN_INVALID")
            words.append(_OcrWord(
                text=token,
                confidence_bps=_ocr_confidence_bps(raw.get("conf")),
                page=_ocr_integer(raw.get("page_num"), code="OCR_TSV_INVALID", minimum=1),
                block=_ocr_integer(raw.get("block_num"), code="OCR_TSV_INVALID", minimum=0),
                paragraph=_ocr_integer(raw.get("par_num"), code="OCR_TSV_INVALID", minimum=0),
                line=_ocr_integer(raw.get("line_num"), code="OCR_TSV_INVALID", minimum=0),
                left=_ocr_integer(raw.get("left"), code="OCR_TSV_INVALID", minimum=0),
                top=_ocr_integer(raw.get("top"), code="OCR_TSV_INVALID", minimum=0),
                width=_ocr_integer(raw.get("width"), code="OCR_TSV_INVALID", minimum=1),
                height=_ocr_integer(raw.get("height"), code="OCR_TSV_INVALID", minimum=1),
            ))
    except csv.Error as exc:
        raise ParseError("OCR_TSV_INVALID") from exc
    if not words:
        raise ParseError("OCR_OUTPUT_EMPTY")
    return tuple(words)


def _ocr_lines(words: Iterable[_OcrWord]) -> tuple[tuple[_OcrWord, ...], ...]:
    grouped: dict[tuple[int, int, int, int], list[_OcrWord]] = {}
    for word in words:
        grouped.setdefault((word.page, word.block, word.paragraph, word.line), []).append(word)
    ordered = sorted(
        grouped.values(),
        key=lambda row: (
            min(word.page for word in row),
            min(word.top for word in row),
            min(word.left for word in row),
            min(word.block for word in row),
            min(word.paragraph for word in row),
            min(word.line for word in row),
        ),
    )
    return tuple(tuple(sorted(row, key=lambda word: (word.left, word.top, word.text))) for row in ordered)


def _ocr_visual_rows(lines: tuple[tuple[_OcrWord, ...], ...]) -> tuple[tuple[int, tuple[_OcrWord, ...]], ...]:
    """Reassemble one visually aligned row when Tesseract splits its columns.

    Tesseract can assign separate ``line_num`` values to cells that share one
    rendered table row.  Group only OCR lines whose vertical boxes overlap;
    adjacent rows remain separate, and callers still apply the same strict
    alias, confidence, and row-total gates after this layout-only repair.
    """

    grouped: list[tuple[int, tuple[_OcrWord, ...]]] = []
    current_index: int | None = None
    current_top: int | None = None
    current_bottom: int | None = None
    current_words: list[_OcrWord] = []

    def flush() -> None:
        nonlocal current_index, current_top, current_bottom, current_words
        if current_index is not None and current_words:
            grouped.append((current_index, tuple(sorted(current_words, key=lambda word: (word.left, word.top, word.text)))))
        current_index = None
        current_top = None
        current_bottom = None
        current_words = []

    for index, words in enumerate(lines):
        line_top = min(word.top for word in words)
        line_bottom = max(word.top + word.height for word in words)
        if current_index is None:
            current_index = index
            current_top = line_top
            current_bottom = line_bottom
            current_words.extend(words)
            continue
        assert current_top is not None and current_bottom is not None
        if line_top <= current_bottom and line_bottom >= current_top:
            current_top = min(current_top, line_top)
            current_bottom = max(current_bottom, line_bottom)
            current_words.extend(words)
            continue
        flush()
        current_index = index
        current_top = line_top
        current_bottom = line_bottom
        current_words.extend(words)
    flush()
    return tuple(grouped)


def _ocr_alias_candidates(words: tuple[_OcrWord, ...]) -> list[tuple[int, int, str]]:
    aliases: dict[str, set[str]] = {}
    for field, values in ALIASES.items():
        for alias in values:
            aliases.setdefault(normalize_header(alias), set()).add(field)
    candidates: list[tuple[int, int, str]] = []
    for start in range(len(words)):
        for end in range(start + 1, min(len(words), start + 3) + 1):
            fields = aliases.get(normalize_header("".join(word.text for word in words[start:end])))
            if fields is None:
                continue
            if len(fields) != 1:
                raise ParseError("OCR_COLUMN_MAPPING_AMBIGUOUS")
            candidates.append((start, end, next(iter(fields))))
    return candidates


def _ocr_header_cells(words: tuple[_OcrWord, ...]) -> tuple[_OcrHeaderCell, ...]:
    candidates = _ocr_alias_candidates(words)
    # Duplicate non-overlapping aliases are a source ambiguity, never a reason
    # to select whichever one Tesseract happened to emit first.
    for field in {field for _, _, field in candidates}:
        positions = [(start, end) for start, end, candidate_field in candidates if candidate_field == field]
        if any(end_a <= start_b or end_b <= start_a for index, (start_a, end_a) in enumerate(positions) for start_b, end_b in positions[index + 1:]):
            raise ParseError("OCR_COLUMN_MAPPING_AMBIGUOUS")
    selected: list[tuple[int, int, str]] = []
    occupied: set[int] = set()
    fields: set[str] = set()
    for start, end, field in sorted(candidates, key=lambda item: (-(item[1] - item[0]), item[0], item[2])):
        if field in fields or any(index in occupied for index in range(start, end)):
            continue
        selected.append((start, end, field))
        occupied.update(range(start, end))
        fields.add(field)
    selected_by_start = {start: (end, field) for start, end, field in selected}
    cells: list[_OcrHeaderCell] = []
    index = 0
    while index < len(words):
        end, field = selected_by_start.get(index, (index + 1, None))
        segment = words[index:end]
        cells.append(_OcrHeaderCell(
            label="".join(word.text for word in segment),
            field=field,
            left=min(word.left for word in segment),
            right=max(word.left + word.width for word in segment),
            top=min(word.top for word in segment),
            bottom=max(word.top + word.height for word in segment),
            confidence_bps=min(word.confidence_bps for word in segment),
        ))
        index = end
    if len({cell.label for cell in cells}) != len(cells):
        raise ParseError("COLUMN_HEADER_DUPLICATE")
    return tuple(sorted(cells, key=lambda cell: (cell.left, cell.right, cell.label)))


def _ocr_required_fields(family: str, fields: set[str]) -> bool:
    if family == ACCOUNT_FAMILY:
        return {"company", "bank", "account", "ending"} <= fields
    if family in TRANSACTION_FAMILIES:
        # ``bank_id`` is optional and the sealed transaction schema has no
        # required source transaction identifier.  A deterministic source-row
        # identity is assigned later only for deduplication; it is never a
        # fabricated business identifier or financial value.
        identity = {"company", "account"} <= fields
        flow = "inflow" in fields or "outflow" in fields
        amount_direction = {"amount", "direction"} <= fields
        return identity and (flow or amount_direction) and not (flow and amount_direction)
    raise ParseError("DOCUMENT_FAMILY_UNSUPPORTED")


def _select_ocr_header(
    lines: tuple[tuple[_OcrWord, ...], ...],
    *,
    family: str,
    min_confidence_bps: int,
) -> tuple[int, tuple[_OcrHeaderCell, ...]]:
    candidates: list[tuple[int, tuple[_OcrHeaderCell, ...], int]] = []
    for index, words in enumerate(lines):
        try:
            cells = _ocr_header_cells(words)
        except ParseError:
            continue
        fields = {cell.field for cell in cells if cell.field is not None}
        if not _ocr_required_fields(family, fields):
            continue
        candidates.append((index, cells, len(fields)))
    if not candidates:
        raise ParseError("OCR_HEADER_MAPPING_MISSING")
    candidates.sort(key=lambda item: item[2], reverse=True)
    if len(candidates) > 1 and candidates[0][2] == candidates[1][2]:
        raise ParseError("OCR_HEADER_ROW_AMBIGUOUS")
    index, cells, _ = candidates[0]
    if any(cell.field is not None and cell.confidence_bps < min_confidence_bps for cell in cells):
        raise ParseError("OCR_LOW_CONFIDENCE")
    return index, cells


def _ocr_cell_index(word: _OcrWord, cells: tuple[_OcrHeaderCell, ...]) -> int:
    center_twice = 2 * word.left + word.width
    for index in range(len(cells) - 1):
        # Compare both centers using integers.  ``center_twice`` is twice the
        # word centre; the midpoint between adjacent header centres is one
        # half of the sum below, so its equivalent scale is
        # ``2 * center_twice < header_center_sum``.  Keeping this integral
        # avoids a rounded boundary moving a money field into its neighbour.
        header_center_sum = cells[index].left + cells[index].right + cells[index + 1].left + cells[index + 1].right
        if 2 * center_twice < header_center_sum:
            return index
    return len(cells) - 1


def _ocr_rows(
    lines: tuple[tuple[_OcrWord, ...], ...],
    *,
    header_index: int,
    cells: tuple[_OcrHeaderCell, ...],
    family: str,
    min_confidence_bps: int,
) -> list[dict[str, object]]:
    header_page = lines[header_index][0].page
    header_bottom = max(cell.bottom for cell in cells)
    field_by_label = {cell.label: cell.field for cell in cells}
    rows: list[dict[str, object]] = []
    for words in lines[header_index + 1:]:
        if words[0].page != header_page or min(word.top for word in words) <= header_bottom:
            continue
        by_index: dict[int, list[_OcrWord]] = {index: [] for index in range(len(cells))}
        for word in words:
            by_index[_ocr_cell_index(word, cells)].append(word)
        row: dict[str, object] = {}
        confidence: dict[str, int | None] = {}
        for index, cell in enumerate(cells):
            values = sorted(by_index[index], key=lambda word: (word.left, word.top, word.text))
            row[cell.label] = "".join(word.text for word in values)
            confidence[cell.label] = min((word.confidence_bps for word in values), default=None)
        mapped = {field: str(row[label] or "") for label, field in field_by_label.items() if field is not None}
        if not any(value for value in mapped.values()):
            continue
        fields = {field for field, value in mapped.items() if value}
        if not _ocr_required_fields(family, fields):
            raise ParseError("OCR_ROW_REQUIRED_CELL_MISSING")
        for label, field in field_by_label.items():
            if field is not None and row[label] and (confidence[label] is None or confidence[label] < min_confidence_bps):
                raise ParseError("OCR_LOW_CONFIDENCE")
        rows.append(row)
    if not rows:
        raise ParseError("SOURCE_ROWS_EMPTY")
    return rows


def _ocr_layout_fingerprint(
    *,
    family: str,
    evidence: ParserEvidence,
    cells: tuple[_OcrHeaderCell, ...],
) -> str:
    width = max(cell.right for cell in cells)
    if width <= 0:
        raise ParseError("OCR_LAYOUT_INVALID")
    layout = {
        "family": family,
        "format": evidence.format,
        "magic": evidence.magic,
        "columns": [cell.field or "UNMAPPED" for cell in cells],
        "centers_bps": [((cell.left + cell.right) * 10_000) // (2 * width) for cell in cells],
    }
    return sha256(json.dumps(layout, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def deterministic_ocr_runtime_ready(*, runner: Callable[..., Any] = subprocess.run) -> bool:
    """Return whether the isolated image has the two offline OCR tools.

    This uses no document input and intentionally discards all command output.
    It is suitable for the values-free runtime isolation audit, not as a claim
    that any source layout or financial value has been verified.
    """

    try:
        languages = _run_ocr_command(["tesseract", "--list-langs"], runner=runner, failure_code="OCR_RUNTIME_UNAVAILABLE")
        _run_ocr_command(["pdfinfo", "-v"], runner=runner, failure_code="OCR_RUNTIME_UNAVAILABLE")
        _run_ocr_command(["pdftoppm", "-v"], runner=runner, failure_code="OCR_RUNTIME_UNAVAILABLE")
    except ParseError:
        return False
    return "chi_sim" in {line.strip() for line in languages.splitlines()}


def _parse_ocr_table(
    *,
    family: str,
    filename: str,
    source: SourceRef,
    evidence: ParserEvidence,
    lines: tuple[tuple[_OcrWord, ...], ...],
    min_confidence_bps: int,
) -> OcrParsedAttachment:
    """Parse one already-OCRed table under one exact source-family schema."""

    header_index, cells = _select_ocr_header(lines, family=family, min_confidence_bps=min_confidence_bps)
    rows = _ocr_rows(lines, header_index=header_index, cells=cells, family=family, min_confidence_bps=min_confidence_bps)
    facts = _facts_from_rows(family=family, filename=filename, source=source, rows=rows, parser_evidence=evidence)
    return OcrParsedAttachment(
        facts=facts,
        layout_fingerprint=_ocr_layout_fingerprint(family=family, evidence=evidence, cells=cells),
    )


def _select_ocr_cashflow_header(
    lines: tuple[tuple[_OcrWord, ...], ...],
    *,
    min_confidence_bps: int,
) -> tuple[int, tuple[_OcrHeaderCell, ...]]:
    """Select the one strict receipt/payment table header in an OCR image.

    The chart-only profile deliberately requires both money directions, a
    date, and a bank column.  That is narrow enough to avoid treating an
    arbitrary image containing a number as financial evidence, while still
    matching the existing daily ``资金明细`` screenshot layout.
    """

    required = {"business_date", "inflow", "outflow", "bank"}
    candidates: list[tuple[int, tuple[_OcrHeaderCell, ...], int]] = []
    for index, words in enumerate(lines):
        try:
            cells = _ocr_header_cells(words)
        except ParseError:
            continue
        fields = {cell.field for cell in cells if cell.field is not None}
        if not required <= fields:
            continue
        candidates.append((index, cells, len(fields)))
    # Receipt/payment screenshots can put each heading cell in a distinct
    # Tesseract line despite their boxes being vertically aligned.  This is a
    # layout reassembly only; no looser alias or amount rule is introduced.
    if not candidates:
        for index, words in _ocr_visual_rows(lines):
            try:
                cells = _ocr_header_cells(words)
            except ParseError:
                continue
            fields = {cell.field for cell in cells if cell.field is not None}
            if not required <= fields:
                continue
            candidates.append((index, cells, len(fields)))
    if not candidates:
        return _select_ocr_cashflow_template_header(
            lines,
            min_confidence_bps=min_confidence_bps,
        )
    candidates.sort(key=lambda item: item[2], reverse=True)
    if len(candidates) > 1 and candidates[0][2] == candidates[1][2]:
        raise ParseError("CASHFLOW_OBSERVATION_HEADER_AMBIGUOUS")
    index, cells, _ = candidates[0]
    if any(cell.field in required and cell.confidence_bps < min_confidence_bps for cell in cells):
        raise ParseError("OCR_LOW_CONFIDENCE")
    return index, cells


_CASHFLOW_TEMPLATE_MAX_ANCHOR_VERTICAL_SPAN = 160
_CASHFLOW_TEMPLATE_EDGE_TOLERANCE = 16
_CASHFLOW_TEMPLATE_MIN_EDGE_OBSERVATIONS = 2
_CASHFLOW_TEMPLATE_MIN_MONEY_COLUMN_GAP = 32


def _cashflow_template_anchor_pair(
    lines: tuple[tuple[_OcrWord, ...], ...],
) -> tuple[int, _OcrHeaderCell, _OcrHeaderCell]:
    """Return the single exact date and category anchor pair for the layout.

    The source's date and category captions are explicit table labels.  They
    are not inferred from row content, and the pair must occur once on one
    page in left-to-right order.  This leaves all source layouts with a
    duplicated or incomplete anchor fail-closed.
    """

    anchors: dict[str, list[tuple[int, int, _OcrHeaderCell]]] = {
        "business_date": [],
        "category": [],
    }
    for line_index, words in enumerate(lines):
        try:
            cells = _ocr_header_cells(words)
        except ParseError:
            continue
        page = words[0].page
        for cell in cells:
            if cell.field in anchors:
                anchors[cell.field].append((page, line_index, cell))

    candidates: list[tuple[int, _OcrHeaderCell, _OcrHeaderCell]] = []
    for date_page, date_index, date_cell in anchors["business_date"]:
        for category_page, category_index, category_cell in anchors["category"]:
            if date_page != category_page or date_cell.right >= category_cell.left:
                continue
            vertical_span = abs(
                (date_cell.top + date_cell.bottom) - (category_cell.top + category_cell.bottom)
            )
            if vertical_span > _CASHFLOW_TEMPLATE_MAX_ANCHOR_VERTICAL_SPAN:
                continue
            candidates.append((min(date_index, category_index), date_cell, category_cell))

    if not candidates:
        raise ParseError("CASHFLOW_OBSERVATION_HEADER_MISSING")
    if len(candidates) != 1:
        raise ParseError("CASHFLOW_OBSERVATION_HEADER_AMBIGUOUS")
    return candidates[0]


def _cashflow_template_money_cells(
    lines: tuple[tuple[_OcrWord, ...], ...],
    *,
    header_index: int,
    date_cell: _OcrHeaderCell,
    category_cell: _OcrHeaderCell,
    min_confidence_bps: int,
) -> tuple[_OcrHeaderCell, ...]:
    """Derive two fixed money columns from repeated right-aligned values.

    This is a bounded layout calibration, not value inference: only
    parseable high-confidence numeric OCR words to the right of the category
    anchor take part, each retained column needs repeated observations, and
    the first two stable columns must be materially separated.  The resulting
    cells are then subject to the existing per-row and footer-total gates.
    """

    header_page = lines[header_index][0].page
    header_bottom = max(date_cell.bottom, category_cell.bottom)
    numeric_words: list[_OcrWord] = []
    for words in lines[header_index + 1:]:
        if words[0].page != header_page or min(word.top for word in words) <= header_bottom:
            continue
        for word in words:
            if word.left + word.width <= category_cell.right or word.confidence_bps < min_confidence_bps:
                continue
            try:
                _cashflow_observation_amount(word.text)
            except ParseError:
                continue
            numeric_words.append(word)

    clusters: list[list[_OcrWord]] = []
    for word in sorted(numeric_words, key=lambda item: (item.left + item.width, item.left, item.top)):
        right = word.left + word.width
        if not clusters or right - (clusters[-1][-1].left + clusters[-1][-1].width) > _CASHFLOW_TEMPLATE_EDGE_TOLERANCE:
            clusters.append([word])
            continue
        clusters[-1].append(word)

    right_edges = [
        sorted(word.left + word.width for word in cluster)[len(cluster) // 2]
        for cluster in clusters
        if len(cluster) >= _CASHFLOW_TEMPLATE_MIN_EDGE_OBSERVATIONS
    ]
    if len(right_edges) < 2:
        raise ParseError("CASHFLOW_OBSERVATION_HEADER_MISSING")
    outflow_right, inflow_right = right_edges[:2]
    if inflow_right - outflow_right < _CASHFLOW_TEMPLATE_MIN_MONEY_COLUMN_GAP:
        raise ParseError("CASHFLOW_OBSERVATION_HEADER_MISSING")
    detail_left = date_cell.right + 1
    detail_right = category_cell.left - 1
    if detail_left >= detail_right:
        raise ParseError("CASHFLOW_OBSERVATION_HEADER_MISSING")

    tail_center = inflow_right + ((inflow_right - outflow_right) // 2)
    return (
        _OcrHeaderCell(
            label="cashflow_template_date",
            field="business_date",
            left=date_cell.left,
            right=date_cell.right,
            top=date_cell.top,
            bottom=date_cell.bottom,
            confidence_bps=date_cell.confidence_bps,
        ),
        _OcrHeaderCell(
            label="cashflow_template_details",
            field=None,
            left=detail_left,
            right=detail_right,
            top=category_cell.top,
            bottom=category_cell.bottom,
            confidence_bps=min_confidence_bps,
        ),
        _OcrHeaderCell(
            label="cashflow_template_category",
            field=None,
            left=category_cell.left,
            right=category_cell.right,
            top=category_cell.top,
            bottom=category_cell.bottom,
            confidence_bps=category_cell.confidence_bps,
        ),
        _OcrHeaderCell(
            label="cashflow_template_outflow",
            field="outflow",
            left=category_cell.right + 1,
            right=outflow_right,
            top=category_cell.top,
            bottom=category_cell.bottom,
            confidence_bps=min_confidence_bps,
        ),
        _OcrHeaderCell(
            label="cashflow_template_inflow",
            field="inflow",
            left=outflow_right + 1,
            right=inflow_right,
            top=category_cell.top,
            bottom=category_cell.bottom,
            confidence_bps=min_confidence_bps,
        ),
        _OcrHeaderCell(
            label="cashflow_template_tail",
            field=None,
            left=tail_center - 1,
            right=tail_center + 1,
            top=category_cell.top,
            bottom=category_cell.bottom,
            confidence_bps=min_confidence_bps,
        ),
    )


def _select_ocr_cashflow_template_header(
    lines: tuple[tuple[_OcrWord, ...], ...],
    *,
    min_confidence_bps: int,
) -> tuple[int, tuple[_OcrHeaderCell, ...]]:
    """Build the verified fixed-layout profile when header aliases are split."""

    header_index, date_cell, category_cell = _cashflow_template_anchor_pair(lines)
    if date_cell.confidence_bps < min_confidence_bps or category_cell.confidence_bps < min_confidence_bps:
        raise ParseError("OCR_LOW_CONFIDENCE")
    return (
        header_index,
        _cashflow_template_money_cells(
            lines,
            header_index=header_index,
            date_cell=date_cell,
            category_cell=category_cell,
            min_confidence_bps=min_confidence_bps,
        ),
    )


def _cashflow_observation_amount(value: object) -> int:
    text = str(value or "").strip()
    if not text:
        return 0
    try:
        amount = parse_amount_to_fen(text)
    except ContractError as exc:
        raise ParseError("CASHFLOW_OBSERVATION_AMOUNT_INVALID") from exc
    if amount < 0:
        raise ParseError("CASHFLOW_OBSERVATION_AMOUNT_NEGATIVE")
    return amount


_CASHFLOW_SHORT_DATE = re.compile(r"^(?P<month>0?[1-9]|1[0-2])月(?P<day>0?[1-9]|[12]\d|3[01])日?$")


def _cashflow_observation_date(value: object, *, received_at: datetime) -> date:
    """Resolve a screenshot's month/day cell against its source-message date.

    A source image regularly renders ``08月07日`` rather than a full year.
    The received timestamp supplies only the calendar year boundary; the
    parser rejects dates more than a year away instead of silently guessing an
    arbitrary period.
    """

    text = str(value or "").strip().replace(" ", "")
    if not text:
        raise ParseError("CASHFLOW_OBSERVATION_DATE_MISSING")
    try:
        parsed = _parse_date(text)
    except ParseError:
        matched = _CASHFLOW_SHORT_DATE.fullmatch(text)
        if matched is None:
            raise ParseError("CASHFLOW_OBSERVATION_DATE_INVALID")
        reference = received_at.date()
        try:
            parsed = date(reference.year, int(matched.group("month")), int(matched.group("day")))
        except ValueError as exc:
            raise ParseError("CASHFLOW_OBSERVATION_DATE_INVALID") from exc
        # A December report received in January belongs to the immediately
        # preceding year.  No other year inference is allowed.
        if (parsed - reference).days > 31:
            try:
                parsed = date(parsed.year - 1, parsed.month, parsed.day)
            except ValueError as exc:
                raise ParseError("CASHFLOW_OBSERVATION_DATE_INVALID") from exc
    reference = received_at.date()
    if abs((reference - parsed).days) > 366:
        raise ParseError("CASHFLOW_OBSERVATION_DATE_OUT_OF_RANGE")
    return parsed


def _ocr_cashflow_observation_totals(
    lines: tuple[tuple[_OcrWord, ...], ...],
    *,
    header_index: int,
    cells: tuple[_OcrHeaderCell, ...],
    received_at: datetime,
    min_confidence_bps: int,
) -> tuple[date, int, int]:
    """Return a zero-leak, footer-reconciled daily receipt/payment total.

    Individual receipt/payment rows are read only long enough to recompute the
    visible ``合计`` footer.  No row description, bank, counterparty or amount
    text is returned or persisted by this function.
    """

    header_page = lines[header_index][0].page
    header_bottom = max(cell.bottom for cell in cells)
    field_by_label = {cell.label: cell.field for cell in cells}
    row_inflow = 0
    row_outflow = 0
    business_dates: set[date] = set()
    total: tuple[int, int] | None = None
    row_count = 0
    for words in lines[header_index + 1:]:
        if words[0].page != header_page or min(word.top for word in words) <= header_bottom:
            continue
        by_index: dict[int, list[_OcrWord]] = {index: [] for index in range(len(cells))}
        for word in words:
            by_index[_ocr_cell_index(word, cells)].append(word)
        row: dict[str, str] = {}
        confidence: dict[str, int | None] = {}
        for index, cell in enumerate(cells):
            values = sorted(by_index[index], key=lambda word: (word.left, word.top, word.text))
            row[cell.label] = "".join(word.text for word in values)
            confidence[cell.label] = min((word.confidence_bps for word in values), default=None)
        mapped = {field: row[label] for label, field in field_by_label.items() if field is not None}
        inflow_text = mapped.get("inflow", "")
        outflow_text = mapped.get("outflow", "")
        row_text = normalize_header("".join(row.values()))
        is_total = "合计" in row_text
        if not inflow_text and not outflow_text:
            # Wrapped descriptions have neither money direction.  They cannot
            # change a footer total and are intentionally not treated as rows.
            if is_total:
                raise ParseError("CASHFLOW_OBSERVATION_TOTAL_MISSING")
            continue
        for label, field in field_by_label.items():
            if field in {"business_date", "inflow", "outflow", "bank"} and row[label] and (
                confidence[label] is None or confidence[label] < min_confidence_bps
            ):
                raise ParseError("OCR_LOW_CONFIDENCE")
        inflow = _cashflow_observation_amount(inflow_text)
        outflow = _cashflow_observation_amount(outflow_text)
        if inflow == 0 and outflow == 0:
            raise ParseError("CASHFLOW_OBSERVATION_ZERO_ROW")
        if is_total:
            if total is not None:
                raise ParseError("CASHFLOW_OBSERVATION_TOTAL_AMBIGUOUS")
            total = (inflow, outflow)
            continue
        business_dates.add(_cashflow_observation_date(mapped.get("business_date"), received_at=received_at))
        row_inflow += inflow
        row_outflow += outflow
        row_count += 1
    if row_count == 0:
        raise ParseError("CASHFLOW_OBSERVATION_ROWS_EMPTY")
    if len(business_dates) != 1:
        raise ParseError("CASHFLOW_OBSERVATION_DATE_AMBIGUOUS")
    if total is None:
        raise ParseError("CASHFLOW_OBSERVATION_TOTAL_MISSING")
    if total != (row_inflow, row_outflow):
        raise ParseError("CASHFLOW_OBSERVATION_TOTAL_MISMATCH")
    return next(iter(business_dates)), row_inflow, row_outflow


def parse_cashflow_observation(
    *,
    family: str,
    filename: str,
    payload: bytes,
    source: SourceRef,
    received_at: datetime,
    mime: str | None = None,
    min_confidence_bps: int = OCR_MIN_CONFIDENCE_BPS,
    runner: Callable[..., Any] = subprocess.run,
) -> CashflowObservation:
    """Parse one footer-reconciled receipt/payment screenshot for the UI only.

    It requires an explicit flow document family and does not return account,
    counterparty, bank, or individual-row fields.  Calling code must keep the
    result out of formal account/transaction reconciliation and publication.
    """

    if family not in TRANSACTION_FAMILIES:
        raise ParseError("CASHFLOW_OBSERVATION_FAMILY_UNSUPPORTED")
    if not isinstance(received_at, datetime):
        raise ParseError("CASHFLOW_OBSERVATION_RECEIVED_AT_INVALID")
    if not payload:
        raise ParseError("CORRUPT_ATTACHMENT")
    _validate_source(source, payload)
    threshold = _validate_ocr_min_confidence(min_confidence_bps)
    evidence = replace(
        inspect_ocr_attachment_format(filename=filename, payload=payload, mime=mime),
        parser_version=CASHFLOW_OBSERVATION_PARSER_VERSION,
    )
    words = _parse_tesseract_tsv(_ocr_tsv(payload=payload, evidence=evidence, runner=runner))
    lines = _ocr_lines(words)
    header_index, cells = _select_ocr_cashflow_header(lines, min_confidence_bps=threshold)
    business_date, inflow_fen, outflow_fen = _ocr_cashflow_observation_totals(
        lines,
        header_index=header_index,
        cells=cells,
        received_at=received_at,
        min_confidence_bps=threshold,
    )
    return CashflowObservation(
        business_date=business_date,
        inflow_fen=inflow_fen,
        outflow_fen=outflow_fen,
        source=source,
        parser_evidence=evidence,
        layout_fingerprint=_ocr_layout_fingerprint(
            family="cashflow_observation",
            evidence=evidence,
            cells=cells,
        ),
    )


def _generic_ocr_unresolved_code(failures: Iterable[ParseError]) -> str:
    """Return a conservative values-free reason for zero generic candidates.

    The two strict schemas are still both required to fail.  A more specific
    code is returned only if every failed candidate stopped in the same broad
    OCR phase; mixed or unknown failures retain the original fail-closed code.
    """

    codes = {str(failure).split(":", 1)[0] for failure in failures}
    if codes and codes <= _GENERIC_OCR_HEADER_PHASE_CODES:
        return "OCR_GENERIC_HEADER_SCHEMA_MISSING"
    if codes and codes <= _GENERIC_OCR_ROW_PHASE_CODES:
        return "OCR_GENERIC_ROW_SCHEMA_MISSING"
    if codes and codes <= _GENERIC_OCR_CONFIDENCE_PHASE_CODES:
        return "OCR_GENERIC_CONFIDENCE_BLOCKED"
    return "OCR_GENERIC_FAMILY_UNRESOLVED"


def parse_ocr_attachment(
    *,
    family: str,
    filename: str,
    payload: bytes,
    source: SourceRef,
    mime: str | None = None,
    min_confidence_bps: int = OCR_MIN_CONFIDENCE_BPS,
    runner: Callable[..., Any] = subprocess.run,
) -> OcrParsedAttachment:
    """Open one image/scanned-PDF through a deterministic offline OCR table path.

    This function proves only a strict, in-memory parser-open.  The runtime
    adds the separate two-business-day layout calibration gate before it can
    treat the resulting facts as a supported source for reconciliation.
    """

    if family not in TRANSACTION_FAMILIES | {ACCOUNT_FAMILY}:
        raise ParseError("DOCUMENT_FAMILY_UNSUPPORTED")
    if not payload:
        raise ParseError("CORRUPT_ATTACHMENT")
    _validate_source(source, payload)
    threshold = _validate_ocr_min_confidence(min_confidence_bps)
    evidence = inspect_ocr_attachment_format(filename=filename, payload=payload, mime=mime)
    words = _parse_tesseract_tsv(_ocr_tsv(payload=payload, evidence=evidence, runner=runner))
    lines = _ocr_lines(words)
    # ``资金明细`` is an allowed transaction family, but it is also the one
    # generic source label used by historical image messages.  Do not let that
    # label force an account-looking table through the transaction schema.  We
    # accept the image only when the already-produced OCR table validates under
    # exactly one of the two complete fact schemas; zero or two matches remain
    # fail-closed.  OCR itself executes once, so this adds no second raw read
    # or a heuristic retry path.
    candidate_families = (ACCOUNT_FAMILY, "资金明细") if family == "资金明细" else (family,)
    candidates: list[OcrParsedAttachment] = []
    failures: list[ParseError] = []
    for candidate_family in candidate_families:
        try:
            candidates.append(_parse_ocr_table(
                family=candidate_family,
                filename=filename,
                source=source,
                evidence=evidence,
                lines=lines,
                min_confidence_bps=threshold,
            ))
        except ParseError as exc:
            failures.append(exc)

    if len(candidates) == 1:
        return candidates[0]
    if family == "资金明细":
        if len(candidates) > 1:
            raise ParseError("OCR_GENERIC_FAMILY_AMBIGUOUS")
        raise ParseError(_generic_ocr_unresolved_code(failures))
    # A non-generic source family has exactly one candidate, so preserving the
    # original strict parser code is both more precise and backward compatible.
    raise failures[0]


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


def _facts_from_rows(
    *,
    family: str,
    filename: str,
    source: SourceRef,
    rows: list[dict[str, object]],
    parser_evidence: ParserEvidence,
) -> ParsedFacts:
    """Build one fact family from rows already opened by a strict parser."""

    if family not in TRANSACTION_FAMILIES | {ACCOUNT_FAMILY}:
        raise ParseError("DOCUMENT_FAMILY_UNSUPPORTED")
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

    # The sealed transaction schema requires a company/account alias but makes
    # bank_id optional and does not require a source transaction identifier.
    # Retain a provided identifier when present; otherwise the stable row
    # position within this immutable attachment is a fact-local identity used
    # exclusively for deduplication.
    _required(mapped, ("company", "account"))
    has_flow_columns = "inflow" in mapped or "outflow" in mapped
    has_amount_direction = {"amount", "direction"} <= set(mapped)
    # These are two alternative financial encodings.  Without a frozen real
    # template proving their relationship, preferring one and ignoring the
    # other could silently publish a different amount than the attachment
    # states.  Treat coexistence as ambiguity rather than an implicit choice.
    if has_flow_columns and has_amount_direction:
        raise ParseError("TRANSACTION_AMOUNT_MAPPING_AMBIGUOUS")
    if not has_flow_columns and not has_amount_direction:
        raise ParseError("TRANSACTION_AMOUNT_MAPPING_MISSING")
    transactions: list[Transaction] = []
    seen_transactions: set[tuple[date, str, str | None, str, str]] = set()
    for row_index, row in enumerate(rows, start=1):
        company = _required_text(row, mapped["company"], "TRANSACTION_COMPANY_MISSING")
        bank = (
            _required_text(row, mapped["bank"], "TRANSACTION_BANK_MISSING")
            if "bank" in mapped and not _is_blank(row.get(mapped["bank"]))
            else None
        )
        account = _required_identifier(
            row,
            mapped["account"],
            "TRANSACTION_ACCOUNT_MISSING",
            "TRANSACTION_ACCOUNT_NON_TEXT",
        )
        transaction_id = (
            _required_identifier(
                row,
                mapped["transaction_id"],
                "TRANSACTION_ID_MISSING",
                "TRANSACTION_ID_NON_TEXT",
            )
            if "transaction_id" in mapped and not _is_blank(row.get(mapped["transaction_id"]))
            else f"source-row-{row_index}"
        )
        key = (business_date, company, bank, account, transaction_id)
        if key in seen_transactions:
            raise ParseError("TRANSACTION_DUPLICATE")
        seen_transactions.add(key)
        if has_flow_columns:
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


def parse_attachment(
    *,
    family: str,
    filename: str,
    payload: bytes,
    source: SourceRef,
    mime: str | None = None,
) -> ParsedFacts:
    """Open and parse one structured source file into exactly one fact family.

    Images and scanned PDFs deliberately use :func:`parse_ocr_attachment`
    instead.  Keeping that route explicit prevents an unsupported binary from
    silently becoming a financial fact merely because its filename resembles a
    supported spreadsheet.
    """

    if family not in TRANSACTION_FAMILIES | {ACCOUNT_FAMILY}:
        raise ParseError("DOCUMENT_FAMILY_UNSUPPORTED")
    if not payload:
        raise ParseError("CORRUPT_ATTACHMENT")
    _validate_source(source, payload)
    rows, parser_evidence = _rows_from_bytes(filename, payload, mime)
    return _facts_from_rows(
        family=family,
        filename=filename,
        source=source,
        rows=rows,
        parser_evidence=parser_evidence,
    )
