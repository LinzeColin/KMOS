"""Bounded file classification executed only by the scanner service.

The public application imports the authenticated protocol client, never this
module.  All format parsing therefore stays outside the web process and outside
the database/object credential plane.  Unknown or high-risk formats are
accepted only as attachments; this policy never creates a preview.
"""

from __future__ import annotations

import io
import json
import re
import stat
import unicodedata
import zipfile
import zlib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from .file_security_protocol import (
    FILE_SECURITY_POLICY_VERSION,
    SCANNER_ENGINE,
    SCANNER_VERSION,
)

POLICY_VERSION = FILE_SECURITY_POLICY_VERSION
ENGINE_NAME = SCANNER_ENGINE
ENGINE_VERSION = SCANNER_VERSION
MAX_SCAN_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 1024
MAX_ARCHIVE_EXPANDED_BYTES = 128 * 1024 * 1024
MAX_ARCHIVE_ENTRY_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_RATIO = 100
MAX_ARCHIVE_NESTED = 0
MAX_RESULT_FLAGS = 16

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MEDIA_TYPE_RE = re.compile(
    r"^[a-z0-9][a-z0-9!#$&^_.+-]{0,126}/"
    r"[a-z0-9][a-z0-9!#$&^_.+-]{0,126}$"
)
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")
_DANGEROUS_EXTENSIONS = frozenset(
    {
        ".apk",
        ".app",
        ".bat",
        ".cmd",
        ".com",
        ".cpl",
        ".dll",
        ".dmg",
        ".docm",
        ".exe",
        ".hta",
        ".html",
        ".htm",
        ".jar",
        ".js",
        ".jse",
        ".lnk",
        ".msi",
        ".msp",
        ".pif",
        ".ps1",
        ".pptm",
        ".scr",
        ".sh",
        ".svg",
        ".vbe",
        ".vbs",
        ".wasm",
        ".xlsm",
    }
)
_ARCHIVE_EXTENSIONS = frozenset(
    {".7z", ".bz2", ".gz", ".rar", ".tar", ".tgz", ".xz", ".zip"}
)
_GENERIC_MEDIA_TYPES = frozenset(
    {"application/octet-stream", "binary/octet-stream"}
)
_MAGIC_MEDIA_TYPES = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "zip": "application/zip",
    "ole": "application/x-ole-storage",
    "pe": "application/vnd.microsoft.portable-executable",
    "elf": "application/x-elf",
    "wasm": "application/wasm",
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "mp4": "video/mp4",
    "gzip": "application/gzip",
    "7z": "application/x-7z-compressed",
    "rar": "application/vnd.rar",
    "html": "text/html",
    "svg": "image/svg+xml",
    "script": "text/x-script",
    "json": "application/json",
    "text": "text/plain",
    "empty": "application/x-empty",
    "unknown": "application/octet-stream",
}
_EXTENSION_MEDIA_TYPES = {
    ".csv": frozenset({"text/csv", "text/plain"}),
    ".gif": frozenset({"image/gif"}),
    ".jpeg": frozenset({"image/jpeg"}),
    ".jpg": frozenset({"image/jpeg"}),
    ".json": frozenset({"application/json", "text/json", "text/plain"}),
    ".md": frozenset({"text/markdown", "text/plain"}),
    ".mp3": frozenset({"audio/mpeg"}),
    ".mp4": frozenset({"video/mp4"}),
    ".pdf": frozenset({"application/pdf"}),
    ".png": frozenset({"image/png"}),
    ".txt": frozenset({"text/plain"}),
    ".wav": frozenset({"audio/wav", "audio/x-wav"}),
    ".zip": frozenset({"application/zip", "application/x-zip-compressed"}),
}
_SAFE_CLEAN_KINDS = frozenset(
    {"gif", "jpeg", "json", "mp3", "mp4", "png", "text", "wav"}
)
_ACTIVE_KINDS = frozenset(
    {"elf", "html", "ole", "pe", "script", "svg", "wasm"}
)
_OFFICE_MACRO_NAMES = (
    "vbaproject.bin",
    "vbaprojectsignature.bin",
    "macros/",
)

# Keep the harmless EICAR canary split so source checkouts are not themselves
# mistaken for an uploaded test file by endpoint scanners.
_EICAR = (
    b"X5O!P%@AP[4"
    + bytes((92,))
    + b"PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
)


class FileSecurityPolicyError(RuntimeError):
    """Static scanner-policy error suitable for a fail-closed response."""


@dataclass(frozen=True)
class PolicyDecision:
    verdict: str
    reason_code: str
    detected_media_type: str
    risk_flags: tuple[str, ...]
    archive_entries: int = 0
    expanded_bytes: int = 0


def _normalized_filename(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value).strip()
    if (
        not normalized
        or normalized in {".", ".."}
        or normalized.startswith(("-", "."))
        or "/" in normalized
        or "\\" in normalized
        or "\x00" in normalized
        or ".." in normalized
        or len(normalized.encode("utf-8")) > 255
        or any(unicodedata.category(char).startswith("C") for char in normalized)
    ):
        raise FileSecurityPolicyError("security_filename_invalid")
    return normalized


def _normalized_media_type(value: str) -> str:
    normalized = value.split(";", 1)[0].strip().lower()
    if not _MEDIA_TYPE_RE.fullmatch(normalized):
        return "application/octet-stream"
    return normalized


def _read_prefix(path: Path, limit: int = 8192) -> bytes:
    try:
        with path.open("rb") as source:
            return source.read(limit)
    except OSError as exc:
        raise FileSecurityPolicyError("security_source_unavailable") from exc


def _looks_like_text(prefix: bytes) -> bool:
    if not prefix:
        return False
    if b"\x00" in prefix:
        return False
    try:
        decoded = prefix.decode("utf-8")
    except UnicodeDecodeError:
        return False
    controls = sum(
        1
        for char in decoded
        if unicodedata.category(char).startswith("C")
        and char not in {"\n", "\r", "\t"}
    )
    return controls / max(1, len(decoded)) < 0.01


def _magic_kind(prefix: bytes) -> str:
    if not prefix:
        return "empty"
    lowered = prefix.lstrip().lower()
    if prefix.startswith(b"%PDF-"):
        return "pdf"
    if prefix.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if prefix.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if prefix.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if prefix.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        return "zip"
    if prefix.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "ole"
    if prefix.startswith(b"MZ"):
        return "pe"
    if prefix.startswith(b"\x7fELF"):
        return "elf"
    if prefix.startswith(b"\x00asm"):
        return "wasm"
    if prefix.startswith(b"ID3") or (
        len(prefix) >= 2
        and prefix[0] == 0xFF
        and prefix[1] & 0xE0 == 0xE0
    ):
        return "mp3"
    if prefix.startswith(b"RIFF") and prefix[8:12] == b"WAVE":
        return "wav"
    if len(prefix) >= 12 and prefix[4:8] == b"ftyp":
        return "mp4"
    if prefix.startswith(b"\x1f\x8b"):
        return "gzip"
    if prefix.startswith(b"7z\xbc\xaf\x27\x1c"):
        return "7z"
    if prefix.startswith((b"Rar!\x1a\x07\x00", b"Rar!\x1a\x07\x01\x00")):
        return "rar"
    if lowered.startswith((b"<!doctype html", b"<html", b"<script")):
        return "html"
    if lowered.startswith(b"<svg"):
        return "svg"
    if prefix.startswith(b"#!"):
        return "script"
    if _looks_like_text(prefix):
        return "text"
    return "unknown"


def _stream_contains(
    source: BinaryIO,
    needle: bytes,
    *,
    limit: int,
) -> bool:
    tail = b""
    consumed = 0
    while True:
        block = source.read(min(1024 * 1024, limit - consumed + 1))
        if not block:
            return False
        consumed += len(block)
        if consumed > limit:
            raise FileSecurityPolicyError("security_scan_limit_exceeded")
        candidate = tail + block
        if needle in candidate:
            return True
        tail = candidate[-max(0, len(needle) - 1) :]


def _file_contains(path: Path, needle: bytes) -> bool:
    try:
        with path.open("rb") as source:
            return _stream_contains(source, needle, limit=MAX_SCAN_BYTES)
    except OSError as exc:
        raise FileSecurityPolicyError("security_source_unavailable") from exc


def _validate_png(path: Path, size_bytes: int) -> bool:
    if size_bytes < 45:
        return False
    try:
        with path.open("rb") as source:
            if source.read(8) != b"\x89PNG\r\n\x1a\n":
                return False
            chunks = 0
            saw_header = False
            while source.tell() < size_bytes:
                header = source.read(8)
                if len(header) != 8:
                    return False
                length = int.from_bytes(header[:4], "big")
                kind = header[4:]
                if length > size_bytes or source.tell() + length + 4 > size_bytes:
                    return False
                payload = source.read(length)
                checksum = source.read(4)
                if len(payload) != length or len(checksum) != 4:
                    return False
                if (
                    zlib.crc32(kind + payload) & 0xFFFFFFFF
                    != int.from_bytes(checksum, "big")
                ):
                    return False
                chunks += 1
                if chunks > 4096:
                    return False
                if chunks == 1:
                    saw_header = kind == b"IHDR" and length == 13
                if kind == b"IEND":
                    return (
                        saw_header
                        and length == 0
                        and source.tell() == size_bytes
                    )
    except OSError:
        return False
    return False


def _validate_json(path: Path) -> bool:
    try:
        with path.open("r", encoding="utf-8") as source:
            json.load(source)
        return True
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return False


def _validate_structure(path: Path, kind: str, size_bytes: int) -> bool:
    try:
        if kind == "png":
            return _validate_png(path, size_bytes)
        if kind == "jpeg":
            with path.open("rb") as source:
                return (
                    size_bytes >= 4
                    and source.read(3) == b"\xff\xd8\xff"
                    and _read_tail(source, size_bytes, 2) == b"\xff\xd9"
                )
        if kind == "gif":
            with path.open("rb") as source:
                return (
                    size_bytes >= 14
                    and source.read(6) in {b"GIF87a", b"GIF89a"}
                    and _read_tail(source, size_bytes, 1) == b";"
                )
        if kind == "pdf":
            with path.open("rb") as source:
                tail = _read_tail(source, size_bytes, min(size_bytes, 2048))
                return size_bytes >= 8 and b"%%EOF" in tail
        if kind == "mp4":
            with path.open("rb") as source:
                header = source.read(12)
                box_size = int.from_bytes(header[:4], "big")
                return (
                    len(header) == 12
                    and header[4:8] == b"ftyp"
                    and 8 <= box_size <= size_bytes
                )
        if kind == "wav":
            with path.open("rb") as source:
                header = source.read(12)
                declared = int.from_bytes(header[4:8], "little") + 8
                return (
                    len(header) == 12
                    and header[:4] == b"RIFF"
                    and header[8:] == b"WAVE"
                    and 12 <= declared <= size_bytes
                )
        if kind == "mp3":
            with path.open("rb") as source:
                header = source.read(10)
                if header.startswith(b"ID3") and len(header) == 10:
                    if any(byte & 0x80 for byte in header[6:10]):
                        return False
                    tag_size = (
                        (header[6] << 21)
                        | (header[7] << 14)
                        | (header[8] << 7)
                        | header[9]
                    )
                    return 10 + tag_size <= size_bytes
                return len(header) >= 2 and header[0] == 0xFF
        if kind == "json":
            return _validate_json(path)
    except OSError:
        return False
    return True


def _read_tail(source: BinaryIO, size_bytes: int, length: int) -> bytes:
    source.seek(max(0, size_bytes - length), io.SEEK_SET)
    return source.read(length)


def _archive_name_is_unsafe(value: str) -> bool:
    if (
        not value
        or "\x00" in value
        or "\\" in value
        or value.startswith(("/", "~"))
        or _WINDOWS_DRIVE_RE.match(value)
    ):
        return True
    parts = PurePosixPath(value).parts
    return any(part in {"", ".", ".."} for part in parts)


def _zip_entry_is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)


def _inspect_zip(path: Path) -> PolicyDecision:
    entry_count = 0
    total_expanded = 0
    compressed_total = 0
    macro = False
    nested = False
    encrypted = False
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            entry_count = len(entries)
            if entry_count > MAX_ARCHIVE_ENTRIES:
                return _rejected(
                    "security_archive_entry_limit",
                    "application/zip",
                    entry_count,
                    0,
                )
            for info in entries:
                if _archive_name_is_unsafe(info.filename):
                    return _rejected(
                        "security_archive_path_traversal",
                        "application/zip",
                        entry_count,
                        total_expanded,
                    )
                if _zip_entry_is_symlink(info):
                    return _rejected(
                        "security_archive_symlink",
                        "application/zip",
                        entry_count,
                        total_expanded,
                    )
                if info.file_size > MAX_ARCHIVE_ENTRY_BYTES:
                    return _rejected(
                        "security_archive_bomb",
                        "application/zip",
                        entry_count,
                        total_expanded,
                    )
                total_expanded += int(info.file_size)
                compressed_total += int(info.compress_size)
                if total_expanded > MAX_ARCHIVE_EXPANDED_BYTES:
                    return _rejected(
                        "security_archive_bomb",
                        "application/zip",
                        entry_count,
                        total_expanded,
                    )
                if info.file_size and (
                    info.compress_size == 0
                    or info.file_size
                    > max(1, info.compress_size) * MAX_ARCHIVE_RATIO
                ):
                    return _rejected(
                        "security_archive_bomb",
                        "application/zip",
                        entry_count,
                        total_expanded,
                    )
                lowered = info.filename.lower()
                macro = macro or any(
                    token in lowered for token in _OFFICE_MACRO_NAMES
                )
                nested = nested or Path(lowered).suffix in _ARCHIVE_EXTENSIONS
                encrypted = encrypted or bool(info.flag_bits & 0x1)
            if total_expanded and (
                compressed_total == 0
                or total_expanded
                > max(1, compressed_total) * MAX_ARCHIVE_RATIO
            ):
                return _rejected(
                    "security_archive_bomb",
                    "application/zip",
                    entry_count,
                    total_expanded,
                )
            if encrypted:
                return _attachment(
                    "security_archive_encrypted",
                    "application/zip",
                    ("encrypted_archive",),
                    entry_count,
                    total_expanded,
                )
            for info in entries:
                if info.is_dir():
                    continue
                with archive.open(info, "r") as source:
                    if _stream_contains(
                        source,
                        _EICAR,
                        limit=MAX_ARCHIVE_ENTRY_BYTES,
                    ):
                        return _rejected(
                            "security_malware_eicar",
                            "application/zip",
                            entry_count,
                            total_expanded,
                        )
            if macro:
                return _attachment(
                    "security_office_macro",
                    "application/zip",
                    ("office_macro",),
                    entry_count,
                    total_expanded,
                )
            if nested and MAX_ARCHIVE_NESTED == 0:
                return _attachment(
                    "security_nested_archive",
                    "application/zip",
                    ("nested_archive",),
                    entry_count,
                    total_expanded,
                )
            return _attachment(
                "security_archive_attachment_only",
                "application/zip",
                ("archive_no_preview",),
                entry_count,
                total_expanded,
            )
    except (
        OSError,
        RuntimeError,
        EOFError,
        zipfile.BadZipFile,
        zlib.error,
    ):
        return _rejected(
            "security_archive_malformed",
            "application/zip",
            entry_count,
            total_expanded,
        )


def _suffixes(filename: str) -> tuple[str, ...]:
    return tuple(suffix.lower() for suffix in Path(filename).suffixes)


def _has_dangerous_double_extension(filename: str) -> bool:
    suffixes = _suffixes(filename)
    return len(suffixes) > 1 and any(
        suffix in _DANGEROUS_EXTENSIONS for suffix in suffixes[:-1]
    )


def _media_mismatch(
    *,
    suffix: str,
    reported: str,
    detected: str,
) -> bool:
    if reported not in _GENERIC_MEDIA_TYPES and reported != detected:
        aliases = _EXTENSION_MEDIA_TYPES.get(suffix, frozenset())
        if not (reported in aliases and detected in aliases):
            return True
    allowed = _EXTENSION_MEDIA_TYPES.get(suffix)
    return bool(allowed and detected not in allowed)


def _bounded_flags(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))[:MAX_RESULT_FLAGS]


def _attachment(
    reason: str,
    media_type: str,
    flags: Iterable[str],
    entries: int = 0,
    expanded: int = 0,
) -> PolicyDecision:
    return PolicyDecision(
        verdict="attachment_only",
        reason_code=reason,
        detected_media_type=media_type,
        risk_flags=_bounded_flags(flags),
        archive_entries=entries,
        expanded_bytes=expanded,
    )


def _rejected(
    reason: str,
    media_type: str,
    entries: int = 0,
    expanded: int = 0,
) -> PolicyDecision:
    return PolicyDecision(
        verdict="rejected",
        reason_code=reason,
        detected_media_type=media_type,
        risk_flags=(reason,),
        archive_entries=entries,
        expanded_bytes=expanded,
    )


def inspect_file(
    path: Path,
    *,
    original_name: str,
    reported_media_type: str,
    expected_size: int,
    expected_sha256: str,
) -> PolicyDecision:
    """Inspect one private scanner-local file under explicit resource bounds."""

    try:
        filename = _normalized_filename(original_name)
    except FileSecurityPolicyError as exc:
        return _rejected(str(exc), "application/octet-stream")
    media_type = _normalized_media_type(reported_media_type)
    if expected_size < 0 or expected_size > MAX_SCAN_BYTES:
        return _rejected("security_scan_limit_exceeded", media_type)
    if _SHA256_RE.fullmatch(expected_sha256) is None:
        return _rejected("security_checksum_invalid", media_type)
    try:
        details = path.lstat()
    except OSError:
        return _rejected("security_source_unavailable", media_type)
    if path.is_symlink() or not stat.S_ISREG(details.st_mode):
        return _rejected("security_source_invalid", media_type)
    if int(details.st_size) != expected_size:
        return _rejected("security_size_mismatch", media_type)
    if _file_contains(path, _EICAR):
        return _rejected("security_malware_eicar", media_type)

    prefix = _read_prefix(path)
    kind = _magic_kind(prefix)
    suffixes = _suffixes(filename)
    suffix = suffixes[-1] if suffixes else ""
    if kind == "text" and (
        suffix == ".json"
        or media_type in {"application/json", "text/json"}
    ):
        kind = "json"
    detected = _MAGIC_MEDIA_TYPES[kind]

    if kind == "zip":
        archive = _inspect_zip(path)
        archive_flags = list(archive.risk_flags)
        if _has_dangerous_double_extension(filename):
            archive_flags.append("dangerous_double_extension")
        if _media_mismatch(
            suffix=suffix,
            reported=media_type,
            detected=archive.detected_media_type,
        ):
            archive_flags.append("mime_magic_mismatch")
        if archive.verdict == "rejected":
            return archive
        if "dangerous_double_extension" in archive_flags:
            reason = "security_dangerous_double_extension"
        elif "mime_magic_mismatch" in archive_flags:
            reason = "security_mime_magic_mismatch"
        else:
            reason = archive.reason_code
        return _attachment(
            reason,
            archive.detected_media_type,
            archive_flags,
            archive.archive_entries,
            archive.expanded_bytes,
        )

    if kind in {
        "png",
        "jpeg",
        "gif",
        "pdf",
        "mp3",
        "mp4",
        "wav",
        "json",
    } and not _validate_structure(path, kind, expected_size):
        return _rejected("security_media_malformed", detected)

    flags: list[str] = []
    if _has_dangerous_double_extension(filename):
        flags.append("dangerous_double_extension")
    if suffix in _DANGEROUS_EXTENSIONS:
        flags.append("dangerous_extension")
    if kind in _ACTIVE_KINDS:
        flags.append("active_content")
    if kind in {"gzip", "7z", "rar"}:
        flags.append("uninspected_archive")
    if kind in {"empty", "unknown"}:
        flags.append("unknown_format")
    if kind == "pdf":
        flags.append("format_requires_safe_processor")
    if _media_mismatch(
        suffix=suffix,
        reported=media_type,
        detected=detected,
    ):
        flags.append("mime_magic_mismatch")

    if flags:
        reason_by_flag = {
            "dangerous_double_extension": "security_dangerous_double_extension",
            "dangerous_extension": "security_dangerous_extension",
            "active_content": "security_active_content",
            "uninspected_archive": "security_uninspected_archive",
            "unknown_format": "security_unknown_format",
            "format_requires_safe_processor": (
                "security_format_attachment_only"
            ),
            "mime_magic_mismatch": "security_mime_magic_mismatch",
        }
        return _attachment(reason_by_flag[flags[0]], detected, flags)
    if kind in _SAFE_CLEAN_KINDS:
        return PolicyDecision(
            verdict="clean",
            reason_code="security_scan_clean",
            detected_media_type=detected,
            risk_flags=(),
        )
    return _attachment(
        "security_unknown_format",
        detected,
        ("unknown_format",),
    )
