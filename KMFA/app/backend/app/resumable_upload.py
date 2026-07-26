"""Private filesystem staging for the S06/P6.1 offset upload protocol.

The durable upload intent remains in ``consistency_operations``.  This module
only owns bounded, non-public staging chunks until the existing S05 object
workflow verifies and persists the immutable original.  Chunk names contain no
user filename or content and are rooted under the private application state
directory.
"""

from __future__ import annotations

import fcntl
import hashlib
import os
import re
import secrets
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

UPLOAD_SESSION_ID_RE = re.compile(r"^operation_[A-Za-z0-9_-]{24}$")
_CHUNK_OFFSET_WIDTH = 20


class ResumableStorageError(RuntimeError):
    """Static, non-sensitive staging failure."""

    def __init__(self, code: str, *, offset: int | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.offset = offset


@dataclass(frozen=True)
class ChunkRecord:
    offset: int
    size_bytes: int
    path: Path


@dataclass(frozen=True)
class UploadSnapshot:
    offset_bytes: int
    chunk_count: int


def resumable_staged_name(upload_session_id: str) -> str:
    _validate_session_id(upload_session_id)
    return f"resumable-{upload_session_id}.complete"


def is_resumable_staged_name(value: str) -> bool:
    if not value.startswith("resumable-") or not value.endswith(".complete"):
        return False
    session_id = value[len("resumable-") : -len(".complete")]
    return UPLOAD_SESSION_ID_RE.fullmatch(session_id) is not None


def _validate_session_id(upload_session_id: str) -> None:
    if UPLOAD_SESSION_ID_RE.fullmatch(upload_session_id) is None:
        raise ResumableStorageError("upload_session_not_found")


def _chunk_prefix(upload_session_id: str) -> str:
    _validate_session_id(upload_session_id)
    return f"resumable-{upload_session_id}-"


def _chunk_name(upload_session_id: str, offset: int) -> str:
    if offset < 0:
        raise ResumableStorageError("invalid_upload_offset")
    return (
        f"{_chunk_prefix(upload_session_id)}"
        f"{offset:0{_CHUNK_OFFSET_WIDTH}d}.chunk"
    )


def _chunk_pattern(upload_session_id: str) -> re.Pattern[str]:
    return re.compile(
        rf"^{re.escape(_chunk_prefix(upload_session_id))}"
        rf"(?P<offset>[0-9]{{{_CHUNK_OFFSET_WIDTH}}})\.chunk$"
    )


def _lock_path(tmp_dir: Path, upload_session_id: str) -> Path:
    _validate_session_id(upload_session_id)
    return tmp_dir / f"resumable-{upload_session_id}.lock"


def _staged_path(tmp_dir: Path, upload_session_id: str) -> Path:
    return tmp_dir / resumable_staged_name(upload_session_id)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _validate_regular_private_file(path: Path) -> int:
    try:
        details = path.lstat()
    except OSError as exc:
        raise ResumableStorageError("resumable_storage_unavailable") from exc
    if path.is_symlink() or not stat.S_ISREG(details.st_mode):
        raise ResumableStorageError("resumable_storage_unavailable")
    return int(details.st_size)


@contextmanager
def _session_lock(
    tmp_dir: Path,
    upload_session_id: str,
) -> Iterator[None]:
    path = _lock_path(tmp_dir, upload_session_id)
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
        details = os.fstat(descriptor)
        if not stat.S_ISREG(details.st_mode):
            raise ResumableStorageError("resumable_storage_unavailable")
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    except ResumableStorageError:
        raise
    except OSError as exc:
        raise ResumableStorageError("resumable_storage_unavailable") from exc
    finally:
        if "descriptor" in locals():
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)


def _inventory_unlocked(
    tmp_dir: Path,
    upload_session_id: str,
    *,
    expected_size: int,
    max_chunk_bytes: int,
) -> list[ChunkRecord]:
    pattern = _chunk_pattern(upload_session_id)
    rows: list[ChunkRecord] = []
    try:
        candidates = list(
            tmp_dir.glob(f"{_chunk_prefix(upload_session_id)}*.chunk")
        )
    except OSError as exc:
        raise ResumableStorageError("resumable_storage_unavailable") from exc
    for path in candidates:
        match = pattern.fullmatch(path.name)
        if match is None or path.parent.resolve() != tmp_dir.resolve():
            raise ResumableStorageError("resumable_storage_unavailable")
        size = _validate_regular_private_file(path)
        if size < 1 or size > max_chunk_bytes:
            raise ResumableStorageError("upload_chunk_state_invalid")
        rows.append(
            ChunkRecord(
                offset=int(match.group("offset")),
                size_bytes=size,
                path=path,
            )
        )
    rows.sort(key=lambda row: row.offset)
    expected_offset = 0
    for row in rows:
        if row.offset != expected_offset:
            raise ResumableStorageError(
                "upload_chunk_state_invalid",
                offset=expected_offset,
            )
        expected_offset += row.size_bytes
        if expected_offset > expected_size:
            raise ResumableStorageError(
                "upload_chunk_state_invalid",
                offset=expected_offset,
            )
        if expected_offset < expected_size and row.size_bytes != max_chunk_bytes:
            raise ResumableStorageError(
                "upload_chunk_state_invalid",
                offset=row.offset,
            )
    return rows


def inspect_upload(
    tmp_dir: Path,
    upload_session_id: str,
    *,
    expected_size: int,
    max_chunk_bytes: int,
) -> UploadSnapshot:
    with _session_lock(tmp_dir, upload_session_id):
        rows = _inventory_unlocked(
            tmp_dir,
            upload_session_id,
            expected_size=expected_size,
            max_chunk_bytes=max_chunk_bytes,
        )
        return UploadSnapshot(
            offset_bytes=sum(row.size_bytes for row in rows),
            chunk_count=len(rows),
        )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise ResumableStorageError("resumable_storage_unavailable") from exc
    return digest.hexdigest()


def store_verified_chunk(
    tmp_dir: Path,
    upload_session_id: str,
    source_path: Path,
    *,
    upload_offset: int,
    chunk_size: int,
    chunk_sha256: str,
    expected_size: int,
    max_chunk_bytes: int,
    active_check: Callable[[], None] | None = None,
) -> UploadSnapshot:
    if chunk_size < 1 or chunk_size > max_chunk_bytes:
        raise ResumableStorageError("upload_chunk_size_invalid")
    if upload_offset < 0:
        raise ResumableStorageError("invalid_upload_offset")
    with _session_lock(tmp_dir, upload_session_id):
        # Keep the durable-state check under the same cross-process lock as
        # the link. A concurrent cancellation can therefore either claim the
        # session first or remove this complete chunk afterwards, but cannot
        # leave a new chunk behind an already-cancelled session.
        if active_check is not None:
            active_check()
        rows = _inventory_unlocked(
            tmp_dir,
            upload_session_id,
            expected_size=expected_size,
            max_chunk_bytes=max_chunk_bytes,
        )
        current_offset = sum(row.size_bytes for row in rows)
        if upload_offset < current_offset:
            existing = next(
                (row for row in rows if row.offset == upload_offset),
                None,
            )
            if (
                existing is not None
                and existing.size_bytes == chunk_size
                and _sha256_file(existing.path) == chunk_sha256
            ):
                return UploadSnapshot(current_offset, len(rows))
            raise ResumableStorageError(
                "upload_chunk_conflict",
                offset=current_offset,
            )
        if upload_offset != current_offset:
            raise ResumableStorageError(
                "upload_offset_conflict",
                offset=current_offset,
            )
        next_offset = current_offset + chunk_size
        if next_offset > expected_size:
            raise ResumableStorageError(
                "artifact_too_large",
                offset=current_offset,
            )
        if next_offset < expected_size and chunk_size != max_chunk_bytes:
            raise ResumableStorageError(
                "upload_chunk_size_invalid",
                offset=current_offset,
            )
        target = tmp_dir / _chunk_name(upload_session_id, current_offset)
        try:
            os.link(source_path, target)
            target.chmod(0o600)
            _fsync_directory(tmp_dir)
        except FileExistsError:
            if (
                _validate_regular_private_file(target) != chunk_size
                or _sha256_file(target) != chunk_sha256
            ):
                raise ResumableStorageError(
                    "upload_chunk_conflict",
                    offset=current_offset,
                )
        except ResumableStorageError:
            raise
        except OSError as exc:
            raise ResumableStorageError(
                "resumable_storage_unavailable"
            ) from exc
        return UploadSnapshot(next_offset, len(rows) + 1)


def assemble_upload(
    tmp_dir: Path,
    upload_session_id: str,
    *,
    expected_size: int,
    expected_sha256: str,
    max_chunk_bytes: int,
) -> Path:
    with _session_lock(tmp_dir, upload_session_id):
        rows = _inventory_unlocked(
            tmp_dir,
            upload_session_id,
            expected_size=expected_size,
            max_chunk_bytes=max_chunk_bytes,
        )
        current_offset = sum(row.size_bytes for row in rows)
        if current_offset != expected_size:
            raise ResumableStorageError(
                "upload_incomplete",
                offset=current_offset,
            )
        staged = _staged_path(tmp_dir, upload_session_id)
        if staged.exists():
            if (
                _validate_regular_private_file(staged) != expected_size
                or _sha256_file(staged) != expected_sha256
            ):
                raise ResumableStorageError(
                    "upload_checksum_mismatch",
                    offset=current_offset,
                )
            return staged

        candidate = tmp_dir / f"request-{secrets.token_urlsafe(24)}.part"
        descriptor = os.open(
            candidate,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o600,
        )
        digest = hashlib.sha256()
        assembled_size = 0
        try:
            with os.fdopen(descriptor, "wb") as output:
                for row in rows:
                    with row.path.open("rb") as source:
                        for block in iter(
                            lambda: source.read(1024 * 1024),
                            b"",
                        ):
                            assembled_size += len(block)
                            digest.update(block)
                            output.write(block)
                output.flush()
                os.fsync(output.fileno())
            if (
                assembled_size != expected_size
                or digest.hexdigest() != expected_sha256
            ):
                raise ResumableStorageError(
                    "upload_checksum_mismatch",
                    offset=current_offset,
                )
            try:
                os.link(candidate, staged)
                staged.chmod(0o600)
                _fsync_directory(tmp_dir)
            except FileExistsError:
                if (
                    _validate_regular_private_file(staged) != expected_size
                    or _sha256_file(staged) != expected_sha256
                ):
                    raise ResumableStorageError(
                        "upload_checksum_mismatch",
                        offset=current_offset,
                    )
            return staged
        except ResumableStorageError:
            raise
        except OSError as exc:
            raise ResumableStorageError(
                "resumable_storage_unavailable"
            ) from exc
        finally:
            try:
                candidate.unlink(missing_ok=True)
            except OSError:
                pass


def cleanup_chunks(
    tmp_dir: Path,
    upload_session_id: str,
    *,
    expected_size: int,
    max_chunk_bytes: int,
) -> None:
    with _session_lock(tmp_dir, upload_session_id):
        rows = _inventory_unlocked(
            tmp_dir,
            upload_session_id,
            expected_size=expected_size,
            max_chunk_bytes=max_chunk_bytes,
        )
        try:
            for row in rows:
                row.path.unlink(missing_ok=True)
            _fsync_directory(tmp_dir)
        except OSError as exc:
            raise ResumableStorageError(
                "resumable_storage_unavailable"
            ) from exc


def discard_incomplete(
    tmp_dir: Path,
    upload_session_id: str,
    *,
    expected_size: int,
    max_chunk_bytes: int,
    before_discard: Callable[[], None] | None = None,
) -> None:
    with _session_lock(tmp_dir, upload_session_id):
        # The caller claims cancellation while the session lock is held.
        # Uploaders perform their active check under this same lock, closing
        # the cleanup/state-transition race across processes.
        if before_discard is not None:
            before_discard()
        rows = _inventory_unlocked(
            tmp_dir,
            upload_session_id,
            expected_size=expected_size,
            max_chunk_bytes=max_chunk_bytes,
        )
        staged = _staged_path(tmp_dir, upload_session_id)
        try:
            for row in rows:
                row.path.unlink(missing_ok=True)
            if staged.exists():
                _validate_regular_private_file(staged)
                staged.unlink()
            _fsync_directory(tmp_dir)
        except OSError as exc:
            raise ResumableStorageError(
                "resumable_storage_unavailable"
            ) from exc
