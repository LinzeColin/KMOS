"""DWS history collection and the narrow Private-Database sparse writer.

The only persistent raw authority written here is
``Private-KMDatabase/KMFA/daily_funds`` in the private GitHub repository.  The
runtime journal carries hashes/cursors only; it never becomes a second raw
archive.
"""

from __future__ import annotations

import base64
import json
import os
import re
import shlex
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
_MEDIA_ID_RE = re.compile(r"mediaId=([^\)\s]+)")


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
class DwsAuthStatus:
    authenticated: bool
    refresh_token_valid: bool


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
    # ``chat message list`` returns a naïve Beijing-local ``createTime``.
    # Treating it as UTC shifts the historical window by eight hours and can
    # drop a report around the business-day boundary.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=BEIJING)
    return parsed.astimezone(UTC)


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
    if not isinstance(content, str):
        return []
    # DWS v1.0.52 represents media attachments inside the message text as
    # ``mediaId=<opaque-id>`` rather than in a top-level attachment array.
    # Keep this narrowly scoped to the documented media token and never walk
    # quoted-message JSON, which would turn an old quoted attachment into a
    # fresh occurrence.
    return [{"mediaId": match.group(1)} for match in _MEDIA_ID_RE.finditer(content)]


def _dws_history_failure_code(*values: object, fallback: str = "DWS_HISTORY_FAILED") -> str:
    """Classify a DWS failure without retaining its potentially sensitive text.

    DWS uses both process exit codes and a JSON business envelope.  A shell
    exit status of ``1`` is not synonymous with an expired OAuth token: the
    real service also uses it for a current-user permission denial.  Keep the
    original diagnostic text in neither the state journal nor status surface;
    reduce it to a stable, actionable machine code instead.
    """

    fragments: list[str] = []

    def add(value: object) -> None:
        if isinstance(value, Mapping):
            for key in ("errorCode", "error_code", "code", "errorMsg", "error_msg", "message"):
                candidate = value.get(key)
                if candidate not in (None, ""):
                    fragments.append(str(candidate))
        elif value not in (None, ""):
            fragments.append(str(value))

    for value in values:
        add(value)
    text = " ".join(fragments).lower()
    if any(token in text for token in ("permission", "denied", "forbidden", "无权限", "权限")):
        return "DWS_HISTORY_PERMISSION_DENIED"
    if any(token in text for token in ("auth", "token", "login", "unauthorized", "认证", "登录", "令牌")):
        return "DWS_AUTH_REQUIRED"
    if any(token in text for token in ("parameter", "argument", "invalid", "参数")):
        return "DWS_HISTORY_ARGUMENT_INVALID"
    return fallback


def _unwrap_dws_history_payload(payload: object) -> object:
    """Validate the DWS v1 business envelope before page extraction.

    ``dws`` can exit zero while returning ``{"success": false, ...}``.  The
    worker must never turn that response into an empty successful scan.
    """

    if not isinstance(payload, Mapping) or "success" not in payload:
        return payload
    if payload.get("success") is not True:
        raise IngestionError(_dws_history_failure_code(payload, fallback="DWS_HISTORY_API_FAILED"))
    result = payload.get("result")
    if not isinstance(result, Mapping):
        raise IngestionError("DWS_HISTORY_RESULT_INVALID")
    return result


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


def _extract_page(payload: object, *, require_next_cursor: bool = True) -> DwsPage:
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
            # DWS v1 represents a valid empty search page as
            # ``{"hasMore": false}`` inside its successful ``result``
            # envelope.  It is a real, bounded zero-result query, whereas a
            # non-terminal page without a records list remains malformed.
            if raw_more is False:
                records = []
            else:
                continue
        next_cursor = candidate.get("nextCursor", candidate.get("next_cursor"))
        if raw_more and require_next_cursor and not isinstance(next_cursor, str):
            raise IngestionError("NEXT_CURSOR_MISSING")
        return DwsPage(
            tuple(dict(item) for item in records if isinstance(item, Mapping)),
            str(next_cursor) if isinstance(next_cursor, str) and next_cursor else None,
            raw_more,
        )
    raise IngestionError("DWS_PAGE_SHAPE_INVALID")


def _format_dws_history_time(value: datetime) -> str:
    """Format the documented DWS list boundary in its Beijing-local syntax."""

    return value.astimezone(BEIJING).strftime("%Y-%m-%d %H:%M:%S")


def _parse_dws_history_cursor(value: str) -> datetime:
    """Decode the durable list boundary without accepting opaque old cursors."""

    try:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise IngestionError("DWS_HISTORY_CURSOR_INVALID") from exc
    return parsed.replace(tzinfo=BEIJING).astimezone(UTC)


class DwsHistoryClient:
    """Exact group-history client; event delivery is intentionally absent."""

    def __init__(
        self,
        config: DailyFundsConfig,
        *,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
        interactive_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
        event_sink: Callable[[str, str, str], None] | None = None,
    ):
        self.config = config
        self._runner = runner
        self._interactive_runner = interactive_runner
        self._event_sink = event_sink
        self._auth_ready = False

    def _record_network_event(self, operation: str, outcome: str) -> None:
        if self._event_sink is not None:
            self._event_sink("DWS", operation, outcome)

    def _run_dws(self, command: list[str], *, operation: str, timeout: int) -> subprocess.CompletedProcess[str]:
        try:
            return self._runner(
                command,
                capture_output=True,
                text=True,
                check=False,
                env=self._environment(),
                timeout=timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            self._record_network_event(operation, "UNAVAILABLE")
            raise

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
        self.config.dws_keyring_dir.mkdir(parents=True, exist_ok=True)
        env.update({
            "HOME": str(home),
            "DWS_CONFIG_DIR": str(self.config.dws_config_dir),
            "DWS_KEYCHAIN_DIR": str(self.config.dws_keyring_dir),
            # On the cloud Linux runtime this selects DWS's file-backed,
            # slice-local keyring.  It also makes an accidental macOS test
            # invocation refuse the host Keychain rather than inheriting it.
            "DWS_DISABLE_KEYCHAIN": "1",
        })
        # An explicit client ID is an isolated deployment override, never an
        # inherited host/other-skill value.  When it is absent, omit the
        # variable entirely so DWS can use its own supported default client.
        # An AppSecret is deliberately never injected into this slice.
        if self.config.dws_client_id:
            env["DWS_CLIENT_ID"] = self.config.dws_client_id
        return env

    def _auth_status(self) -> DwsAuthStatus:
        try:
            completed = self._run_dws(
                [self.config.dws_bin, "auth", "status", "--format", "json"],
                operation="AUTH_STATUS",
                timeout=90,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise IngestionError("DWS_AUTH_STATUS_UNAVAILABLE") from exc
        if completed.returncode != 0:
            self._record_network_event("AUTH_STATUS", "FAILED")
            raise IngestionError("DWS_AUTH_STATUS_FAILED")
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            self._record_network_event("AUTH_STATUS", "INVALID")
            raise IngestionError("DWS_AUTH_STATUS_INVALID") from exc
        if not isinstance(payload, Mapping):
            self._record_network_event("AUTH_STATUS", "INVALID")
            raise IngestionError("DWS_AUTH_STATUS_INVALID")
        self._record_network_event("AUTH_STATUS", "OK")
        return DwsAuthStatus(
            authenticated=payload.get("authenticated") is True,
            refresh_token_valid=payload.get("refresh_token_valid") is True,
        )

    def _import_auth_bundle(self) -> None:
        self.config.state_dir.mkdir(parents=True, exist_ok=True)
        # The bundle is an opaque base64 export created for this dedicated DWS
        # identity.  It is never printed and exists on disk only for the CLI
        # import process inside this temporary directory.
        with tempfile.TemporaryDirectory(prefix="daily-funds-auth-", dir=self.config.state_dir) as temp:
            bundle = Path(temp) / "dws-auth.b64"
            bundle.write_text(self.config.dws_auth_bundle_b64, encoding="ascii")
            bundle.chmod(0o600)
            try:
                completed = self._run_dws(
                    [
                        self.config.dws_bin,
                        "auth",
                        "import",
                        "--input",
                        str(bundle),
                        "--base64",
                        "--force",
                    ],
                    operation="AUTH_IMPORT",
                    timeout=90,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise IngestionError("DWS_AUTH_IMPORT_UNAVAILABLE") from exc
            if completed.returncode != 0:
                self._record_network_event("AUTH_IMPORT", "FAILED")
                raise IngestionError("DWS_AUTH_IMPORT_FAILED")
            self._record_network_event("AUTH_IMPORT", "OK")

    def bootstrap_device_auth(self) -> None:
        """Perform one explicit device login inside this slice's cloud volume.

        This method is intentionally *not* called by cron or normal polling.
        Its stdout/stderr stay attached to the operator's protected cloud
        terminal so a device code never enters runtime files, status JSON or
        cron logs.  Once it succeeds, later jobs need only the isolated DWS
        config/keyring volume and run unattended.
        """

        self.config.validate_dws_bootstrap()
        status = self._auth_status()
        if status.authenticated and status.refresh_token_valid:
            self._auth_ready = True
            self._record_network_event("AUTH_BOOTSTRAP", "ALREADY_READY")
            return
        self._record_network_event("AUTH_BOOTSTRAP", "STARTED")
        try:
            completed = self._interactive_runner(
                [self.config.dws_bin, "auth", "login", "--device", "--no-browser", "--yes"],
                text=True,
                check=False,
                env=self._environment(),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            self._record_network_event("AUTH_BOOTSTRAP", "UNAVAILABLE")
            raise IngestionError("DWS_AUTH_BOOTSTRAP_UNAVAILABLE") from exc
        if completed.returncode != 0:
            self._record_network_event("AUTH_BOOTSTRAP", "FAILED")
            raise IngestionError("DWS_AUTH_BOOTSTRAP_FAILED")
        status = self._auth_status()
        if not (status.authenticated and status.refresh_token_valid):
            self._record_network_event("AUTH_BOOTSTRAP", "AUTH_REQUIRED")
            raise IngestionError("DWS_AUTH_REQUIRED")
        self._auth_ready = True
        self._record_network_event("AUTH_BOOTSTRAP", "OK")

    def ensure_authenticated(self) -> None:
        """Establish only this slice's portable DWS auth state, fail closed."""

        if self._auth_ready:
            return
        status = self._auth_status()
        if not (status.authenticated and status.refresh_token_valid):
            if not self.config.dws_auth_bundle_b64:
                # No cloud profile and no explicit recovery bundle is a hard
                # source gate.  Never launch an interactive login from cron.
                self._record_network_event("AUTH_IMPORT", "NOT_CONFIGURED")
                raise IngestionError("DWS_AUTH_REQUIRED")
            self._import_auth_bundle()
            status = self._auth_status()
        if not (status.authenticated and status.refresh_token_valid):
            raise IngestionError("DWS_AUTH_REQUIRED")
        self._auth_ready = True

    def search(self, start: datetime, end: datetime, cursor: str | None) -> DwsPage:
        self.ensure_authenticated()
        start = start.astimezone(UTC)
        end = end.astimezone(UTC)
        anchor = _parse_dws_history_cursor(cursor) if cursor else end
        if anchor < start:
            return DwsPage(messages=(), next_cursor=None, has_more=False)
        command = [
            self.config.dws_bin,
            "chat", "message", "list",
            "--group", self.config.group_id,
            # DWS documents list pagination as a boundary ``createTime``;
            # the server returns newest-to-oldest for ``older``.  It is not
            # the opaque cursor contract used by search-advanced.
            "--time", _format_dws_history_time(anchor),
            "--direction", "older",
            "--limit", "30",
            "--format", "json",
        ]
        try:
            completed = self._run_dws(
                command,
                operation="HISTORY_LIST",
                timeout=90,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise IngestionError("DWS_HISTORY_UNAVAILABLE") from exc
        if completed.returncode != 0:
            code = _dws_history_failure_code(completed.stdout, completed.stderr)
            self._record_network_event("HISTORY_LIST", code)
            raise IngestionError(code)
        try:
            payload = json.loads(completed.stdout)
            raw_page = _extract_page(
                _unwrap_dws_history_payload(payload),
                require_next_cursor=False,
            )
        except (IngestionError, json.JSONDecodeError) as exc:
            if isinstance(exc, IngestionError):
                self._record_network_event("HISTORY_LIST", exc.code)
                raise
            self._record_network_event("HISTORY_LIST", "INVALID")
            raise IngestionError("DWS_HISTORY_JSON_INVALID") from exc
        try:
            timestamps = tuple(_message_timestamp(message) for message in raw_page.messages)
        except IngestionError as exc:
            self._record_network_event("HISTORY_LIST", exc.code)
            raise
        if raw_page.has_more and not timestamps:
            self._record_network_event("HISTORY_LIST", "INVALID")
            raise IngestionError("DWS_HISTORY_BOUNDARY_MISSING")
        boundary = min(timestamps) if timestamps else None
        if boundary is not None and boundary >= anchor and raw_page.has_more:
            self._record_network_event("HISTORY_LIST", "INVALID")
            raise IngestionError("DWS_HISTORY_CURSOR_STALLED")
        page_messages = tuple(
            message
            for message, timestamp in zip(raw_page.messages, timestamps)
            if start <= timestamp <= end
        )
        has_more = raw_page.has_more and boundary is not None and boundary > start
        page = DwsPage(
            messages=page_messages,
            next_cursor=_format_dws_history_time(boundary) if has_more and boundary is not None else None,
            has_more=has_more,
        )
        self._record_network_event("HISTORY_LIST", "OK")
        return page

    def assert_exact_source(self, message: Mapping[str, Any]) -> None:
        conversation_id = _message_field(message, ("openConversationId", "conversationId", "conversation_id"))
        # ``sender`` is a display name.  The stable source gate must use the
        # opaque senderOpenDingTalkId that DWS returns with group history.
        sender_id = _message_field(message, ("senderOpenDingTalkId", "sender_open_dingtalk_id"))
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
            sender_id = _message_field(message, ("senderOpenDingTalkId", "sender_open_dingtalk_id"))
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
        self.ensure_authenticated()
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
        declared_filename = _message_field(attachment, ("fileName", "name", "title"))
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
                "--format", "json",
            ]
            try:
                completed = self._run_dws(
                    command,
                    operation="ATTACHMENT_DOWNLOAD",
                    timeout=180,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise IngestionError("ATTACHMENT_DOWNLOAD_FAILED") from exc
            if completed.returncode != 0:
                code = "AUTH_REQUIRED" if completed.returncode in {1, 401, 403} else "FAILED"
                self._record_network_event("ATTACHMENT_DOWNLOAD", code)
                raise IngestionError("AUTH_REQUIRED" if code == "AUTH_REQUIRED" else "ATTACHMENT_DOWNLOAD_FAILED")
            files = [path for path in output.rglob("*") if path.is_file()]
            if len(files) != 1:
                self._record_network_event("ATTACHMENT_DOWNLOAD", "INVALID")
                raise IngestionError("ATTACHMENT_DOWNLOAD_AMBIGUOUS")
            downloaded = files[0]
            payload = downloaded.read_bytes()
            # Text-embedded media tokens lack a filename.  Prefer a declared
            # source filename when it has a supported suffix; otherwise use
            # DWS's downloaded filename so parsing remains evidence-based.
            filename = declared_filename
            if not filename or Path(filename).suffix.lower() not in ALLOWED_SUFFIXES:
                filename = downloaded.name
        if not payload:
            self._record_network_event("ATTACHMENT_DOWNLOAD", "INVALID")
            raise IngestionError("CORRUPT_ATTACHMENT")
        self._record_network_event("ATTACHMENT_DOWNLOAD", "OK")
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
                if not page.has_more:
                    # DWS defines ``nextCursor`` as a continuation token only
                    # while ``hasMore`` is true.  A terminal response may
                    # still contain a value, but persisting it would bind the
                    # next 30-minute overlap query to a completed result set.
                    candidate_cursor = None
                    break
                candidate_cursor = page.next_cursor
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
    def _json_text(value: object, *, code: str) -> str:
        try:
            return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
        except (TypeError, ValueError) as exc:
            raise IngestionError(code) from exc

    @staticmethod
    def _safe_path(root: Path, relative: Path) -> Path:
        """Reject a pre-existing sparse-tree symlink escape before writing."""

        if root.is_symlink():
            raise IngestionError("RAW_PATH_SYMLINK_REJECTED")
        root_resolved = root.resolve()
        candidate = root / relative
        try:
            candidate.resolve(strict=False).relative_to(root_resolved)
        except ValueError as exc:
            raise IngestionError("RAW_PATH_ESCAPE") from exc
        return candidate

    @staticmethod
    def _validate_attachment(attachment: DownloadedAttachment) -> None:
        for value, code in (
            (attachment.message_id_hash, "RAW_MESSAGE_ID_HASH_INVALID"),
            (attachment.sha256, "RAW_ATTACHMENT_HASH_INVALID"),
        ):
            if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
                raise IngestionError(code)
        if not isinstance(attachment.index, int) or isinstance(attachment.index, bool) or attachment.index < 0:
            raise IngestionError("RAW_ATTACHMENT_INDEX_INVALID")
        if not attachment.filename:
            raise IngestionError("RAW_FILENAME_MISSING")
        if attachment.message_at.tzinfo is None or attachment.message_at.utcoffset() is None:
            raise IngestionError("RAW_MESSAGE_TIMESTAMP_INVALID")

    @classmethod
    def canonical_attachments(cls, attachments: Iterable[DownloadedAttachment]) -> tuple[DownloadedAttachment, ...]:
        """Make an overlap batch order-independent without erasing occurrences.

        One immutable occurrence is identified by message hash plus attachment
        index.  An exact repeat belongs to that same occurrence; a different
        byte hash at that address is an integrity conflict and must stop.
        """

        frozen = tuple(attachments)
        if not frozen:
            raise IngestionError("SOURCE_MISSING")
        unique: list[DownloadedAttachment] = []
        by_occurrence: dict[tuple[str, int], DownloadedAttachment] = {}
        for attachment in frozen:
            cls._validate_attachment(attachment)
            occurrence_key = (attachment.message_id_hash, attachment.index)
            previous = by_occurrence.get(occurrence_key)
            if previous is None:
                by_occurrence[occurrence_key] = attachment
                unique.append(attachment)
                continue
            if previous != attachment:
                raise IngestionError("RAW_OCCURRENCE_COLLISION")
        return tuple(unique)

    @staticmethod
    def _attachment_paths(attachment: DownloadedAttachment) -> tuple[Path, Path, Path, Path]:
        day = attachment.message_at.astimezone(BEIJING).date()
        message_path = Path("raw/messages") / day.strftime("%Y/%m/%d") / f"{attachment.message_id_hash}.json"
        occurrence_path = (
            Path("raw/occurrences") / day.strftime("%Y/%m/%d") /
            attachment.message_id_hash / f"{attachment.index}.json"
        )
        blob_path = Path("raw/blobs/sha256") / attachment.sha256[:2] / f"{attachment.sha256}{RawMaterializer._suffix(attachment.filename)}"
        manifest_path = Path("raw/chunks/sha256") / attachment.sha256 / "reassembly.json"
        return message_path, occurrence_path, blob_path, manifest_path

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
        fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def stage(self, root: Path, attachments: Iterable[DownloadedAttachment]) -> StagedRawBatch:
        frozen = self.canonical_attachments(attachments)
        root.mkdir(parents=True, exist_ok=True)
        if root.is_symlink() or any(path.is_symlink() for path in root.rglob("*")):
            raise IngestionError("RAW_PATH_SYMLINK_REJECTED")
        paths: list[str] = []
        manifests: list[str] = []
        hash_list: list[str] = []
        batch_rows: list[dict[str, Any]] = []
        for attachment in frozen:
            if sha256(attachment.payload).hexdigest() != attachment.sha256:
                raise IngestionError("RAW_SOURCE_HASH_MISMATCH")
            message_path, occurrence_path, blob_path, manifest_path = self._attachment_paths(attachment)
            blob_absolute = self._safe_path(root, blob_path)
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
                    self._write_once(self._safe_path(root, part_path), part)
                    object_paths.append(str(part_path))
                    part_hashes.append(sha256(part).hexdigest())
                reassembly_payload = {
                    "schema_version": "kmfa.daily_funds.reassembly.v1",
                    "sha256": attachment.sha256,
                    "original_size_bytes": len(attachment.payload),
                    "chunk_size_bytes": CHUNK_BYTES,
                    "chunks": part_hashes,
                }
                self._write_once(self._safe_path(root, manifest_path), self._json_text(reassembly_payload, code="RAW_MANIFEST_SERIALIZATION_FAILED").encode("utf-8"))
                object_paths.append(str(manifest_path))
                manifests.append(str(manifest_path))
                reassembly = str(manifest_path)
            self._write_once(self._safe_path(root, message_path), self._json_text(attachment.message, code="RAW_MESSAGE_SERIALIZATION_FAILED").encode("utf-8"))
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
            self._write_once(self._safe_path(root, occurrence_path), self._json_text(occurrence, code="RAW_OCCURRENCE_SERIALIZATION_FAILED").encode("utf-8"))
            paths.extend([str(message_path), str(occurrence_path), *object_paths])
            hash_list.append(attachment.sha256)
            batch_rows.append({
                "message_id_hash": attachment.message_id_hash,
                "attachment_index": attachment.index,
                "attachment_sha256": attachment.sha256,
                "occurrence_path": str(occurrence_path),
            })
        batch_rows.sort(key=lambda row: (row["message_id_hash"], row["attachment_index"], row["attachment_sha256"]))
        batch_id = sha256(json.dumps(batch_rows, sort_keys=True).encode("utf-8")).hexdigest()
        batch_path = Path("raw/batches") / f"{batch_id}.json"
        batch = {
            "schema_version": "kmfa.daily_funds.batch.v1",
            "batch_id": batch_id,
            "occurrences": batch_rows,
        }
        self._write_once(self._safe_path(root, batch_path), self._json_text(batch, code="RAW_BATCH_SERIALIZATION_FAILED").encode("utf-8"))
        paths.append(str(batch_path))
        return StagedRawBatch(batch_id, tuple(sorted(set(paths))), tuple(sorted(set(hash_list))), len(frozen), tuple(sorted(set(manifests))))

    @staticmethod
    def reassemble(root: Path, attachment_sha256: str) -> bytes:
        if len(attachment_sha256) != 64 or any(character not in "0123456789abcdef" for character in attachment_sha256):
            raise IngestionError("REASSEMBLY_HASH_MISMATCH")
        manifest_path = RawMaterializer._safe_path(root, Path("raw/chunks/sha256") / attachment_sha256 / "reassembly.json")
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            not isinstance(payload, Mapping)
            or payload.get("schema_version") != "kmfa.daily_funds.reassembly.v1"
            or payload.get("sha256") != attachment_sha256
            or payload.get("chunk_size_bytes") != CHUNK_BYTES
            or not isinstance(payload.get("original_size_bytes"), int)
            or payload["original_size_bytes"] < 0
            or not isinstance(payload.get("chunks"), list)
        ):
            raise IngestionError("REASSEMBLY_MANIFEST_INVALID")
        chunks = []
        for index, expected_sha in enumerate(payload["chunks"]):
            if not isinstance(expected_sha, str) or len(expected_sha) != 64:
                raise IngestionError("REASSEMBLY_MANIFEST_INVALID")
            part = RawMaterializer._safe_path(root, manifest_path.parent.relative_to(root) / f"{index:06d}.part").read_bytes()
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
            cls._validate_attachment(attachment)
            if root.is_symlink():
                raise IngestionError("GIT_READBACK_FAILED")
            message_path, occurrence_path, direct_path, manifest_path = cls._attachment_paths(attachment)
            expected_message = cls._json_text(attachment.message, code="GIT_READBACK_FAILED")
            if cls._safe_path(root, message_path).read_text(encoding="utf-8") != expected_message:
                raise IngestionError("GIT_READBACK_FAILED")
            occurrence = json.loads(cls._safe_path(root, occurrence_path).read_text(encoding="utf-8"))
            if not isinstance(occurrence, Mapping):
                raise IngestionError("GIT_READBACK_FAILED")
            required = {
                "schema_version": "kmfa.daily_funds.occurrence.v1",
                "message_id_hash": attachment.message_id_hash,
                "attachment_index": attachment.index,
                "attachment_sha256": attachment.sha256,
                "attachment_size_bytes": len(attachment.payload),
                "filename": attachment.filename,
                "mime": attachment.mime,
                "family": attachment.family,
                "message_path": str(message_path),
                "message_at": attachment.message_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            }
            if any(occurrence.get(key) != value for key, value in required.items()):
                raise IngestionError("GIT_READBACK_FAILED")
            if len(attachment.payload) <= DIRECT_BLOB_MAX_BYTES:
                if occurrence.get("object_paths") != [str(direct_path)] or occurrence.get("reassembly_manifest") is not None:
                    raise IngestionError("GIT_READBACK_FAILED")
                payload = cls._safe_path(root, direct_path).read_bytes()
            else:
                manifest = json.loads(cls._safe_path(root, manifest_path).read_text(encoding="utf-8"))
                if not isinstance(manifest, Mapping) or not isinstance(manifest.get("chunks"), list):
                    raise IngestionError("GIT_READBACK_FAILED")
                expected_paths = [
                    str(Path("raw/chunks/sha256") / attachment.sha256 / f"{index:06d}.part")
                    for index in range(len(manifest["chunks"]))
                ] + [str(manifest_path)]
                if occurrence.get("object_paths") != expected_paths or occurrence.get("reassembly_manifest") != str(manifest_path):
                    raise IngestionError("GIT_READBACK_FAILED")
                payload = cls.reassemble(root, attachment.sha256)
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

    @staticmethod
    def _is_force_push(args: Sequence[str]) -> bool:
        return bool(args and args[0] == "push" and any(
            argument == "-f" or argument.startswith("--force")
            for argument in args[1:]
        ))

    @staticmethod
    def _is_non_fast_forward(args: Sequence[str], stderr: str) -> bool:
        if not args or args[0] != "push":
            return False
        text = stderr.lower()
        return any(marker in text for marker in (
            "non-fast-forward",
            "non fast forward",
            "fetch first",
            "[rejected]",
        ))

    @staticmethod
    def _git_environment(temp_root: Path, key_path: Path) -> dict[str, str]:
        """Create an isolated Git/SSH process environment for the one writer.

        The deploy key is the sole authentication source.  No host SSH agent,
        global Git config, `known_hosts`, or prompt may silently participate.
        """

        home = temp_root / "git-home"
        home.mkdir(mode=0o700, exist_ok=True)
        passthrough = (
            "PATH", "LANG", "LC_ALL", "TZ", "SSL_CERT_FILE", "SSL_CERT_DIR",
            "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY",
        )
        env = {key: value for key in passthrough if (value := os.environ.get(key))}
        known_hosts = home / "known_hosts"
        ssh_args = (
            "ssh", "-F", "/dev/null", "-i", str(key_path),
            "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", f"UserKnownHostsFile={known_hosts}",
        )
        env.update({
            "HOME": str(home),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "/bin/false",
            "SSH_ASKPASS": "/bin/false",
            "GIT_SSH_COMMAND": " ".join(shlex.quote(argument) for argument in ssh_args),
        })
        return env

    @staticmethod
    def _write_deploy_key(temp_root: Path, encoded_key: str) -> Path:
        key_path = temp_root / "private_db_ed25519"
        try:
            key_path.write_bytes(base64.b64decode(encoded_key, validate=True))
        except (OSError, ValueError) as exc:
            raise IngestionError("GIT_SSH_KEY_WRITE_FAILED") from exc
        key_path.chmod(0o600)
        return key_path

    def _git(self, args: Sequence[str], *, cwd: Path | None = None, env: Mapping[str, str] | None = None) -> str:
        if self._is_force_push(args):
            raise IngestionError("GIT_FORCE_PUSH_FORBIDDEN")
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
            raise IngestionError("GIT_NON_FAST_FORWARD" if self._is_non_fast_forward(args, completed.stderr or "") else "GIT_WRITE_FAILED")
        return completed.stdout.strip()

    @staticmethod
    def _assert_sparse_checkout_scope(repo: Path) -> None:
        """The clone may materialize only the owner-approved sparse path."""

        for path in repo.rglob("*"):
            relative = path.relative_to(repo)
            if relative.parts and relative.parts[0] == ".git":
                continue
            if path.is_symlink() or (path.is_file() and not relative.is_relative_to(SPARSE_PATH)):
                raise IngestionError("GIT_SPARSE_SCOPE_VIOLATION")

    def _assert_staged_scope(self, repo: Path, *, env: Mapping[str, str]) -> None:
        expected_prefix = f"{SPARSE_PATH.as_posix()}/"
        staged_paths = self._git(["diff", "--cached", "--name-only", "--"], cwd=repo, env=env).splitlines()
        if any(path != SPARSE_PATH.as_posix() and not path.startswith(expected_prefix) for path in staged_paths):
            raise IngestionError("GIT_SPARSE_SCOPE_VIOLATION")

    @staticmethod
    def _attachment_sparse_patterns(attachments: Iterable[DownloadedAttachment]) -> tuple[str, ...]:
        """Return the smallest day/hash paths needed for one raw batch.

        Checking out the whole ``daily_funds`` tree makes a nominally sparse
        clone materialise every historic raw object.  That is both unnecessary
        for a new immutable batch and unsafe on the bounded cloud worker disk.
        The writer only needs the four deterministic directories which contain
        each attachment's envelope, occurrence, blob and reassembly manifest.
        """

        directories: set[Path] = set()
        for attachment in attachments:
            for path in RawMaterializer._attachment_paths(attachment):
                directories.add(SPARSE_PATH / path.parent)
        return tuple(f"{path.as_posix()}/" for path in sorted(directories, key=lambda path: path.as_posix()))

    @staticmethod
    def _publication_sparse_patterns(business_date: str) -> tuple[str, ...]:
        return (f"{(SPARSE_PATH / 'publications' / business_date).as_posix()}/",)

    def _clone_sparse(
        self,
        repo: Path,
        *,
        env: Mapping[str, str],
        ref: str,
        patterns: Sequence[str] | None = None,
    ) -> None:
        """Clone only the caller's approved sparse materialisation paths.

        ``patterns=None`` remains the compatibility/default path for callers
        which really need the complete approved tree.  Raw ingestion and
        publication callers always provide a narrow immutable path set.
        """

        selected = tuple(patterns) if patterns is not None else (f"{SPARSE_PATH.as_posix()}/",)
        if not selected:
            raise IngestionError("GIT_SPARSE_SCOPE_VIOLATION")
        sparse_root = SPARSE_PATH.as_posix() + "/"
        if any(not pattern.startswith(sparse_root) for pattern in selected):
            raise IngestionError("GIT_SPARSE_SCOPE_VIOLATION")
        self._git([
            "clone", "--depth=1", "--filter=blob:none", "--sparse", "--no-checkout",
            self.config.private_repo, str(repo),
        ], env=env)
        # Cone mode always includes root-level files.  Non-cone mode is used
        # deliberately so an exact-path writer never checks out unrelated
        # repository material before it handles financial evidence.
        self._git(["sparse-checkout", "set", "--no-cone", *selected], cwd=repo, env=env)
        self._git(["checkout", ref], cwd=repo, env=env)
        self._assert_sparse_checkout_scope(repo)

    def _push_with_single_rebase(self, repo: Path, *, env: Mapping[str, str]) -> None:
        """Retry the expected main race once, never with a force push."""

        try:
            self._git(["push", "origin", f"HEAD:{self.config.private_branch}"], cwd=repo, env=env)
        except IngestionError as exc:
            if exc.code != "GIT_NON_FAST_FORWARD":
                raise
            self._git(["fetch", "origin", self.config.private_branch], cwd=repo, env=env)
            self._git(["rebase", f"origin/{self.config.private_branch}"], cwd=repo, env=env)
            self._git(["push", "origin", f"HEAD:{self.config.private_branch}"], cwd=repo, env=env)

    def _readback_sparse_root(
        self,
        temp_root: Path,
        *,
        env: Mapping[str, str],
        commit_sha: str,
        patterns: Sequence[str] | None = None,
    ) -> Path:
        """Reopen the pushed commit through a new sparse clone.

        ``ls-remote`` only proves that a ref points at a SHA.  This extra clone
        proves that the actual objects which will feed R2/parser can be fetched
        and opened from GitHub after the push succeeds (F-008).
        """

        repo = temp_root / "private-db-readback"
        # Clone first on the permitted branch so sparse setup remains identical
        # to the writer, then detach at the pushed SHA for the actual readback.
        self._clone_sparse(repo, env=env, ref=self.config.private_branch, patterns=patterns)
        self._git(["checkout", "--detach", commit_sha], cwd=repo, env=env)
        return repo / SPARSE_PATH

    def _readback_attachments(
        self,
        temp_root: Path,
        *,
        env: Mapping[str, str],
        commit_sha: str,
        attachments: Iterable[DownloadedAttachment],
        patterns: Sequence[str],
    ) -> tuple[DownloadedAttachment, ...]:
        root = self._readback_sparse_root(temp_root, env=env, commit_sha=commit_sha, patterns=patterns)
        return tuple(RawMaterializer.readback_attachment(root, attachment) for attachment in attachments)

    def persist(self, attachments: Iterable[DownloadedAttachment]) -> GitCommit:
        self.config.validate(include_storage=False)
        frozen_attachments = RawMaterializer.canonical_attachments(attachments)
        sparse_patterns = self._attachment_sparse_patterns(frozen_attachments)
        if not self.config.state_dir.exists():
            self.config.state_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="daily-funds-git-", dir=self.config.state_dir) as temp:
            temp_root = Path(temp)
            key_path = self._write_deploy_key(temp_root, self.config.git_ssh_key_b64)
            env = self._git_environment(temp_root, key_path)
            repo = temp_root / "private-db"
            self._clone_sparse(repo, env=env, ref=self.config.private_branch, patterns=sparse_patterns)
            self._git(["config", "user.name", "kmfa-daily-funds-writer"], cwd=repo, env=env)
            self._git(["config", "user.email", "kmfa-daily-funds@localhost"], cwd=repo, env=env)
            materializer = RawMaterializer()
            staged = materializer.stage(repo / SPARSE_PATH, frozen_attachments)
            self._git(["add", "--sparse", "--", str(SPARSE_PATH)], cwd=repo, env=env)
            self._assert_staged_scope(repo, env=env)
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
                self._push_with_single_rebase(repo, env=env)
            commit_sha = self._git(["rev-parse", "HEAD"], cwd=repo, env=env)
            remote_head = self._git(["ls-remote", "origin", f"refs/heads/{self.config.private_branch}"], cwd=repo, env=env).split()
            if not remote_head or remote_head[0] != commit_sha:
                raise IngestionError("GIT_READBACK_FAILED")
            verified_attachments = self._readback_attachments(
                temp_root,
                env=env,
                commit_sha=commit_sha,
                attachments=frozen_attachments,
                patterns=sparse_patterns,
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
        sparse_patterns = self._publication_sparse_patterns(business_date)
        with tempfile.TemporaryDirectory(prefix="daily-funds-publication-", dir=self.config.state_dir) as temp:
            temp_root = Path(temp)
            key_path = self._write_deploy_key(temp_root, self.config.git_ssh_key_b64)
            env = self._git_environment(temp_root, key_path)
            repo = temp_root / "private-db"
            self._clone_sparse(repo, env=env, ref=self.config.private_branch, patterns=sparse_patterns)
            self._git(["config", "user.name", "kmfa-daily-funds-writer"], cwd=repo, env=env)
            self._git(["config", "user.email", "kmfa-daily-funds@localhost"], cwd=repo, env=env)
            target = RawMaterializer._safe_path(
                repo / SPARSE_PATH,
                Path("publications") / business_date / f"{publication_id}.json",
            )
            payload = json.dumps(publication, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            if target.exists() and target.read_text(encoding="utf-8") != payload:
                raise IngestionError("PUBLICATION_ID_COLLISION")
            RawMaterializer._write_once(target, payload.encode("utf-8"))
            self._git(["add", "--sparse", "--", str(SPARSE_PATH)], cwd=repo, env=env)
            self._assert_staged_scope(repo, env=env)
            changed = bool(self._git(["status", "--porcelain"], cwd=repo, env=env))
            if changed:
                self._git(["commit", "-m", f"data(kmfa): daily funds publication {publication_id[:12]}"], cwd=repo, env=env)
                self._push_with_single_rebase(repo, env=env)
            commit_sha = self._git(["rev-parse", "HEAD"], cwd=repo, env=env)
            remote = self._git(["ls-remote", "origin", f"refs/heads/{self.config.private_branch}"], cwd=repo, env=env).split()
            if not remote or remote[0] != commit_sha:
                raise IngestionError("GIT_READBACK_FAILED")
            readback_root = self._readback_sparse_root(
                temp_root,
                env=env,
                commit_sha=commit_sha,
                patterns=sparse_patterns,
            )
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
            key_path = self._write_deploy_key(temp_root, self.config.git_ssh_key_b64)
            env = self._git_environment(temp_root, key_path)
            repo = temp_root / "private-db"
            self._clone_sparse(repo, env=env, ref=self.config.private_branch)
            bundle = temp_root / "daily-funds.bundle"
            self._git(["bundle", "create", str(bundle), "HEAD"], cwd=repo, env=env)
            payload = bundle.read_bytes()
            if not payload:
                raise IngestionError("GIT_BUNDLE_EMPTY")
            return payload
