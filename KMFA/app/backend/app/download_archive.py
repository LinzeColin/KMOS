"""Bounded, deterministic ZIP streaming for S07/P7.2 batch downloads.

The archive body is never assembled in memory or in a second archive file.
Only bounded central-directory metadata is retained while source objects are
materialized and streamed one at a time.  ZIP_STORED plus data descriptors
keeps CPU and memory predictable and lets client disconnects close the active
source immediately.
"""

from __future__ import annotations

import binascii
import hashlib
import json
import re
import struct
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Iterator, Protocol

import anyio

MAX_BATCH_DOWNLOAD_ASSETS = 500
MAX_ZIP32_BYTES = (1 << 32) - 1
ZIP_STREAM_CHUNK_BYTES = 64 * 1024
MANIFEST_PATH = "manifest.json"
MANIFEST_FORMAT = "kmfa-download-manifest"
MANIFEST_VERSION = 1
ARCHIVE_FORMAT = "zip-stored-stream-v1"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_LOCAL_FILE_HEADER = 0x04034B50
_DATA_DESCRIPTOR = 0x08074B50
_CENTRAL_DIRECTORY_HEADER = 0x02014B50
_END_OF_CENTRAL_DIRECTORY = 0x06054B50
_VERSION_NEEDED = 20
_VERSION_MADE_BY_UNIX = (3 << 8) | 20
_UTF8_DATA_DESCRIPTOR_FLAGS = (1 << 11) | (1 << 3)
_ZIP_STORED = 0
_DOS_TIME = 0
_DOS_DATE = (1 << 5) | 1  # 1980-01-01, the earliest ZIP timestamp.
_REGULAR_FILE_0600 = (0o100600 & 0xFFFF) << 16
_END = object()


class BatchArchiveError(RuntimeError):
    """Safe, non-sensitive batch archive failure."""


class MaterializedSource(Protocol):
    path: Path
    temporary: bool


@dataclass(frozen=True)
class BatchArchiveEntry:
    archive_path: str
    size_bytes: int
    sha256: str
    manifest_record: dict[str, Any]
    storage_backend: str
    storage_key: str


@dataclass(frozen=True)
class PreparedBatchArchive:
    entries: tuple[BatchArchiveEntry, ...]
    manifest_bytes: bytes
    manifest_sha256: str
    total_source_bytes: int
    content_length: int


@dataclass(frozen=True)
class _CentralDirectoryEntry:
    name: bytes
    crc32: int
    size_bytes: int
    local_header_offset: int


def archive_path_for(index: int, original_name: str) -> str:
    """Return a non-overlapping, zip-slip-safe path for one selected asset."""

    if index < 1 or index > MAX_BATCH_DOWNLOAD_ASSETS:
        raise BatchArchiveError("batch_asset_count_invalid")
    normalized = unicodedata.normalize("NFC", str(original_name)).strip()
    if (
        not normalized
        or normalized in {".", ".."}
        or "/" in normalized
        or "\\" in normalized
        or len(normalized.encode("utf-8")) > 255
        or any(
            unicodedata.category(character).startswith("C")
            for character in normalized
        )
    ):
        normalized = "download"
    return f"files/{index:04d}/{normalized}"


def _validated_name(value: str) -> bytes:
    if "\\" in value or value.startswith("/"):
        raise BatchArchiveError("batch_archive_path_invalid")
    segments = value.split("/")
    if (
        not segments
        or any(segment in {"", ".", ".."} for segment in segments)
    ):
        raise BatchArchiveError("batch_archive_path_invalid")
    encoded = value.encode("utf-8")
    if not encoded or len(encoded) > 65535:
        raise BatchArchiveError("batch_archive_path_invalid")
    return encoded


def _local_header(name: bytes) -> bytes:
    return struct.pack(
        "<I5H3I2H",
        _LOCAL_FILE_HEADER,
        _VERSION_NEEDED,
        _UTF8_DATA_DESCRIPTOR_FLAGS,
        _ZIP_STORED,
        _DOS_TIME,
        _DOS_DATE,
        0,
        0,
        0,
        len(name),
        0,
    )


def _data_descriptor(crc32: int, size_bytes: int) -> bytes:
    return struct.pack(
        "<4I",
        _DATA_DESCRIPTOR,
        crc32,
        size_bytes,
        size_bytes,
    )


def _central_directory_header(
    entry: _CentralDirectoryEntry,
) -> bytes:
    return struct.pack(
        "<I6H3I5H2I",
        _CENTRAL_DIRECTORY_HEADER,
        _VERSION_MADE_BY_UNIX,
        _VERSION_NEEDED,
        _UTF8_DATA_DESCRIPTOR_FLAGS,
        _ZIP_STORED,
        _DOS_TIME,
        _DOS_DATE,
        entry.crc32,
        entry.size_bytes,
        entry.size_bytes,
        len(entry.name),
        0,
        0,
        0,
        0,
        _REGULAR_FILE_0600,
        entry.local_header_offset,
    )


def _end_of_central_directory(
    *,
    entry_count: int,
    central_directory_size: int,
    central_directory_offset: int,
) -> bytes:
    return struct.pack(
        "<I4H2IH",
        _END_OF_CENTRAL_DIRECTORY,
        0,
        0,
        entry_count,
        entry_count,
        central_directory_size,
        central_directory_offset,
        0,
    )


def _archive_content_length(
    named_sizes: tuple[tuple[bytes, int], ...],
) -> int:
    local_total = sum(
        30 + len(name) + size_bytes + 16
        for name, size_bytes in named_sizes
    )
    central_total = sum(46 + len(name) for name, _ in named_sizes)
    return local_total + central_total + 22


def prepare_batch_archive(
    entries: list[BatchArchiveEntry] | tuple[BatchArchiveEntry, ...],
    *,
    max_total_source_bytes: int,
) -> PreparedBatchArchive:
    resolved = tuple(entries)
    if not 1 <= len(resolved) <= MAX_BATCH_DOWNLOAD_ASSETS:
        raise BatchArchiveError("batch_asset_count_invalid")

    seen_paths: set[str] = set()
    total_source_bytes = 0
    manifest_files: list[dict[str, Any]] = []
    named_sizes: list[tuple[bytes, int]] = []
    for entry in resolved:
        name = _validated_name(entry.archive_path)
        if entry.archive_path in seen_paths:
            raise BatchArchiveError("batch_archive_path_duplicate")
        seen_paths.add(entry.archive_path)
        if (
            type(entry.size_bytes) is not int
            or entry.size_bytes < 0
            or entry.size_bytes > MAX_ZIP32_BYTES
            or _SHA256_RE.fullmatch(entry.sha256) is None
        ):
            raise BatchArchiveError("batch_asset_metadata_invalid")
        total_source_bytes += entry.size_bytes
        if total_source_bytes > max_total_source_bytes:
            raise BatchArchiveError("batch_download_bytes_exceeded")
        manifest_files.append(
            {
                **entry.manifest_record,
                "archive_path": entry.archive_path,
                "size_bytes": entry.size_bytes,
                "sha256": entry.sha256,
            }
        )
        named_sizes.append((name, entry.size_bytes))

    manifest = {
        "format": MANIFEST_FORMAT,
        "version": MANIFEST_VERSION,
        "archive_format": ARCHIVE_FORMAT,
        "compression": "stored",
        "file_count": len(resolved),
        "total_uncompressed_bytes": total_source_bytes,
        "files": manifest_files,
    }
    try:
        manifest_bytes = (
            json.dumps(
                manifest,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise BatchArchiveError("batch_asset_metadata_invalid") from exc
    if len(manifest_bytes) > MAX_ZIP32_BYTES:
        raise BatchArchiveError("batch_manifest_too_large")

    manifest_name = _validated_name(MANIFEST_PATH)
    all_named_sizes = (
        (manifest_name, len(manifest_bytes)),
        *named_sizes,
    )
    content_length = _archive_content_length(all_named_sizes)
    if content_length > MAX_ZIP32_BYTES:
        raise BatchArchiveError("batch_archive_too_large")
    return PreparedBatchArchive(
        entries=resolved,
        manifest_bytes=manifest_bytes,
        manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
        total_source_bytes=total_source_bytes,
        content_length=content_length,
    )


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def iter_prepared_archive(
    prepared: PreparedBatchArchive,
    materialize: Callable[[BatchArchiveEntry], MaterializedSource],
) -> Iterator[bytes]:
    """Yield a deterministic ZIP32 archive while holding one source at a time."""

    central_entries: list[_CentralDirectoryEntry] = []
    offset = 0

    manifest_name = _validated_name(MANIFEST_PATH)
    manifest_header_offset = offset
    header = _local_header(manifest_name)
    yield header
    offset += len(header)
    yield manifest_name
    offset += len(manifest_name)
    manifest_crc = binascii.crc32(prepared.manifest_bytes) & 0xFFFFFFFF
    for start in range(
        0,
        len(prepared.manifest_bytes),
        ZIP_STREAM_CHUNK_BYTES,
    ):
        chunk = prepared.manifest_bytes[
            start : start + ZIP_STREAM_CHUNK_BYTES
        ]
        yield chunk
        offset += len(chunk)
    descriptor = _data_descriptor(
        manifest_crc,
        len(prepared.manifest_bytes),
    )
    yield descriptor
    offset += len(descriptor)
    central_entries.append(
        _CentralDirectoryEntry(
            name=manifest_name,
            crc32=manifest_crc,
            size_bytes=len(prepared.manifest_bytes),
            local_header_offset=manifest_header_offset,
        )
    )

    for entry in prepared.entries:
        name = _validated_name(entry.archive_path)
        local_header_offset = offset
        header = _local_header(name)
        yield header
        offset += len(header)
        yield name
        offset += len(name)

        materialized: MaterializedSource | None = None
        digest = hashlib.sha256()
        crc32 = 0
        size_bytes = 0
        try:
            materialized = materialize(entry)
            with materialized.path.open("rb") as source:
                while True:
                    chunk = source.read(ZIP_STREAM_CHUNK_BYTES)
                    if not chunk:
                        break
                    size_bytes += len(chunk)
                    if size_bytes > entry.size_bytes:
                        raise BatchArchiveError(
                            "batch_source_integrity_failed"
                        )
                    digest.update(chunk)
                    crc32 = binascii.crc32(chunk, crc32)
                    yield chunk
                    offset += len(chunk)
            if (
                size_bytes != entry.size_bytes
                or digest.hexdigest() != entry.sha256
            ):
                raise BatchArchiveError("batch_source_integrity_failed")
        finally:
            if materialized is not None and materialized.temporary:
                _safe_unlink(materialized.path)

        crc32 &= 0xFFFFFFFF
        descriptor = _data_descriptor(crc32, size_bytes)
        yield descriptor
        offset += len(descriptor)
        central_entries.append(
            _CentralDirectoryEntry(
                name=name,
                crc32=crc32,
                size_bytes=size_bytes,
                local_header_offset=local_header_offset,
            )
        )

    central_directory_offset = offset
    for central_entry in central_entries:
        header = _central_directory_header(central_entry)
        yield header
        offset += len(header)
        yield central_entry.name
        offset += len(central_entry.name)
    central_directory_size = offset - central_directory_offset
    end = _end_of_central_directory(
        entry_count=len(central_entries),
        central_directory_size=central_directory_size,
        central_directory_offset=central_directory_offset,
    )
    expected_final_size = offset + len(end)
    if expected_final_size != prepared.content_length:
        raise BatchArchiveError("batch_archive_size_mismatch")
    yield end


def _next_or_end(iterator: Iterator[bytes]) -> bytes | object:
    try:
        return next(iterator)
    except StopIteration:
        return _END


async def async_iter_prepared_archive(
    prepared: PreparedBatchArchive,
    materialize: Callable[[BatchArchiveEntry], MaterializedSource],
) -> AsyncIterator[bytes]:
    """Bridge the bounded sync ZIP writer to ASGI with cancellation cleanup."""

    iterator = iter_prepared_archive(prepared, materialize)
    try:
        while True:
            chunk = await anyio.to_thread.run_sync(
                _next_or_end,
                iterator,
            )
            if chunk is _END:
                break
            assert isinstance(chunk, bytes)
            yield chunk
    finally:
        with anyio.CancelScope(shield=True):
            await anyio.to_thread.run_sync(iterator.close)
