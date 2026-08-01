"""DWS history collection and the narrow Private-Database sparse writer.

The only persistent raw authority written here is
``Private-KMDatabase/KMFA/daily_funds`` in the private GitHub repository.  The
runtime journal carries hashes/cursors only; it never becomes a second raw
archive.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

from .config import DailyFundsConfig
from .state import RuntimeState

UTC = timezone.utc
BEIJING = ZoneInfo("Asia/Shanghai")

SPARSE_PATH = Path("Private-KMDatabase/KMFA/daily_funds")
DIRECT_BLOB_MAX_BYTES = 94_371_840
CHUNK_BYTES = 48 * 1024 * 1024
ALLOWED_SUFFIXES = frozenset({".csv", ".txt", ".xlsx", ".xlsm"})


class IngestionError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class DwsPage:
    messages: tuple[dict[str, Any], ...]
    next_cursor: str | None
    has_more: bool


@dataclass(frozen=True)
class DownloadedAttachment:
    message: dict[str, Any]
    message_id: str
    message_id_hash: str
    message_at: datetime
    index: int
    filename: str
    family: str | None
    payload: bytes
    sha256: str
    mime: str | None


@dataclass(frozen=True)
class StagedRawBatch:
    batch_id: str
    paths: tuple[str, ...]
    attachment_hashes: tuple[str, ...]
    occurrences: int
    reassembly_manifest_paths: tuple[str, ...]


@dataclass(frozen=True)
class GitCommit:
    commit_sha: str
    staged: StagedRawBatch
    bundle_bytes: bytes
    # These bytes have been re-opened from a fresh sparse clone at
    # ``commit_sha``.  Downstream R2, parsing and reconciliation must consume
    # this list rather than the transient DWS download buffer.
    verified_attachments: tuple[DownloadedAttachment, ...] = ()


def _hash_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _message_field(message: Mapping[str, Any], names: Sequence[str]) -> str | None:
    for name in names:
        value = message.get(name)
        if value not in (None, ""):
            return str(value)
    return None


def _message_timestamp(message: Mapping[str, Any]) -> datetime:
    raw = _message_field(message, ("createTime", "createdAt", "timestamp", "sendTime", "msgTime"))
    if not raw:
        raise IngestionError("MESSAGE_TIMESTAMP_MISSING")
    if raw.isdigit():
        value = int(raw)
        if value > 10_000_000_000:
            value //= 1000
        return datetime.fromtimestamp(value, tz=UTC)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IngestionError("MESSAGE_TIMESTAMP_INVALID") from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _attachments(message: Mapping[str, Any]) -> list[dict[str, Any]]:
    # DWS serialises different message types with one of these top-level lists.
    # We do not recursively hunt arbitrary nested JSON: doing so risks treating
    # a quoted old message as a fresh attachment occurrence.
    for key in ("attachments", "fileList", "files", "attachmentList"):
        value = message.get(key)
        if isinstance(value, list):
            return [dict(item) for item in value if isinstance(item, Mapping)]
    content = message.get("content")
    if isinstance(content, Mapping):
        for key in ("attachments", "fileList", "files"):
            value = content.get(key)
            if isinstance(value, list):
                return [dict(item) for item in value if isinstance(item, Mapping)]
    return []


def _family(message: Mapping[str, Any]) -> str | None:
    fragments: list[str] = []
    for key in ("text", "content", "msgContent", "title", "fileName", "name"):
        value = message.get(key)
        if isinstance(value, Mapping):
            fragments.append(json.dumps(value, ensure_ascii=False))
        elif value not in (None, ""):
            fragments.append(str(value))
    for item in _attachments(message):
        fragments.extend(str(item.get(key) or "") for key in ("fileName", "name", "title"))
    text = " ".join(fragments)
    if "资金账户明细表" in text:
        return "资金账户明细表"
    if "资金流水明细" in text:
        return "资金流水明细"
    if "资金明细" in text:
        return "资金明细"
    return None


def _extract_page(payload: object) -> DwsPage:
    """Find the DWS paged result without silently fabricating ``hasMore``."""

    candidates: list[Mapping[str, Any]] = []

    def visit(value: object) -> None:
        if isinstance(value, Mapping):
            if "hasMore" in value or "has_more" in value:
                candidates.append(value)
            for child in value.values():
                if isinstance(child, Mapping):
                    visit(child)

    visit(payload)
    for candidate in candidates:
        raw_more = candidate.get("hasMore", candidate.get("has_more"))
        if not isinstance(raw_more, bool):
            continue
        records: object | None = None
        for key in ("messages", "items", "records", "list"):
            if isinstance(candidate.get(key), list):
                records = candidate[key]
                break
        if records is None and isinstance(candidate.get("data"), list):
            records = candidate["data"]
        if records is None:
            continue
        next_cursor = candidate.get("nextCursor", candidate.get("next_cursor"))
        if raw_more and not isinstance(next_cursor, str):
            raise IngestionError("NEXT_CURSOR_MISSING")
        return DwsPage(
            tuple(dict(item) for item in records if isinstance(item, Mapping)),
            str(next_cursor) if isinstance(next_cursor, str) and next_cursor else None,
            raw_more,
        )
    raise IngestionError("DWS_PAGE_SHAPE_INVALID")


class DwsHistoryClient:
    """Exact history-search client; event delivery is intentionally absent."""

    def __init__(
        self,
        config: DailyFundsConfig,
        *,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ):
        self.config = config
        self._runner = runner

    def _environment(self) -> dict[str, str]:
        # Do not inherit another KMFA skill's DWS profile, keyring or optional
        # profile selector.  DWS gets only a tiny process environment plus this
        # slice's own persistent config/keyring roots.
        passthrough = (
            "PATH", "LANG", "LC_ALL", "TZ", "SSL_CERT_FILE", "SSL_CERT_DIR",
            "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY",
        )
        env = {key: value for key in passthrough if (value := os.environ.get(key))}
        home = self.config.dws_config_dir / "home"
        home.mkdir(parents=True, exist_ok=True)
        env.update({
            "HOME": str(home),
            "DWS_CONFIG_DIR": str(self.config.dws_config_dir),
            "XDG_DATA_HOME": str(self.config.dws_keyring_dir),
            "DWS_CLIENT_ID": self.config.dws_client_id,
            "DWS_CLIENT_SECRET": self.config.dws_client_secret,
        })
        return env

    def search(self, start: datetime, end: datetime, cursor: str | None) -> DwsPage:
        command = [
            self.config.dws_bin,
            "chat", "message", "search-advanced",
            "--conversation-ids", self.config.group_id,
            "--start", start.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "--end", end.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "--limit", "100",
            "--cursor", cursor if cursor is not None else "0",
            "--format", "json",
        ]
        try:
            completed = self._runner(
                command,
                capture_output=True,
                text=True,
                check=False,
                env=self._environment(),
                timeout=90,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise IngestionError("DWS_HISTORY_UNAVAILABLE") from exc
        if completed.returncode != 0:
            raise IngestionError("AUTH_REQUIRED" if completed.returncode in {1, 401, 403} else "DWS_HISTORY_FAILED")
        try:
            return _extract_page(json.loads(completed.stdout))
        except json.JSONDecodeError as exc:
            raise IngestionError("DWS_HISTORY_JSON_INVALID") from exc

    def assert_exact_source(self, message: Mapping[str, Any]) -> None:
        conversation_id = _message_field(message, ("openConversationId", "conversationId", "conversation_id"))
        sender_id = _message_field(message, ("senderId", "sender_id", "senderStaffId", "senderUserId"))
        if conversation_id != self.config.group_id or sender_id != self.config.sender_id:
            raise IngestionError("AMBIGUOUS_SOURCE")

    def selected_messages(self, page: DwsPage) -> tuple[dict[str, Any], ...]:
        """Keep only the configured sender's two document families.

        A history search is group-scoped and therefore normally contains other
        participants.  Other senders are not an error and must not make the
        job unavailable.  A returned *different group* is a source-integrity
        failure because it contradicts the command's exact conversation ID.
        """

        selected: list[dict[str, Any]] = []
        for message in page.messages:
            conversation_id = _message_field(message, ("openConversationId", "conversationId", "conversation_id"))
            sender_id = _message_field(message, ("senderId", "sender_id", "senderStaffId", "senderUserId"))
            if conversation_id != self.config.group_id:
                raise IngestionError("AMBIGUOUS_SOURCE")
            if sender_id == self.config.sender_id and _family(message) is not None:
                selected.append(message)
        return tuple(selected)

    @staticmethod
    def attachment_count(message: Mapping[str, Any]) -> int:
        return len(_attachments(message))

    def download(self, message: dict[str, Any], index: int) -> DownloadedAttachment:
        self.assert_exact_source(message)
        attachments = _attachments(message)
        if index >= len(attachments):
            raise IngestionError("ATTACHMENT_INDEX_INVALID")
        attachment = attachments[index]
        media_id = _message_field(attachment, ("mediaId", "media_id", "resourceId", "resource_id"))
        if not media_id:
            raise IngestionError("UNSUPPORTED_ATTACHMENT")
        message_id = _message_field(message, ("openMessageId", "messageId", "message_id", "id"))
        if not message_id:
            raise IngestionError("MESSAGE_ID_MISSING")
        filename = _message_field(attachment, ("fileName", "name", "title")) or f"attachment-{index}.bin"
        with tempfile.TemporaryDirectory(prefix="daily-funds-dws-", dir=self.config.state_dir) as temp:
            output = Path(temp) / "download"
            output.mkdir()
            command = [
                self.config.dws_bin,
                "chat", "message", "download-media",
                "--type", "mediaId",
                "--resource-id", media_id,
                "--message-id", message_id,
                "--open-conversation-id", self.config.group_id,
                "--output", str(output),
            ]
            try:
                completed = self._runner(
                    command,
                    capture_output=True,
                    text=True,
                    check=False,
                    env=self._environment(),
                    timeout=180,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise IngestionError("ATTACHMENT_DOWNLOAD_FAILED") from exc
            if completed.returncode != 0:
                raise IngestionError("AUTH_REQUIRED" if completed.returncode in {1, 401, 403} else "ATTACHMENT_DOWNLOAD_FAILED")
            files = [path for path in output.rglob("*") if path.is_file()]
            if len(files) != 1:
                raise IngestionError("ATTACHMENT_DOWNLOAD_AMBIGUOUS")
            payload = files[0].read_bytes()
        if not payload:
            raise IngestionError("CORRUPT_ATTACHMENT")
        return DownloadedAttachment(
            message=message,
            message_id=message_id,
            message_id_hash=_hash_text(message_id),
            message_at=_message_timestamp(message),
            index=index,
            filename=filename,
            family=_family(message),
            payload=payload,
            sha256=sha256(payload).hexdigest(),
            mime=_message_field(attachment, ("mimeType", "mime", "contentType")),
        )


class HistoryPoller:
    """Cursor-safe polling.  No page advances high water until all its raw
    occurrences have been persisted by the injected callback.
    """

    def __init__(self, state: RuntimeState, client: DwsHistoryClient):
        self.state = state
        self.client = client

    def poll(
        self,
        *,
        now: datetime,
        persist_page: Callable[[DwsPage], None],
        holder: str,
        cursor_key: str = "history_next_cursor",
        high_water_key: str = "history_high_water_at",
        start_override: datetime | None = None,
    ) -> int:
        if not self.state.acquire_lease("poll_lock", holder, ttl_seconds=14 * 60):
            raise IngestionError("POLL_LOCK_HELD")
        try:
            previous_high_water = self.state.get(high_water_key)
            if start_override is not None:
                start = start_override
            elif previous_high_water:
                start = datetime.fromisoformat(previous_high_water.replace("Z", "+00:00")) - timedelta(minutes=30)
            else:
                # Current-day priority is defined in the business timezone,
                # not UTC.  Around Beijing midnight the former implementation
                # silently skipped eight hours of the intended initial window.
                start = now.astimezone(BEIJING).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
            cursor = self.state.get_cursor(cursor_key) or None
            pages = 0
            candidate_cursor = cursor
            while True:
                page = self.client.search(start, now, candidate_cursor)
                persist_page(page)
                pages += 1
                candidate_cursor = page.next_cursor
                if not page.has_more:
                    break
                if candidate_cursor is None:
                    raise IngestionError("NEXT_CURSOR_MISSING")
            # Commit both durable high-water markers only after every page and
            # each raw persistence callback succeeded.
            self.state.commit_cursor(candidate_cursor, cursor_key)
            self.state.put(high_water_key, now.astimezone(UTC).isoformat().replace("+00:00", "Z"))
            return pages
        finally:
            self.state.release_lease("poll_lock", holder)


class RawMaterializer:
    """Write byte-identical raw blobs and deterministic manifests below a root."""

    @staticmethod
    def _suffix(filename: str) -> str:
        suffix = Path(filename).suffix.lower()
        return suffix if suffix and len(suffix) <= 10 and suffix.replace(".", "").isalnum() else ".bin"

    @staticmethod
    def _write_once(path: Path, payload: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != payload:
                raise IngestionError("RAW_PATH_HASH_COLLISION")
            return
        path.write_bytes(payload)

    def stage(self, root: Path, attachments: Iterable[DownloadedAttachment]) -> StagedRawBatch:
        frozen = list(attachments)
        if not frozen:
            raise IngestionError("SOURCE_MISSING")
        paths: list[str] = []
        manifests: list[str] = []
        hash_list: list[str] = []
        batch_rows: list[dict[str, Any]] = []
        for attachment in frozen:
            if sha256(attachment.payload).hexdigest() != attachment.sha256:
                raise IngestionError("RAW_SOURCE_HASH_MISMATCH")
            day = attachment.message_at.astimezone(BEIJING).date()
            prefix = attachment.sha256[:2]
            suffix = self._suffix(attachment.filename)
            blob_path = Path("raw/blobs/sha256") / prefix / f"{attachment.sha256}{suffix}"
            blob_absolute = root / blob_path
            if len(attachment.payload) <= DIRECT_BLOB_MAX_BYTES:
                self._write_once(blob_absolute, attachment.payload)
                object_paths = [str(blob_path)]
                reassembly = None
            else:
                object_paths = []
                part_hashes: list[str] = []
                for index, offset in enumerate(range(0, len(attachment.payload), CHUNK_BYTES)):
                    part = attachment.payload[offset:offset + CHUNK_BYTES]
                    part_path = Path("raw/chunks/sha256") / attachment.sha256 / f"{index:06d}.part"
                    self._write_once(root / part_path, part)
                    object_paths.append(str(part_path))
                    part_hashes.append(sha256(part).hexdigest())
                manifest_path = Path("raw/chunks/sha256") / attachment.sha256 / "reassembly.json"
                reassembly_payload = {
                    "schema_version": "kmfa.daily_funds.reassembly.v1",
                    "sha256": attachment.sha256,
                    "original_size_bytes": len(attachment.payload),
                    "chunk_size_bytes": CHUNK_BYTES,
                    "chunks": part_hashes,
                }
                self._write_once(root / manifest_path, (json.dumps(reassembly_payload, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
                object_paths.append(str(manifest_path))
                manifests.append(str(manifest_path))
                reassembly = str(manifest_path)
            message_path = Path("raw/messages") / day.strftime("%Y/%m/%d") / f"{attachment.message_id_hash}.json"
            self._write_once(root / message_path, (json.dumps(attachment.message, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
            occurrence_path = (
                Path("raw/occurrences") / day.strftime("%Y/%m/%d") /
                attachment.message_id_hash / f"{attachment.index}.json"
            )
            occurrence = {
                "schema_version": "kmfa.daily_funds.occurrence.v1",
                "message_id_hash": attachment.message_id_hash,
                "attachment_index": attachment.index,
                "attachment_sha256": attachment.sha256,
                "attachment_size_bytes": len(attachment.payload),
                "filename": attachment.filename,
                "mime": attachment.mime,
                "family": attachment.family,
                "message_path": str(message_path),
                "object_paths": object_paths,
                "reassembly_manifest": reassembly,
                # Immutable raw manifests must be byte-identical when the
                # 30-minute overlap redelivers the same occurrence.  Runtime
                # time belongs in SQLite, not the Git authority record.
                "message_at": attachment.message_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            }
            self._write_once(root / occurrence_path, (json.dumps(occurrence, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
            paths.extend([str(message_path), str(occurrence_path), *object_paths])
            hash_list.append(attachment.sha256)
            batch_rows.append({
                "message_id_hash": attachment.message_id_hash,
                "attachment_index": attachment.index,
                "attachment_sha256": attachment.sha256,
                "occurrence_path": str(occurrence_path),
            })
        batch_id = sha256(json.dumps(batch_rows, sort_keys=True).encode("utf-8")).hexdigest()
        batch_path = Path("raw/batches") / f"{batch_id}.json"
        batch = {
            "schema_version": "kmfa.daily_funds.batch.v1",
            "batch_id": batch_id,
            "occurrences": batch_rows,
        }
        self._write_once(root / batch_path, (json.dumps(batch, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
        paths.append(str(batch_path))
        return StagedRawBatch(batch_id, tuple(sorted(set(paths))), tuple(sorted(set(hash_list))), len(frozen), tuple(sorted(set(manifests))))

    @staticmethod
    def reassemble(root: Path, attachment_sha256: str) -> bytes:
        manifest_path = root / "raw/chunks/sha256" / attachment_sha256 / "reassembly.json"
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        chunks = []
        for index, expected_sha in enumerate(payload["chunks"]):
            part = (manifest_path.parent / f"{index:06d}.part").read_bytes()
            if sha256(part).hexdigest() != expected_sha:
                raise IngestionError("CHUNK_HASH_MISMATCH")
            chunks.append(part)
        restored = b"".join(chunks)
        if len(restored) != payload["original_size_bytes"] or sha256(restored).hexdigest() != attachment_sha256:
            raise IngestionError("REASSEMBLY_HASH_MISMATCH")
        return restored

    @classmethod
    def readback_attachment(cls, root: Path, attachment: DownloadedAttachment) -> DownloadedAttachment:
        """Load one original payload from an already checked-out Git authority.

        This makes the post-push readback meaningful: if a direct object,
        chunk, or reassembly manifest is missing or altered, R2 and the parser
        never see the transient download bytes as a substitute.
        """

        try:
            suffix = cls._suffix(attachment.filename)
            direct = root / "raw/blobs/sha256" / attachment.sha256[:2] / f"{attachment.sha256}{suffix}"
            payload = direct.read_bytes() if direct.is_file() else cls.reassemble(root, attachment.sha256)
            if sha256(payload).hexdigest() != attachment.sha256:
                raise IngestionError("GIT_READBACK_FAILED")
            return replace(attachment, payload=payload)
        except (OSError, KeyError, TypeError, ValueError, IngestionError) as exc:
            raise IngestionError("GIT_READBACK_FAILED") from exc


class GitSparseWriter:
    """The owner-authorised, single-writer sparse clone exception.

    This code is intentionally standalone rather than using the normal
    ``private_db_client`` read adapter.  It is the only module allowed to clone
    the private repository, always narrows checkout to one path and never force
    pushes.
    """

    def __init__(self, config: DailyFundsConfig, *, runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run):
        self.config = config
        self._runner = runner

    def _git(self, args: Sequence[str], *, cwd: Path | None = None, env: Mapping[str, str] | None = None) -> str:
        try:
            completed = self._runner(
                ["git", *args],
                cwd=str(cwd) if cwd else None,
                capture_output=True,
                text=True,
                check=False,
                env=dict(env) if env else None,
                timeout=180,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise IngestionError("GIT_WRITE_FAILED") from exc
        if completed.returncode != 0:
            raise IngestionError("GIT_NON_FAST_FORWARD" if "non-fast-forward" in (completed.stderr or "").lower() else "GIT_WRITE_FAILED")
        return completed.stdout.strip()

    def _clone_sparse(self, repo: Path, *, env: Mapping[str, str], ref: str) -> None:
        self._git([
            "clone", "--filter=blob:none", "--sparse", "--no-checkout",
            self.config.private_repo, str(repo),
        ], env=env)
        self._git(["sparse-checkout", "set", "--cone", str(SPARSE_PATH)], cwd=repo, env=env)
        self._git(["checkout", ref], cwd=repo, env=env)

    def _readback_sparse_root(self, temp_root: Path, *, env: Mapping[str, str], commit_sha: str) -> Path:
        """Reopen the pushed commit through a new sparse clone.

        ``ls-remote`` only proves that a ref points at a SHA.  This extra clone
        proves that the actual objects which will feed R2/parser can be fetched
        and opened from GitHub after the push succeeds (F-008).
        """

        repo = temp_root / "private-db-readback"
        # Clone first on the permitted branch so sparse setup remains identical
        # to the writer, then detach at the pushed SHA for the actual readback.
        self._clone_sparse(repo, env=env, ref=self.config.private_branch)
        self._git(["checkout", "--detach", commit_sha], cwd=repo, env=env)
        return repo / SPARSE_PATH

    def _readback_attachments(
        self,
        temp_root: Path,
        *,
        env: Mapping[str, str],
        commit_sha: str,
        attachments: Iterable[DownloadedAttachment],
    ) -> tuple[DownloadedAttachment, ...]:
        root = self._readback_sparse_root(temp_root, env=env, commit_sha=commit_sha)
        return tuple(RawMaterializer.readback_attachment(root, attachment) for attachment in attachments)

    def persist(self, attachments: Iterable[DownloadedAttachment]) -> GitCommit:
        self.config.validate(include_storage=False)
        frozen_attachments = tuple(attachments)
        if not self.config.state_dir.exists():
            self.config.state_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="daily-funds-git-", dir=self.config.state_dir) as temp:
            temp_root = Path(temp)
            key_path = temp_root / "private_db_ed25519"
            import base64
            key_path.write_bytes(base64.b64decode(self.config.git_ssh_key_b64))
            key_path.chmod(0o600)
            env = dict(os.environ)
            env["GIT_SSH_COMMAND"] = f"ssh -i {key_path} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
            repo = temp_root / "private-db"
            self._clone_sparse(repo, env=env, ref=self.config.private_branch)
            self._git(["config", "user.name", "kmfa-daily-funds-writer"], cwd=repo, env=env)
            self._git(["config", "user.email", "kmfa-daily-funds@localhost"], cwd=repo, env=env)
            materializer = RawMaterializer()
            staged = materializer.stage(repo / SPARSE_PATH, frozen_attachments)
            self._git(["add", "--", str(SPARSE_PATH)], cwd=repo, env=env)
            try:
                self._git(["diff", "--cached", "--quiet"], cwd=repo, env=env)
                changed = False
            except IngestionError as exc:
                if exc.code != "GIT_WRITE_FAILED":
                    raise
                # `git diff --quiet` exits 1 for changes; ask porcelain without
                # parsing a potentially sensitive filename into logs.
                changed = bool(self._git(["status", "--porcelain"], cwd=repo, env=env))
            if changed:
                self._git(["commit", "-m", f"data(kmfa): daily funds raw batch {staged.batch_id[:12]}"], cwd=repo, env=env)
                try:
                    self._git(["push", "origin", f"HEAD:{self.config.private_branch}"], cwd=repo, env=env)
                except IngestionError as exc:
                    if exc.code != "GIT_NON_FAST_FORWARD":
                        raise
                    self._git(["fetch", "origin", self.config.private_branch], cwd=repo, env=env)
                    self._git(["rebase", f"origin/{self.config.private_branch}"], cwd=repo, env=env)
                    self._git(["push", "origin", f"HEAD:{self.config.private_branch}"], cwd=repo, env=env)
            commit_sha = self._git(["rev-parse", "HEAD"], cwd=repo, env=env)
            remote_head = self._git(["ls-remote", "origin", f"refs/heads/{self.config.private_branch}"], cwd=repo, env=env).split()
            if not remote_head or remote_head[0] != commit_sha:
                raise IngestionError("GIT_READBACK_FAILED")
            verified_attachments = self._readback_attachments(
                temp_root,
                env=env,
                commit_sha=commit_sha,
                attachments=frozen_attachments,
            )
            bundle_path = temp_root / f"{staged.batch_id}.bundle"
            self._git(["bundle", "create", str(bundle_path), "HEAD"], cwd=repo, env=env)
            bundle_bytes = bundle_path.read_bytes()
            if not bundle_bytes:
                raise IngestionError("GIT_BUNDLE_EMPTY")
            return GitCommit(commit_sha, staged, bundle_bytes, verified_attachments)

    def persist_publication(self, publication: Mapping[str, Any]) -> str:
        """Persist the immutable formal publication before its UI pointer moves."""

        self.config.validate(include_storage=False)
        publication_id = str(publication.get("publication_id") or "")
        business_date = str(publication.get("business_date") or "")
        if len(publication_id) != 64 or len(business_date) != 10:
            raise IngestionError("PUBLICATION_SHAPE_INVALID")
        with tempfile.TemporaryDirectory(prefix="daily-funds-publication-", dir=self.config.state_dir) as temp:
            temp_root = Path(temp)
            key_path = temp_root / "private_db_ed25519"
            import base64
            key_path.write_bytes(base64.b64decode(self.config.git_ssh_key_b64))
            key_path.chmod(0o600)
            env = dict(os.environ)
            env["GIT_SSH_COMMAND"] = f"ssh -i {key_path} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
            repo = temp_root / "private-db"
            self._clone_sparse(repo, env=env, ref=self.config.private_branch)
            self._git(["config", "user.name", "kmfa-daily-funds-writer"], cwd=repo, env=env)
            self._git(["config", "user.email", "kmfa-daily-funds@localhost"], cwd=repo, env=env)
            target = repo / SPARSE_PATH / "publications" / business_date / f"{publication_id}.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(publication, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            if target.exists() and target.read_text(encoding="utf-8") != payload:
                raise IngestionError("PUBLICATION_ID_COLLISION")
            target.write_text(payload, encoding="utf-8")
            self._git(["add", "--", str(SPARSE_PATH)], cwd=repo, env=env)
            changed = bool(self._git(["status", "--porcelain"], cwd=repo, env=env))
            if changed:
                self._git(["commit", "-m", f"data(kmfa): daily funds publication {publication_id[:12]}"], cwd=repo, env=env)
                try:
                    self._git(["push", "origin", f"HEAD:{self.config.private_branch}"], cwd=repo, env=env)
                except IngestionError as exc:
                    if exc.code != "GIT_NON_FAST_FORWARD":
                        raise
                    self._git(["fetch", "origin", self.config.private_branch], cwd=repo, env=env)
                    self._git(["rebase", f"origin/{self.config.private_branch}"], cwd=repo, env=env)
                    self._git(["push", "origin", f"HEAD:{self.config.private_branch}"], cwd=repo, env=env)
            commit_sha = self._git(["rev-parse", "HEAD"], cwd=repo, env=env)
            remote = self._git(["ls-remote", "origin", f"refs/heads/{self.config.private_branch}"], cwd=repo, env=env).split()
            if not remote or remote[0] != commit_sha:
                raise IngestionError("GIT_READBACK_FAILED")
            readback_root = self._readback_sparse_root(temp_root, env=env, commit_sha=commit_sha)
            try:
                readback = (readback_root / "publications" / business_date / f"{publication_id}.json").read_text(encoding="utf-8")
            except OSError as exc:
                raise IngestionError("GIT_READBACK_FAILED") from exc
            if readback != payload:
                raise IngestionError("GIT_READBACK_FAILED")
            return commit_sha

    def bundle_head(self) -> bytes:
        """Produce an ephemeral sparse-path Git bundle for OCI recovery."""

        self.config.validate(include_storage=False)
        with tempfile.TemporaryDirectory(prefix="daily-funds-bundle-", dir=self.config.state_dir) as temp:
            temp_root = Path(temp)
            key_path = temp_root / "private_db_ed25519"
            import base64
            key_path.write_bytes(base64.b64decode(self.config.git_ssh_key_b64))
            key_path.chmod(0o600)
            env = dict(os.environ)
            env["GIT_SSH_COMMAND"] = f"ssh -i {key_path} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
            repo = temp_root / "private-db"
            self._clone_sparse(repo, env=env, ref=self.config.private_branch)
            bundle = temp_root / "daily-funds.bundle"
            self._git(["bundle", "create", str(bundle), "HEAD"], cwd=repo, env=env)
            payload = bundle.read_bytes()
            if not payload:
                raise IngestionError("GIT_BUNDLE_EMPTY")
            return payload
