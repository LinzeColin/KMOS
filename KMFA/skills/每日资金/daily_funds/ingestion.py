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
import select
import shlex
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from .config import DailyFundsConfig
from .state import RuntimeState

UTC = timezone.utc
BEIJING = ZoneInfo("Asia/Shanghai")

SPARSE_PATH = Path("Private-KMDatabase/KMFA/daily_funds")
DIRECT_BLOB_MAX_BYTES = 94_371_840
CHUNK_BYTES = 48 * 1024 * 1024
ALLOWED_SUFFIXES = frozenset({".csv", ".txt", ".xls", ".xlsx", ".xlsm"})
_DWS_RESOURCE_TYPES = frozenset({"mediaId", "fileId"})
_MEDIA_ID_RE = re.compile(r"mediaId=([^\)\s]+)")
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_DEVICE_CODE_RE = re.compile(
    r"(?:user[ _-]?code|authorization[ _-]?code|授权码)\s*[:：]\s*([A-Za-z0-9][A-Za-z0-9-]{2,63})",
    re.IGNORECASE,
)
_DEVICE_URL_RE = re.compile(r"https://[^\s<>\"']+", re.IGNORECASE)

# A history-probe receipt may report only this bounded protocol classification
# when a terminal DWS page omits the explicit message list required by DF-002.
# It deliberately contains neither a provider field name nor any source value.
DWS_RECORD_LIST_SHAPES = frozenset({
    "NOT_OBSERVED",
    "NO_DIRECT_LIST",
    "UNRECOGNIZED_DIRECT_LIST",
})

# Git and SSH stderr can contain remote paths, account diagnostics or other
# implementation detail.  A scheduled worker must not collapse every write
# failure into one opaque result, but it also must never forward that stderr
# into a status/publication surface.  These fixed tokens identify only the
# safe pipeline stage that needs attention.
_ARCHIVE_WRITE_FAILURE_CODES = frozenset({
    "GIT_ARCHIVE_PREPARE_FAILED",
    "GIT_ARCHIVE_STAGE_FAILED",
    "GIT_ARCHIVE_COMMIT_FAILED",
    "GIT_ARCHIVE_PUSH_FAILED",
    "GIT_ARCHIVE_REBASE_FAILED",
    "GIT_ARCHIVE_VERIFY_FAILED",
    "GIT_ARCHIVE_READBACK_FAILED",
})


class IngestionError(RuntimeError):
    def __init__(self, code: str, *, record_list_shape: str = "NOT_OBSERVED"):
        if record_list_shape not in DWS_RECORD_LIST_SHAPES:
            raise ValueError("invalid DWS record-list shape")
        self.code = code
        # This is intentionally a finite, values-free protocol fact.  It is
        # never interpolated into the exception text or any runtime log.
        self.record_list_shape = record_list_shape
        super().__init__(code)


@dataclass(frozen=True)
class DwsPage:
    messages: tuple[dict[str, Any], ...]
    next_cursor: str | None
    has_more: bool


@dataclass(frozen=True)
class DwsGroupHistoryProbe:
    """Values-free summary of the official exact-group history reader.

    The beta DWS shortcut owns the provider's millisecond cursor conversion
    internally. This slice keeps no message, cursor, timestamp, or selector
    from that command; the fixed control probe needs only bounded page facts.
    """

    pages_fetched: int
    has_more: bool


@dataclass(frozen=True)
class DwsAuthStatus:
    authenticated: bool
    refresh_token_valid: bool


@dataclass(frozen=True)
class DwsDevicePrompt:
    """The short-lived, owner-visible half of a DWS device authorization.

    This is deliberately *not* a token, refresh credential, group identifier,
    or durable status record.  The auth broker holds it only in its private
    control hand-off long enough for the Access-protected owner UI to display
    it.  It must never be sent to a cron log or a publication/status surface.
    """

    authorization_url: str
    user_code: str


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
class PersistedRawAttachment:
    """A repeated source occurrence, before raw metadata is re-opened.

    The overlap journal has only this immutable identity.  Filename, family,
    MIME and bytes must come from the fresh private-Git readback rather than
    from a DWS listing, because embedded-media listings often omit a filename.
    """

    message: dict[str, Any]
    message_id: str
    message_id_hash: str
    message_at: datetime
    index: int
    sha256: str


@dataclass(frozen=True)
class StagedRawBatch:
    batch_id: str
    paths: tuple[str, ...]
    attachment_hashes: tuple[str, ...]
    occurrences: int
    reassembly_manifest_paths: tuple[str, ...]


@dataclass(frozen=True)
class ReopenedRawEvidence:
    """Read-only evidence for an overlap assembled from prior raw batches.

    A later DWS overlap can legitimately return occurrences that were first
    archived in different pages and therefore different immutable batch
    manifests.  It is deliberately not represented as a new raw batch in
    Private-Database.
    """

    source_batch_paths: tuple[str, ...]
    attachment_hashes: tuple[str, ...]
    occurrences: int


@dataclass(frozen=True)
class GitCommit:
    commit_sha: str
    staged: StagedRawBatch | ReopenedRawEvidence
    # These bytes have been re-opened from a fresh sparse clone at
    # ``commit_sha``.  Downstream R2, parsing and reconciliation must consume
    # this list rather than the transient DWS download buffer.
    verified_attachments: tuple[DownloadedAttachment, ...] = ()


@dataclass(frozen=True)
class RawArchiveAudit:
    """Read-only proof for the currently acquired private raw archive.

    The audit intentionally carries only a commit identity, counts and the
    freshly re-opened attachments in process memory.  Callers may create
    values-free parser-capability receipts from those bytes, but this object
    is never a publication or an alternative source of financial facts.
    """

    commit_sha: str
    verified_attachments: tuple[DownloadedAttachment, ...]
    occurrence_count: int
    batch_count: int
    batch_occurrence_references: int


@dataclass(frozen=True)
class _RawArchiveOccurrence:
    """A validated raw-occurrence manifest before its envelope is reopened."""

    occurrence_path: str
    message_path: str
    message_at: datetime
    message_id_hash: str
    index: int
    sha256: str


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
    # DWS can return a naïve Beijing-local ``createTime``.
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
    # The pinned DWS runtime represents media attachments inside the message text as
    # ``mediaId=<opaque-id>`` rather than in a top-level attachment array.
    # Keep this narrowly scoped to the documented media token and never walk
    # quoted-message JSON, which would turn an old quoted attachment into a
    # fresh occurrence.
    return [{"mediaId": match.group(1)} for match in _MEDIA_ID_RE.finditer(content)]


def _attachment_resource(attachment: Mapping[str, Any]) -> tuple[str, str] | None:
    """Return one supported DWS resource identity without guessing its type.

    The exact-group history endpoint emits ``resourceRefs`` with an explicit
    ``type``/``resourceId`` pair.  Older message representations retain only a
    ``mediaId`` token.  A ``fileId`` must stay a file resource: coercing it to
    media loses the provider's download contract and silently excludes native
    account or transaction workbooks from the private raw archive.
    """

    declared_type = _message_field(attachment, ("type", "resourceType", "resource_type"))
    if declared_type is not None:
        if declared_type not in _DWS_RESOURCE_TYPES:
            return None
        resource_id = _message_field(
            attachment,
            ("resourceId", "resource_id", declared_type, declared_type.lower()),
        )
        return (declared_type, resource_id) if resource_id else None

    file_id = _message_field(attachment, ("fileId", "file_id"))
    if file_id:
        return "fileId", file_id
    media_id = _message_field(attachment, ("mediaId", "media_id", "resourceId", "resource_id"))
    if media_id:
        # Untyped historical resource IDs are the legacy media representation.
        return "mediaId", media_id
    return None


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


def _dws_attachment_download_failure_code(
    *values: object,
    fallback: str = "ATTACHMENT_DOWNLOAD_FAILED",
) -> str:
    """Reduce a media-download failure to a finite attachment-stage code.

    The download command has the same OAuth and DingTalk authorization
    semantics as the history collector, but its repair surface is different:
    a group-history permission and an attachment-media permission must not be
    presented as the same action item.  The underlying diagnostic is examined
    only in process memory and is never retained, logged, or returned.
    """

    code = _dws_history_failure_code(*values, fallback=fallback)
    if code == "DWS_HISTORY_PERMISSION_DENIED":
        return "DWS_ATTACHMENT_PERMISSION_DENIED"
    if code == "DWS_HISTORY_ARGUMENT_INVALID":
        return "ATTACHMENT_DOWNLOAD_ARGUMENT_INVALID"
    return code


def _strip_dws_terminal_style(value: str) -> str:
    """Remove only ANSI terminal decoration before parsing a device prompt."""

    return _ANSI_ESCAPE_RE.sub("", value)


def _trusted_dws_authorization_url(value: str) -> str | None:
    """Accept only an HTTPS DingTalk authorization URL from the pinned CLI.

    The control-plane consumer renders this as an owner-clickable link.  A
    malformed or unexpected URL must not turn a CLI-output parsing regression
    into an open redirect from the protected KMFA page.
    """

    candidate = value.rstrip(".,;:)]}")
    try:
        parsed = urlsplit(candidate)
        hostname = (parsed.hostname or "").lower()
    except ValueError:
        return None
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or not (hostname == "dingtalk.com" or hostname.endswith(".dingtalk.com")
                or hostname == "dingtalk.cn" or hostname.endswith(".dingtalk.cn"))
        or len(candidate) > 2_048
    ):
        return None
    return candidate


def _parse_dws_device_prompt(output: str) -> DwsDevicePrompt | None:
    """Extract the device-flow prompt emitted by DWS without retaining output.

    The pinned DWS runtime renders a short authorization URL and a user code
    to its device-flow output stream.  Depending on the runtime locale the
    code label is either ``授权码``, ``user code``, or ``authorization code``.
    A complete URI is rendered afterwards when available, so the last trusted
    URL is preferred: that lets the owner open it directly instead of copying
    a code.  This parser intentionally returns no diagnostic text on mismatch;
    command output could contain OAuth, identity, or upstream error material.
    """

    clean = _strip_dws_terminal_style(output)
    code_match = _DEVICE_CODE_RE.search(clean)
    if code_match is None:
        return None
    urls = [
        trusted
        for match in _DEVICE_URL_RE.finditer(clean)
        if (trusted := _trusted_dws_authorization_url(match.group(0))) is not None
    ]
    if not urls:
        return None
    return DwsDevicePrompt(authorization_url=urls[-1], user_code=code_match.group(1))


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

    candidates: list[tuple[Mapping[str, Any], tuple[tuple[Mapping[str, Any], str], ...]]] = []

    def visit(
        value: object,
        ancestors: tuple[tuple[Mapping[str, Any], str], ...] = (),
    ) -> None:
        if isinstance(value, Mapping):
            if "hasMore" in value or "has_more" in value:
                candidates.append((value, ancestors))
            for key, child in value.items():
                if isinstance(child, Mapping):
                    visit(child, ancestors + ((value, str(key)),))

    visit(payload)
    for candidate, ancestors in candidates:
        raw_more = candidate.get("hasMore", candidate.get("has_more"))
        if not isinstance(raw_more, bool):
            continue
        records = _explicit_dws_page_records(candidate)
        if records is None:
            # Some official adapters keep the opaque cursor and ``hasMore``
            # under a named pagination child while retaining the explicit
            # result list in its immediate envelope.  Pair only those finite
            # pagination-wrapper shapes; do not recursively scan arbitrary
            # message payloads or quoted/forwarded content for a list.
            for ancestor, child_key in reversed(ancestors):
                if child_key not in _DWS_PAGINATION_CONTAINER_KEYS:
                    continue
                records = _explicit_dws_page_records(ancestor)
                if records is not None:
                    break
        if records is None:
            # A terminal page is only a proven zero-result page when DWS
            # explicitly supplies an empty records list.  ``hasMore: false``
            # alone is ambiguous: some DWS query variants omit the records
            # field even when the selected conversation has history.  Never
            # turn that shape into SOURCE_MATCH_ZERO or advance a cursor.
            if raw_more is False:
                raise IngestionError(
                    "DWS_PAGE_RECORDS_MISSING",
                    record_list_shape=_record_list_shape(candidate),
                )
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


_DWS_EXPLICIT_MESSAGE_LIST_KEYS = (
    "messages",
    "items",
    "records",
    "list",
    # ``im/search_messages`` emits this official DWS field in some deployed
    # versions.  It is deliberately explicit rather than a guessed alias.
    "messageList",
    # The official DWS search adapter also accepts a direct raw ``result``
    # array (without the separate ``success`` business envelope).  This is an
    # explicit list shape, not a fallback that infers emptiness from hasMore.
    "result",
)


# Page metadata is sometimes nested independently from an explicit list.
# These are protocol wrapper names, not data-field guesses; any other nested
# ``hasMore`` remains unpaired and fails closed.
_DWS_PAGINATION_CONTAINER_KEYS = frozenset({
    "page",
    "pageData",
    "pageInfo",
    "pageResult",
    "pagination",
    "paging",
})


def _record_list_shape(candidate: Mapping[str, Any]) -> str:
    """Classify a record-less terminal page without retaining source data.

    The probe uses this only after the normal explicit-list parser has failed.
    It inspects the finite page envelope scopes already permitted by that
    parser and emits no field name, list size, value, identifier, cursor, or
    message content.  It must never change the collector's fail-closed result.
    """

    for container in (candidate, candidate.get("data"), candidate.get("result")):
        if not isinstance(container, Mapping):
            continue
        if any(isinstance(value, list) for value in container.values()):
            return "UNRECOGNIZED_DIRECT_LIST"
    return "NO_DIRECT_LIST"


def _explicit_dws_page_records(candidate: Mapping[str, Any]) -> list[Any] | None:
    """Return only an explicitly represented DWS search result list.

    The underlying official ``im/search_messages`` adapter documents both a
    direct ``messageList`` and a grouped ``conversationMessagesList`` shape.
    It may also nest the direct list under ``data`` or ``result``.  We accept
    those finite, documented shapes only.  In particular, an empty list is a
    real terminal page; a missing list is still ambiguous and returns ``None``.
    """

    for container in (candidate, candidate.get("data"), candidate.get("result")):
        if not isinstance(container, Mapping):
            continue
        for key in _DWS_EXPLICIT_MESSAGE_LIST_KEYS:
            value = container.get(key)
            if isinstance(value, list):
                return value
        if isinstance(container.get("data"), list):
            return container["data"]
        grouped = container.get("conversationMessagesList")
        if isinstance(grouped, list):
            messages: list[Any] = []
            for group in grouped:
                if not isinstance(group, Mapping):
                    continue
                group_messages = group.get("messages")
                if not isinstance(group_messages, list):
                    continue
                group_conversation_id = group.get("openConversationId")
                for raw_message in group_messages:
                    if not isinstance(raw_message, Mapping):
                        messages.append(raw_message)
                        continue
                    message = dict(raw_message)
                    if (
                        "openConversationId" not in message
                        and isinstance(group_conversation_id, str)
                        and group_conversation_id
                    ):
                        message["openConversationId"] = group_conversation_id
                    messages.append(message)
            return messages
    return None


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

    def _run_dws(
        self,
        command: list[str],
        *,
        operation: str,
        timeout: int,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        try:
            kwargs: dict[str, Any] = {
                "capture_output": True,
                "text": True,
                "check": False,
                "env": self._environment(),
                "timeout": timeout,
            }
            if cwd is not None:
                kwargs["cwd"] = str(cwd)
            return self._runner(
                command,
                **kwargs,
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

    def bootstrap_device_auth_with_prompt(
        self,
        prompt_sink: Callable[[DwsDevicePrompt], None],
        *,
        cancel_requested: Callable[[], bool],
        max_wait_seconds: int = 660,
    ) -> str:
        """Run one cloud-only device flow and surface only its short-lived prompt.

        The normal bootstrap command keeps stdout/stderr attached to an
        operator terminal.  The Access-protected broker has no terminal, so
        it captures that stream in memory, extracts only the official
        ``verificationUri``/``userCode`` prompt, and discards the rest.  It
        never writes raw CLI output to a file, journal, status projection, or
        cron log.  ``cancel_requested`` is checked at sub-second cadence so a
        stale owner request cannot keep a device flow alive in the background.
        """

        if max_wait_seconds < 60 or max_wait_seconds > 900:
            raise IngestionError("DWS_AUTH_BOOTSTRAP_TIMEOUT_INVALID")
        self.config.validate_dws_bootstrap()
        if cancel_requested():
            raise IngestionError("DWS_AUTH_BOOTSTRAP_CANCELLED")
        status = self._auth_status()
        if status.authenticated and status.refresh_token_valid:
            self._auth_ready = True
            self._record_network_event("AUTH_BOOTSTRAP", "ALREADY_READY")
            return "ALREADY_READY"

        self._record_network_event("AUTH_BOOTSTRAP", "STARTED")
        command = [
            self.config.dws_bin,
            "auth",
            "login",
            "--device",
            "--no-browser",
            "--yes",
            "--format",
            "json",
        ]
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=self._environment(),
            )
        except OSError as exc:
            self._record_network_event("AUTH_BOOTSTRAP", "UNAVAILABLE")
            raise IngestionError("DWS_AUTH_BOOTSTRAP_UNAVAILABLE") from exc

        started = time.monotonic()
        transcript = ""
        emitted: tuple[str, str] | None = None

        def absorb(value: str) -> None:
            nonlocal transcript, emitted
            if not value:
                return
            # Keep only a small rolling parse buffer in memory.  It is never
            # persisted, logged, raised, or returned to the caller.
            transcript = (transcript + _strip_dws_terminal_style(value))[-12_288:]
            prompt = _parse_dws_device_prompt(transcript)
            if prompt is None:
                return
            marker = (prompt.authorization_url, prompt.user_code)
            if marker != emitted:
                prompt_sink(prompt)
                emitted = marker

        def stop_process() -> None:
            if process.poll() is not None:
                return
            try:
                process.terminate()
                process.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    process.kill()
                    process.wait(timeout=5)
                except (OSError, subprocess.TimeoutExpired):
                    pass

        try:
            while process.poll() is None:
                if cancel_requested():
                    stop_process()
                    self._record_network_event("AUTH_BOOTSTRAP", "CANCELLED")
                    raise IngestionError("DWS_AUTH_BOOTSTRAP_CANCELLED")
                if time.monotonic() - started >= max_wait_seconds:
                    stop_process()
                    self._record_network_event("AUTH_BOOTSTRAP", "EXPIRED")
                    raise IngestionError("DWS_AUTH_BOOTSTRAP_EXPIRED")
                if process.stdout is None:
                    stop_process()
                    self._record_network_event("AUTH_BOOTSTRAP", "FAILED")
                    raise IngestionError("DWS_AUTH_BOOTSTRAP_OUTPUT_UNAVAILABLE")
                ready, _, _ = select.select([process.stdout], [], [], 0.25)
                if ready:
                    absorb(process.stdout.readline())
            if process.stdout is not None:
                try:
                    remaining, _ = process.communicate(timeout=2)
                except subprocess.TimeoutExpired:
                    stop_process()
                    self._record_network_event("AUTH_BOOTSTRAP", "FAILED")
                    raise IngestionError("DWS_AUTH_BOOTSTRAP_OUTPUT_UNAVAILABLE")
                absorb(remaining)
            if process.returncode != 0:
                self._record_network_event("AUTH_BOOTSTRAP", "FAILED")
                raise IngestionError("DWS_AUTH_BOOTSTRAP_FAILED")
        finally:
            # A failed parser or cancellation must never leave a live DWS
            # child behind after the broker loop moves on to another request.
            stop_process()

        status = self._auth_status()
        if not (status.authenticated and status.refresh_token_valid):
            self._record_network_event("AUTH_BOOTSTRAP", "AUTH_REQUIRED")
            raise IngestionError("DWS_AUTH_REQUIRED")
        self._auth_ready = True
        self._record_network_event("AUTH_BOOTSTRAP", "OK")
        return "OK"

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

    def verify_exact_group_scope(self) -> None:
        """Prove that this DWS identity can resolve the configured group.

        This is a values-free control preflight for the one-off history probe,
        not an alternate collection source.  It calls the pinned DWS
        ``conversation-info`` read command with the same configured group ID,
        retains no response field, and does not alter the primary
        ``search-advanced --conversation-ids`` collector.  A successful
        command is the upstream CLI's own validation contract for a
        conversation ID; anything else fails closed before a record-less
        search page can be misdiagnosed as an empty group.
        """

        self.ensure_authenticated()
        command = [
            self.config.dws_bin,
            "chat",
            "conversation-info",
            "--group",
            self.config.group_id,
            "--format",
            "json",
        ]
        try:
            completed = self._run_dws(
                command,
                operation="HISTORY_GROUP_SCOPE",
                timeout=90,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise IngestionError("DWS_HISTORY_GROUP_SCOPE_UNAVAILABLE") from exc
        if completed.returncode != 0:
            code = _dws_history_failure_code(
                completed.stdout,
                completed.stderr,
                fallback="DWS_HISTORY_GROUP_SCOPE_UNVERIFIABLE",
            )
            self._record_network_event("HISTORY_GROUP_SCOPE", code)
            raise IngestionError(code)
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            self._record_network_event("HISTORY_GROUP_SCOPE", "INVALID")
            raise IngestionError("DWS_HISTORY_GROUP_SCOPE_UNVERIFIABLE") from exc
        if not isinstance(payload, Mapping):
            self._record_network_event("HISTORY_GROUP_SCOPE", "INVALID")
            raise IngestionError("DWS_HISTORY_GROUP_SCOPE_UNVERIFIABLE")
        # DWS normally converts this business envelope into a non-zero exit,
        # but keep the caller fail-closed if a future CLI returns it on stdout.
        if payload.get("success") is False:
            code = _dws_history_failure_code(
                payload,
                fallback="DWS_HISTORY_GROUP_SCOPE_UNVERIFIABLE",
            )
            self._record_network_event("HISTORY_GROUP_SCOPE", code)
            raise IngestionError(code)
        # The response is intentionally discarded.  Retaining even its
        # metadata would turn a probe-only source-scope check into a new data
        # surface; successful JSON execution is the only evidence recorded.
        self._record_network_event("HISTORY_GROUP_SCOPE", "OK")

    def _group_history_v2_payload(
        self,
        start: datetime,
        end: datetime,
        *,
        page_limit: int,
        operation: str,
        unavailable_code: str,
        failed_code: str,
        invalid_code: str,
        timeout: int,
    ) -> Mapping[str, Any]:
        """Read a bounded exact-group ledger from the official DWS shortcut.

        ``+chat-messages`` owns the provider's millisecond continuation
        internally.  This helper deliberately returns its in-memory typed
        ledger only to the caller that can prove completion; no provider
        cursor, message, selector or diagnostics are recorded in state/logs.
        """

        start = start.astimezone(UTC)
        end = end.astimezone(UTC)
        if start >= end or not 1 <= page_limit <= 500:
            self._record_network_event(operation, "INVALID")
            raise IngestionError("DWS_HISTORY_WINDOW_INVALID")
        self.ensure_authenticated()
        command = [
            self.config.dws_bin,
            "chat",
            "+chat-messages",
            "--group",
            self.config.group_id,
            "--start",
            start.isoformat(),
            "--end",
            end.isoformat(),
            "--order",
            "asc",
            # The shortcut's reviewed full-ledger mode follows only the
            # provider's authoritative millisecond cursor.  It never derives
            # a continuation from projected second-precision createTime.
            "--limit",
            "100",
            "--page-all",
            "--page-limit",
            str(page_limit),
            "--format",
            "json",
        ]
        try:
            completed = self._run_dws(command, operation=operation, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise IngestionError(unavailable_code) from exc
        if completed.returncode != 0:
            code = _dws_history_failure_code(
                completed.stdout,
                completed.stderr,
                fallback=failed_code,
            )
            self._record_network_event(operation, code)
            raise IngestionError(code)
        try:
            payload = _unwrap_dws_history_payload(json.loads(completed.stdout))
        except (IngestionError, json.JSONDecodeError) as exc:
            if isinstance(exc, IngestionError):
                self._record_network_event(operation, exc.code)
                raise
            self._record_network_event(operation, "INVALID")
            raise IngestionError(invalid_code) from exc
        if not isinstance(payload, Mapping):
            self._record_network_event(operation, "INVALID")
            raise IngestionError(invalid_code)
        return payload

    def collect_group_history_v2(self, start: datetime, end: datetime) -> DwsPage:
        """Return one complete exact-group window or fail before persistence.

        This is the production fallback for a DWS ``search-advanced`` page
        that omits its required explicit record list.  Unlike a timestamp
        pagination workaround, the official shortcut follows the provider's
        own millisecond continuation while collecting the entire requested
        range.  A page cap, partial ledger, failure ledger, unknown
        pagination flag, or source-identity loss is fatal; callers receive a
        terminal page only after the whole requested range is complete.
        """

        payload = self._group_history_v2_payload(
            start,
            end,
            page_limit=500,
            operation="HISTORY_GROUP_V2_COLLECT",
            unavailable_code="DWS_GROUP_HISTORY_COLLECT_UNAVAILABLE",
            failed_code="DWS_GROUP_HISTORY_COLLECT_FAILED",
            invalid_code="DWS_GROUP_HISTORY_COLLECT_INVALID",
            timeout=720,
        )
        messages = payload.get("messages")
        pages_fetched = payload.get("pagesFetched")
        count = payload.get("count")
        has_more = payload.get("hasMore")
        complete = payload.get("complete")
        pagination_known = payload.get("paginationKnown")
        failed_count = payload.get("failedCount")
        failures = payload.get("failures")
        partial = payload.get("partial")
        truncated_by_page_limit = payload.get("truncatedByPageLimit")
        truncated_by_result_limit = payload.get("truncatedByResultLimit")
        stop_reason = payload.get("stopReason")
        if (
            not isinstance(messages, list)
            or any(not isinstance(message, Mapping) for message in messages)
            or isinstance(pages_fetched, bool)
            or not isinstance(pages_fetched, int)
            or not 1 <= pages_fetched <= 500
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count != len(messages)
            or not isinstance(has_more, bool)
            or not isinstance(complete, bool)
            or not isinstance(failed_count, int)
            or isinstance(failed_count, bool)
            or not isinstance(failures, list)
            or not isinstance(partial, bool)
            or not isinstance(truncated_by_page_limit, bool)
            or not isinstance(truncated_by_result_limit, bool)
            or not isinstance(stop_reason, str)
        ):
            self._record_network_event("HISTORY_GROUP_V2_COLLECT", "INVALID")
            raise IngestionError("DWS_GROUP_HISTORY_COLLECT_INVALID")
        if (
            complete is not True
            or has_more is not False
            or pagination_known is not True
            or failed_count != 0
            or failures
            or partial
            or truncated_by_page_limit
            or truncated_by_result_limit
            or stop_reason not in {"source_complete", "range_end"}
        ):
            self._record_network_event("HISTORY_GROUP_V2_COLLECT", "INCOMPLETE")
            raise IngestionError("DWS_GROUP_HISTORY_COLLECT_INCOMPLETE")

        normalized: list[dict[str, Any]] = []
        for message in messages:
            # The shortcut exposes a stable, deliberately narrow projection.
            # Preserve it verbatim and add only compatibility aliases needed
            # by the existing raw attachment/download gate.  A missing or
            # different group/sender identity cannot be safely filtered and
            # therefore fails the entire source window.
            canonical = dict(message)
            conversation_id = _message_field(
                canonical,
                ("openConversationId", "conversationId", "conversation_id"),
            )
            sender_id = _message_field(
                canonical,
                ("senderOpenDingTalkId", "sender_open_dingtalk_id", "senderId", "sender_id"),
            )
            if conversation_id != self.config.group_id:
                self._record_network_event("HISTORY_GROUP_V2_COLLECT", "SOURCE_INVALID")
                raise IngestionError("AMBIGUOUS_SOURCE")
            canonical["openConversationId"] = conversation_id
            # System rows can have no stable sender identity.  They cannot be
            # candidates unless they advertise one of the allowed document
            # families; a candidate without that identity is ambiguous and
            # must close the entire source window rather than be skipped.
            if not sender_id:
                if _family(canonical) is not None:
                    self._record_network_event("HISTORY_GROUP_V2_COLLECT", "SOURCE_INVALID")
                    raise IngestionError("AMBIGUOUS_SOURCE")
            else:
                canonical["senderOpenDingTalkId"] = sender_id
            message_id = _message_field(
                canonical,
                ("openMessageId", "messageId", "message_id", "id"),
            )
            if message_id:
                canonical["openMessageId"] = message_id

            resource_refs = canonical.get("resourceRefs")
            if resource_refs is not None:
                if not isinstance(resource_refs, list):
                    self._record_network_event("HISTORY_GROUP_V2_COLLECT", "INVALID")
                    raise IngestionError("DWS_GROUP_HISTORY_COLLECT_INVALID")
                attachments: list[dict[str, Any]] = []
                for resource in resource_refs:
                    if not isinstance(resource, Mapping):
                        self._record_network_event("HISTORY_GROUP_V2_COLLECT", "INVALID")
                        raise IngestionError("DWS_GROUP_HISTORY_COLLECT_INVALID")
                    source = _attachment_resource(resource)
                    if source is None:
                        # DWS can add unrelated resource types over time.  They
                        # are not silently reclassified as an attachment that
                        # this slice knows how to download; supported native
                        # files and media are retained below.
                        continue
                    resource_type, resource_id = source
                    attachments.append({"type": resource_type, "resourceId": resource_id})
                if attachments:
                    canonical["attachments"] = attachments
            normalized.append(canonical)

        self._record_network_event("HISTORY_GROUP_V2_COLLECT", "OK")
        return DwsPage(messages=tuple(normalized), next_cursor=None, has_more=False)

    def probe_group_history_v2(
        self,
        start: datetime,
        end: datetime,
    ) -> DwsGroupHistoryProbe:
        """Exercise DWS's exact-group reader without retaining source data.

        DWS v1.0.58-beta.1 added ``+chat-messages`` for a single group. Its
        own tested implementation follows the authoritative millisecond
        ``nextCursor`` by passing the derived RFC3339Nano boundary to the
        lower message-list API, so this caller must not reconstruct a cursor
        from projected message timestamps. The command is capped at two pages
        and its stdout is parsed only into this finite control result.
        """

        payload = self._group_history_v2_payload(
            start,
            end,
            page_limit=2,
            operation="HISTORY_GROUP_V2",
            unavailable_code="DWS_GROUP_HISTORY_PROBE_UNAVAILABLE",
            failed_code="DWS_GROUP_HISTORY_PROBE_FAILED",
            invalid_code="DWS_GROUP_HISTORY_PROBE_INVALID",
            timeout=90,
        )

        # Require the explicit list even though it is deliberately discarded:
        # an omitted list is the exact ambiguity that caused the primary
        # search adapter to fail closed. Empty is valid; absent is not.
        messages = payload.get("messages")
        pages_fetched = payload.get("pagesFetched")
        has_more = payload.get("hasMore")
        complete = payload.get("complete")
        pagination_known = payload.get("paginationKnown")
        failed_count = payload.get("failedCount")
        failures = payload.get("failures")
        if (
            not isinstance(messages, list)
            or isinstance(pages_fetched, bool)
            or not isinstance(pages_fetched, int)
            or pages_fetched not in {1, 2}
            or not isinstance(has_more, bool)
            or not isinstance(complete, bool)
            or pagination_known is not True
            or isinstance(failed_count, bool)
            or failed_count != 0
            or not isinstance(failures, list)
            or failures
        ):
            self._record_network_event("HISTORY_GROUP_V2", "INVALID")
            raise IngestionError("DWS_GROUP_HISTORY_PROBE_INVALID")
        if has_more:
            next_page = payload.get("nextPage")
            next_cursor = next_page.get("nextCursor") if isinstance(next_page, Mapping) else None
            cursor_valid = (
                isinstance(next_cursor, int) and not isinstance(next_cursor, bool) and next_cursor > 0
            ) or (
                isinstance(next_cursor, str)
                and 1 <= len(next_cursor) <= 19
                and next_cursor.isdecimal()
                and int(next_cursor) > 0
            )
            if complete or pages_fetched != 2 or not cursor_valid:
                self._record_network_event("HISTORY_GROUP_V2", "INVALID")
                raise IngestionError("DWS_GROUP_HISTORY_PROBE_INVALID")
        elif not complete:
            self._record_network_event("HISTORY_GROUP_V2", "INVALID")
            raise IngestionError("DWS_GROUP_HISTORY_PROBE_INVALID")
        self._record_network_event("HISTORY_GROUP_V2", "OK")
        return DwsGroupHistoryProbe(pages_fetched=pages_fetched, has_more=has_more)

    def search(
        self,
        start: datetime | None,
        end: datetime | None,
        cursor: str | None,
    ) -> DwsPage:
        """Read one exact-group history page, with either both bounds or none.

        The normal collector always supplies a bounded time range.  The
        values-free control probe may, after a recordless current-window
        result, issue the same exact-group history request without time bounds
        to distinguish that response shape from an unavailable history
        interface.  A caller can never accidentally send a half-bounded query.
        """

        if (start is None) != (end is None):
            self._record_network_event("HISTORY_SEARCH_ADVANCED", "INVALID")
            raise IngestionError("DWS_HISTORY_WINDOW_INVALID")
        if start is not None:
            start = start.astimezone(UTC)
            end = end.astimezone(UTC)
        self.ensure_authenticated()
        # ``search-advanced`` is a history query when constrained to the
        # configured group *and* stable sender.  Unlike ``message list``, it
        # preserves DWS's opaque ``nextCursor`` contract required by the task
        # pack.  This is a narrower remote selector, never a substitute for
        # the local group, sender and document-family gates below: the
        # provider response is independently verified before it can enter the
        # raw writer.
        request_cursor = cursor or "0"
        command = [
            self.config.dws_bin,
            "chat", "message", "search-advanced",
            "--conversation-ids", self.config.group_id,
            # DWS v1.0.57 exposes this server-side selector.  It keeps the
            # query within the configured group source rather than
            # accepting a broader conversation family.
            "--conversation-type", "group",
            "--sender-ids", self.config.sender_id,
        ]
        if start is not None:
            # ``end`` is necessarily present after the paired-bound check.
            assert end is not None
            command.extend(("--start", start.isoformat(), "--end", end.isoformat()))
        command.extend(("--cursor", request_cursor, "--limit", "30", "--format", "json"))
        try:
            completed = self._run_dws(
                command,
                operation="HISTORY_SEARCH_ADVANCED",
                timeout=90,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise IngestionError("DWS_HISTORY_UNAVAILABLE") from exc
        if completed.returncode != 0:
            code = _dws_history_failure_code(completed.stdout, completed.stderr)
            self._record_network_event("HISTORY_SEARCH_ADVANCED", code)
            raise IngestionError(code)
        try:
            payload = json.loads(completed.stdout)
            raw_page = _extract_page(
                _unwrap_dws_history_payload(payload),
                require_next_cursor=True,
            )
        except (IngestionError, json.JSONDecodeError) as exc:
            if isinstance(exc, IngestionError):
                self._record_network_event("HISTORY_SEARCH_ADVANCED", exc.code)
                raise
            self._record_network_event("HISTORY_SEARCH_ADVANCED", "INVALID")
            raise IngestionError("DWS_HISTORY_JSON_INVALID") from exc
        try:
            timestamps = tuple(_message_timestamp(message) for message in raw_page.messages)
        except IngestionError as exc:
            self._record_network_event("HISTORY_SEARCH_ADVANCED", exc.code)
            raise
        if raw_page.has_more and not timestamps:
            self._record_network_event("HISTORY_SEARCH_ADVANCED", "INVALID")
            raise IngestionError("DWS_HISTORY_BOUNDARY_MISSING")
        if raw_page.has_more and raw_page.next_cursor == request_cursor:
            self._record_network_event("HISTORY_SEARCH_ADVANCED", "INVALID")
            raise IngestionError("DWS_HISTORY_CURSOR_STALLED")
        page_messages = (
            tuple(
                message
                for message, timestamp in zip(raw_page.messages, timestamps)
                if start <= timestamp <= end
            )
            if start is not None
            else raw_page.messages
        )
        page = DwsPage(
            messages=page_messages,
            next_cursor=raw_page.next_cursor if raw_page.has_more else None,
            has_more=raw_page.has_more,
        )
        self._record_network_event("HISTORY_SEARCH_ADVANCED", "OK")
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

        The remote request is already constrained to the configured group and
        sender, but its reply remains untrusted.  An unexpected sender is
        ignored and a returned *different group* is a source-integrity failure
        because it contradicts the command's exact conversation ID.
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

    def quarantine_messages(self, page: DwsPage) -> tuple[dict[str, Any], ...]:
        """Return exact-source attachments whose declared family is unknown.

        These messages are deliberately kept out of the financial fact lane:
        a missing title must never be guessed into a document family.  The
        raw-ingestion lane still preserves their bytes and immutable envelope
        so a later deterministic parser can establish (or reject) a family
        from the document itself.
        """

        quarantined: list[dict[str, Any]] = []
        for message in page.messages:
            conversation_id = _message_field(message, ("openConversationId", "conversationId", "conversation_id"))
            sender_id = _message_field(message, ("senderOpenDingTalkId", "sender_open_dingtalk_id"))
            if conversation_id != self.config.group_id:
                raise IngestionError("AMBIGUOUS_SOURCE")
            if (
                sender_id == self.config.sender_id
                and _family(message) is None
                and self.attachment_count(message) > 0
            ):
                quarantined.append(message)
        return tuple(quarantined)

    @staticmethod
    def attachment_count(message: Mapping[str, Any]) -> int:
        return len(_attachments(message))

    def _message_id(self, message: Mapping[str, Any]) -> str:
        self.assert_exact_source(message)
        message_id = _message_field(message, ("openMessageId", "messageId", "message_id", "id"))
        if not message_id:
            raise IngestionError("MESSAGE_ID_MISSING")
        return message_id

    def message_id_hash(self, message: Mapping[str, Any]) -> str:
        """Derive the durable occurrence key only after the source gate."""

        return _hash_text(self._message_id(message))

    def reopen_candidate(
        self,
        message: dict[str, Any],
        index: int,
        attachment_sha256: str,
    ) -> PersistedRawAttachment | None:
        """Create a raw-identity candidate for an exact Git readback.

        This is deliberately not a cache of source bytes or metadata.  DWS
        can represent a document as an embedded media token with no declared
        filename, so filename/family/MIME are recovered from the immutable raw
        occurrence only after the current full message envelope is matched.
        """

        message_id = self._message_id(message)
        if (
            len(attachment_sha256) != 64
            or any(character not in "0123456789abcdef" for character in attachment_sha256)
        ):
            return None
        attachments = _attachments(message)
        if index < 0 or index >= len(attachments):
            return None
        attachment = attachments[index]
        if _attachment_resource(attachment) is None:
            return None
        return PersistedRawAttachment(
            message=message,
            message_id=message_id,
            message_id_hash=_hash_text(message_id),
            message_at=_message_timestamp(message),
            index=index,
            sha256=attachment_sha256,
        )

    def download(self, message: dict[str, Any], index: int) -> DownloadedAttachment:
        message_id = self._message_id(message)
        self.ensure_authenticated()
        attachments = _attachments(message)
        if index >= len(attachments):
            raise IngestionError("ATTACHMENT_INDEX_INVALID")
        attachment = attachments[index]
        source = _attachment_resource(attachment)
        if source is None:
            raise IngestionError("UNSUPPORTED_ATTACHMENT")
        resource_type, resource_id = source
        declared_filename = _message_field(attachment, ("fileName", "name", "title"))
        declared_mime = _message_field(attachment, ("mimeType", "mime", "contentType"))
        # The dedicated cloud volume is normally made by entrypoint, but a
        # restarted/sparse runtime must not translate a missing empty state
        # directory into an attachment-download failure before DWS is called.
        self.config.state_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="daily-funds-dws-", dir=self.config.state_dir) as temp:
            output_dir = Path(temp) / "download"
            output_dir.mkdir()
            # The current DWS resource downloader writes into a *relative*
            # working-directory path.  Running it inside this short-lived
            # private directory supports both native fileId workbooks and
            # mediaId previews without reusing a provider filename as a path.
            command = [
                self.config.dws_bin,
                "chat", "+messages-resource-download",
                "--type", resource_type,
                "--resource-id", resource_id,
                "--output", ".",
                "--format", "json",
                "--timeout", "150",
            ]
            if resource_type == "mediaId":
                command.extend([
                    "--message-id", message_id,
                    "--open-conversation-id", self.config.group_id,
                ])
            try:
                completed = self._run_dws(
                    command,
                    operation="ATTACHMENT_DOWNLOAD",
                    timeout=180,
                    cwd=output_dir,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                self._record_network_event("ATTACHMENT_DOWNLOAD", "TRANSPORT_FAILED")
                raise IngestionError("ATTACHMENT_DOWNLOAD_TRANSPORT_FAILED") from exc
            if completed.returncode != 0:
                code = _dws_attachment_download_failure_code(
                    completed.stdout,
                    completed.stderr,
                )
                self._record_network_event("ATTACHMENT_DOWNLOAD", code)
                raise IngestionError(code)
            files = [path for path in output_dir.rglob("*") if path.is_file()]
            if len(files) != 1:
                self._record_network_event("ATTACHMENT_DOWNLOAD", "INVALID")
                raise IngestionError("ATTACHMENT_DOWNLOAD_AMBIGUOUS")
            downloaded = files[0]
            try:
                payload = downloaded.read_bytes()
            except OSError as exc:
                self._record_network_event("ATTACHMENT_DOWNLOAD", "READ_FAILED")
                raise IngestionError("ATTACHMENT_DOWNLOAD_READ_FAILED") from exc
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
            mime=declared_mime,
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
        lease_profile: str = "live",
    ) -> int:
        # Live ingestion keeps a durable short lease because it owns a single
        # current-day cursor.  Historical backfill is serialized by the
        # worker-volume process lock in ``DailyFundsRuntime.backfill`` instead:
        # an abruptly replaced container releases that OS lock automatically,
        # whereas a two-hour SQLite lease can survive a deployment and falsely
        # suppress every subsequent scheduled historical batch.  Raw Git
        # writes remain serialised separately by ``git_writer_lock``.
        profiles = {
            "live": ("poll_lock", "POLL_LOCK_HELD", 14 * 60),
            "backfill": (None, "BACKFILL_LOCK_HELD", None),
        }
        try:
            lease_key, lock_code, lease_ttl_seconds = profiles[lease_profile]
        except KeyError as exc:
            raise IngestionError("POLL_LEASE_PROFILE_INVALID") from exc
        if lease_key is not None:
            if not self.state.acquire_lease(lease_key, holder, ttl_seconds=lease_ttl_seconds):
                raise IngestionError(lock_code)
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
            group_history_fallback_used = False
            while True:
                try:
                    page = self.client.search(start, now, candidate_cursor)
                except IngestionError as exc:
                    # A record-less terminal search page is explicitly
                    # ambiguous under DF-002.  The official exact-group
                    # reader is the only compatible fallback: it follows the
                    # provider cursor internally and returns a terminal page
                    # only after the complete requested window.  Never retry
                    # it after a failure or synthesize a cursor from time.
                    if exc.code != "DWS_PAGE_RECORDS_MISSING" or group_history_fallback_used:
                        raise
                    page = self.client.collect_group_history_v2(start, now)
                    group_history_fallback_used = True
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
            if lease_key is not None:
                self.state.release_lease(lease_key, holder)


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

    @classmethod
    def canonicalize_existing_occurrences(
        cls,
        root: Path,
        attachments: Iterable[DownloadedAttachment],
    ) -> tuple[DownloadedAttachment, ...]:
        """Reuse only a verified historic filename for an identical occurrence.

        DWS can return the same media bytes under a different downloaded file
        name on a later history read.  The filename determines the legacy blob
        suffix, so treating that delivery-only change as a new immutable
        occurrence would either create a conflicting manifest or overwrite an
        existing raw record.  Re-open the existing raw object instead: every
        identity, message, byte, size, MIME and family field must still match;
        only the already-recorded filename is allowed to become canonical.
        """

        frozen = cls.canonical_attachments(attachments)
        canonical: list[DownloadedAttachment] = []
        for attachment in frozen:
            _, occurrence_path, _, _ = cls._attachment_paths(attachment)
            occurrence_absolute = cls._safe_path(root, occurrence_path)
            if not occurrence_absolute.exists():
                canonical.append(attachment)
                continue
            try:
                existing = json.loads(occurrence_absolute.read_text(encoding="utf-8"))
                filename = existing.get("filename") if isinstance(existing, Mapping) else None
                if not isinstance(filename, str) or not filename:
                    raise ValueError("invalid historic filename")
                recovered = replace(attachment, filename=filename)
                # This validates the current complete message envelope, all
                # immutable occurrence fields, the historic object path and
                # the original bytes.  It therefore cannot turn a changed
                # source attachment or metadata into a successful replay.
                cls.readback_attachment(root, recovered)
            except (OSError, TypeError, ValueError, json.JSONDecodeError, IngestionError) as exc:
                raise IngestionError("RAW_PATH_HASH_COLLISION") from exc
            canonical.append(recovered)
        return tuple(canonical)

    @staticmethod
    def _message_and_occurrence_paths(
        message_at: datetime,
        message_id_hash: str,
        attachment_index: int,
    ) -> tuple[Path, Path]:
        day = message_at.astimezone(BEIJING).date()
        message_path = Path("raw/messages") / day.strftime("%Y/%m/%d") / f"{message_id_hash}.json"
        occurrence_path = (
            Path("raw/occurrences") / day.strftime("%Y/%m/%d") /
            message_id_hash / f"{attachment_index}.json"
        )
        return message_path, occurrence_path

    @classmethod
    def _attachment_paths(cls, attachment: DownloadedAttachment) -> tuple[Path, Path, Path, Path]:
        message_path, occurrence_path = cls._message_and_occurrence_paths(
            attachment.message_at,
            attachment.message_id_hash,
            attachment.index,
        )
        blob_path = Path("raw/blobs/sha256") / attachment.sha256[:2] / f"{attachment.sha256}{RawMaterializer._suffix(attachment.filename)}"
        manifest_path = Path("raw/chunks/sha256") / attachment.sha256 / "reassembly.json"
        return message_path, occurrence_path, blob_path, manifest_path

    @classmethod
    def _batch_rows(cls, attachments: Iterable[DownloadedAttachment]) -> list[dict[str, Any]]:
        """Build the order-independent occurrence rows of one raw batch.

        This is deliberately shared by staging, sparse-path selection and
        fresh-clone readback.  If any of those three steps derived a batch ID
        differently, a writer could validate an attachment while silently
        omitting the batch manifest that binds its occurrence to the batch.
        """

        rows: list[dict[str, Any]] = []
        for attachment in attachments:
            _, occurrence_path, _, _ = cls._attachment_paths(attachment)
            rows.append({
                "message_id_hash": attachment.message_id_hash,
                "attachment_index": attachment.index,
                "attachment_sha256": attachment.sha256,
                "occurrence_path": str(occurrence_path),
            })
        rows.sort(key=lambda row: (row["message_id_hash"], row["attachment_index"], row["attachment_sha256"]))
        return rows

    @classmethod
    def _batch_details(cls, attachments: Iterable[DownloadedAttachment]) -> tuple[str, list[dict[str, Any]], Path]:
        """Return the immutable batch ID, canonical rows and exact file path."""

        return cls._batch_details_from_rows(cls._batch_rows(attachments))

    @staticmethod
    def _batch_details_from_rows(rows: Iterable[Mapping[str, Any]]) -> tuple[str, list[dict[str, Any]], Path]:
        """Canonicalize pre-built rows without changing historic batch IDs."""

        frozen = [dict(row) for row in rows]
        frozen.sort(key=lambda row: (row["message_id_hash"], row["attachment_index"], row["attachment_sha256"]))
        # Keep the existing default JSON separators: batch IDs already written
        # by a prior worker must remain stable across this code revision.
        batch_id = sha256(json.dumps(frozen, sort_keys=True).encode("utf-8")).hexdigest()
        return batch_id, frozen, Path("raw/batches") / f"{batch_id}.json"

    @classmethod
    def persisted_batch_details(
        cls,
        attachments: Iterable[PersistedRawAttachment],
    ) -> tuple[str, list[dict[str, Any]], Path]:
        """Derive a batch manifest location from durable occurrence identities."""

        rows: list[dict[str, Any]] = []
        for attachment in attachments:
            _, occurrence_path = cls._message_and_occurrence_paths(
                attachment.message_at,
                attachment.message_id_hash,
                attachment.index,
            )
            rows.append({
                "message_id_hash": attachment.message_id_hash,
                "attachment_index": attachment.index,
                "attachment_sha256": attachment.sha256,
                "occurrence_path": str(occurrence_path),
            })
        return cls._batch_details_from_rows(rows)

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
        batch_id, batch_rows, batch_path = self._batch_details(frozen)
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

    @staticmethod
    def validate_persisted_raw_attachment(attachment: PersistedRawAttachment) -> None:
        """Validate the values-free identity that can be held in SQLite."""

        for value, code in (
            (attachment.message_id_hash, "RAW_MESSAGE_ID_HASH_INVALID"),
            (attachment.sha256, "RAW_ATTACHMENT_HASH_INVALID"),
        ):
            if not isinstance(value, str) or len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
                raise IngestionError(code)
        if not isinstance(attachment.message, dict) or not isinstance(attachment.message_id, str) or not attachment.message_id:
            raise IngestionError("RAW_MESSAGE_ENVELOPE_INVALID")
        if attachment.message_id_hash != _hash_text(attachment.message_id):
            raise IngestionError("RAW_MESSAGE_ID_HASH_INVALID")
        if not isinstance(attachment.index, int) or isinstance(attachment.index, bool) or attachment.index < 0:
            raise IngestionError("RAW_ATTACHMENT_INDEX_INVALID")
        if attachment.message_at.tzinfo is None or attachment.message_at.utcoffset() is None:
            raise IngestionError("RAW_MESSAGE_TIMESTAMP_INVALID")

    @staticmethod
    def _persisted_reopen_source_identity(
        message: Mapping[str, Any],
        *,
        attachment_index: int,
    ) -> tuple[str, str, str, datetime, str | None, int, str, str]:
        """Return the immutable source identity needed for an overlap reopen.

        DingTalk can return the same immutable message/media occurrence with
        different non-source display fields on a later history read.  A raw
        reopen must reject a changed source, but it must not treat that volatile
        envelope decoration as a changed attachment.  This deliberately keeps
        the exact source gate, message identity and normalized timestamp,
        document family, complete attachment cardinality, and the selected
        media resource.  The values remain in the private worker process; the
        caller receives no projection of them.
        """

        if not isinstance(message, Mapping):
            raise IngestionError("GIT_READBACK_FAILED")
        if not isinstance(attachment_index, int) or isinstance(attachment_index, bool) or attachment_index < 0:
            raise IngestionError("GIT_READBACK_FAILED")
        conversation_id = _message_field(message, ("openConversationId", "conversationId", "conversation_id"))
        sender_id = _message_field(message, ("senderOpenDingTalkId", "sender_open_dingtalk_id"))
        message_id = _message_field(message, ("openMessageId", "messageId", "message_id", "id"))
        if not conversation_id or not sender_id or not message_id:
            raise IngestionError("GIT_READBACK_FAILED")
        try:
            message_at = _message_timestamp(message)
        except IngestionError as exc:
            raise IngestionError("GIT_READBACK_FAILED") from exc
        attachments = _attachments(message)
        if attachment_index >= len(attachments):
            raise IngestionError("GIT_READBACK_FAILED")
        source = _attachment_resource(attachments[attachment_index])
        if source is None:
            raise IngestionError("GIT_READBACK_FAILED")
        resource_type, resource_id = source
        return (
            conversation_id,
            sender_id,
            message_id,
            message_at,
            _family(message),
            len(attachments),
            resource_type,
            resource_id,
        )

    @classmethod
    def hydrate_persisted_raw_attachment(
        cls,
        root: Path,
        attachment: PersistedRawAttachment,
    ) -> DownloadedAttachment:
        """Recover metadata and bytes only from an exact raw-Git readback.

        DWS embedded-media history rows may omit a filename.  The raw
        occurrence is the only authority for that metadata.  The current
        source result must match the stored immutable source identity, while
        the archived envelope itself is still byte-verified before any value
        is recovered.  The final normal readback then verifies every stored
        field and payload hash a second time.
        """

        try:
            cls.validate_persisted_raw_attachment(attachment)
            if root.is_symlink():
                raise IngestionError("GIT_READBACK_FAILED")
            message_path, occurrence_path = cls._message_and_occurrence_paths(
                attachment.message_at,
                attachment.message_id_hash,
                attachment.index,
            )
            stored_message = json.loads(cls._safe_path(root, message_path).read_text(encoding="utf-8"))
            current_identity = cls._persisted_reopen_source_identity(
                attachment.message,
                attachment_index=attachment.index,
            )
            stored_identity = cls._persisted_reopen_source_identity(
                stored_message,
                attachment_index=attachment.index,
            )
            if (
                current_identity != stored_identity
                or current_identity[2] != attachment.message_id
                or current_identity[3] != attachment.message_at.astimezone(UTC)
            ):
                raise IngestionError("GIT_READBACK_FAILED")
            occurrence = json.loads(cls._safe_path(root, occurrence_path).read_text(encoding="utf-8"))
            required = {
                "schema_version": "kmfa.daily_funds.occurrence.v1",
                "message_id_hash": attachment.message_id_hash,
                "attachment_index": attachment.index,
                "attachment_sha256": attachment.sha256,
                "message_path": str(message_path),
                "message_at": attachment.message_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            }
            if (
                not isinstance(occurrence, Mapping)
                or any(occurrence.get(key) != value for key, value in required.items())
                or not isinstance(occurrence.get("attachment_size_bytes"), int)
                or isinstance(occurrence.get("attachment_size_bytes"), bool)
                or occurrence["attachment_size_bytes"] < 0
                or not isinstance(occurrence.get("filename"), str)
                or not occurrence["filename"]
                or occurrence.get("family") is not None and not isinstance(occurrence.get("family"), str)
                or occurrence.get("mime") is not None and not isinstance(occurrence.get("mime"), str)
            ):
                raise IngestionError("GIT_READBACK_FAILED")
            recovered = DownloadedAttachment(
                message=attachment.message,
                message_id=attachment.message_id,
                message_id_hash=attachment.message_id_hash,
                message_at=attachment.message_at,
                index=attachment.index,
                filename=occurrence["filename"],
                family=occurrence.get("family"),
                payload=b"",
                sha256=attachment.sha256,
                mime=occurrence.get("mime"),
            )
            _, _, direct_path, _ = cls._attachment_paths(recovered)
            if occurrence.get("reassembly_manifest") is None:
                payload = cls._safe_path(root, direct_path).read_bytes()
            else:
                payload = cls.reassemble(root, attachment.sha256)
            if len(payload) != occurrence["attachment_size_bytes"]:
                raise IngestionError("GIT_READBACK_FAILED")
            archived = cls.readback_attachment(
                root,
                replace(recovered, message=stored_message, payload=payload),
            )
            return replace(archived, message=attachment.message)
        except (OSError, KeyError, TypeError, ValueError, IngestionError) as exc:
            raise IngestionError("GIT_READBACK_FAILED") from exc

    @classmethod
    def hydrate_readback_attachment(cls, root: Path, attachment: DownloadedAttachment) -> DownloadedAttachment:
        """Load a metadata-only overlap candidate from the raw authority.

        The SQLite journal intentionally retains just the known SHA, not
        attachment bytes or a byte count.  This method obtains the byte count
        and payload from a fresh sparse clone, then delegates to the normal
        full-envelope readback verifier.  It is therefore not a local cache
        shortcut and cannot turn stale metadata into published data.
        """

        try:
            cls._validate_attachment(attachment)
            if root.is_symlink():
                raise IngestionError("GIT_READBACK_FAILED")
            _, occurrence_path, direct_path, _ = cls._attachment_paths(attachment)
            occurrence = json.loads(cls._safe_path(root, occurrence_path).read_text(encoding="utf-8"))
            if (
                not isinstance(occurrence, Mapping)
                or occurrence.get("message_id_hash") != attachment.message_id_hash
                or occurrence.get("attachment_index") != attachment.index
                or occurrence.get("attachment_sha256") != attachment.sha256
                or not isinstance(occurrence.get("attachment_size_bytes"), int)
                or isinstance(occurrence.get("attachment_size_bytes"), bool)
                or occurrence["attachment_size_bytes"] < 0
            ):
                raise IngestionError("GIT_READBACK_FAILED")
            if occurrence.get("reassembly_manifest") is None:
                payload = cls._safe_path(root, direct_path).read_bytes()
            else:
                payload = cls.reassemble(root, attachment.sha256)
            if len(payload) != occurrence["attachment_size_bytes"]:
                raise IngestionError("GIT_READBACK_FAILED")
            return cls.readback_attachment(root, replace(attachment, payload=payload))
        except (OSError, KeyError, TypeError, ValueError, IngestionError) as exc:
            raise IngestionError("GIT_READBACK_FAILED") from exc

    @classmethod
    def readback_batch(
        cls,
        root: Path,
        attachments: Iterable[DownloadedAttachment],
        staged: StagedRawBatch,
    ) -> None:
        """Verify the occurrence-to-batch binding from a fresh sparse clone.

        Attachment-level readback proves individual envelopes and payloads.
        The immutable batch manifest is a separate raw-evidence object, so it
        must also be materialised and byte-compared before downstream use.
        """

        try:
            frozen = cls.canonical_attachments(attachments)
            batch_id, rows, batch_path = cls._batch_details(frozen)
            expected = cls._json_text({
                "schema_version": "kmfa.daily_funds.batch.v1",
                "batch_id": batch_id,
                "occurrences": rows,
            }, code="GIT_READBACK_FAILED")
            if (
                staged.batch_id != batch_id
                or staged.occurrences != len(frozen)
                or str(batch_path) not in staged.paths
                or tuple(sorted({attachment.sha256 for attachment in frozen})) != staged.attachment_hashes
                or cls._safe_path(root, batch_path).read_text(encoding="utf-8") != expected
            ):
                raise IngestionError("GIT_READBACK_FAILED")
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
            # The configuration allowlist pins this writer to github.com.
            # Route that one GitHub SSH authority over its documented TLS
            # port so restrictive cloud egress cannot block private raw
            # readback on port 22.  The deploy key and isolated known-hosts
            # file remain the only authentication and host-trust sources.
            "-o", "Hostname=ssh.github.com", "-o", "Port=443",
            # A sparse audit can require several independent Git transports.
            # Bound both connection establishment and a silent established
            # session here, rather than allowing one unavailable transport to
            # consume the full per-Git subprocess timeout repeatedly.
            "-o", "ConnectTimeout=20",
            "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=1",
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

    @classmethod
    def _is_retryable_audit_transport(cls, stderr: object) -> bool:
        """Recognise only a bounded Git/OpenSSH transport interruption."""

        text = str(stderr or "").lower()
        return any(marker in text for marker in cls._AUDIT_RETRYABLE_GIT_MARKERS)

    def _git(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        audit_read: bool = False,
        failure_code: str = "GIT_WRITE_FAILED",
    ) -> str:
        if failure_code not in _ARCHIVE_WRITE_FAILURE_CODES | {"GIT_WRITE_FAILED"}:
            raise ValueError("invalid git failure code")
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
            code = "GIT_AUDIT_TRANSPORT_RETRYABLE" if audit_read else failure_code
            raise IngestionError(code) from exc
        if completed.returncode != 0:
            if audit_read and self._is_retryable_audit_transport(completed.stderr):
                raise IngestionError("GIT_AUDIT_TRANSPORT_RETRYABLE")
            raise IngestionError(
                "GIT_NON_FAST_FORWARD"
                if self._is_non_fast_forward(args, completed.stderr or "")
                else failure_code
            )
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

        frozen = RawMaterializer.canonical_attachments(attachments)
        directories: set[Path] = set()
        for attachment in frozen:
            for path in RawMaterializer._attachment_paths(attachment):
                directories.add(SPARSE_PATH / path.parent)
        _, _, batch_path = RawMaterializer._batch_details(frozen)
        # The batch manifest is a single immutable evidence file, not a reason
        # to materialise all historic batches.  A non-cone sparse pattern may
        # select this exact file alongside the required object directories.
        exact_batch_path = (SPARSE_PATH / batch_path).as_posix()
        directory_patterns = [f"{path.as_posix()}/" for path in sorted(directories, key=lambda path: path.as_posix())]
        return tuple(sorted((*directory_patterns, exact_batch_path)))

    @staticmethod
    def _canonical_persisted_raw_attachments(
        attachments: Iterable[PersistedRawAttachment],
    ) -> tuple[PersistedRawAttachment, ...]:
        """Canonicalize overlap identities without trusting their metadata."""

        frozen = tuple(attachments)
        if not frozen:
            raise IngestionError("SOURCE_MISSING")
        unique: list[PersistedRawAttachment] = []
        by_occurrence: dict[tuple[str, int], PersistedRawAttachment] = {}
        for attachment in frozen:
            RawMaterializer.validate_persisted_raw_attachment(attachment)
            key = (attachment.message_id_hash, attachment.index)
            previous = by_occurrence.get(key)
            if previous is None:
                by_occurrence[key] = attachment
                unique.append(attachment)
                continue
            if previous != attachment:
                raise IngestionError("RAW_OCCURRENCE_COLLISION")
        return tuple(unique)

    @staticmethod
    def _persisted_raw_sparse_patterns(
        attachments: Iterable[PersistedRawAttachment],
    ) -> tuple[str, ...]:
        """Materialize only each known raw identity, not its historic peers.

        The one trailing ``*`` is constrained by the complete SHA-256 prefix:
        it selects the same direct blob under whichever original suffix DWS
        supplied, while avoiding a checkout of the enclosing hash directory.
        Batch membership is resolved separately from a commit-pinned metadata
        clone: one current DWS page may combine occurrences that were archived
        in more than one historic batch, so there is no safe synthetic batch
        filename to include here.
        """

        frozen = GitSparseWriter._canonical_persisted_raw_attachments(attachments)
        patterns: set[str] = set()
        for attachment in frozen:
            message_path, occurrence_path = RawMaterializer._message_and_occurrence_paths(
                attachment.message_at,
                attachment.message_id_hash,
                attachment.index,
            )
            patterns.add((SPARSE_PATH / message_path).as_posix())
            patterns.add((SPARSE_PATH / occurrence_path).as_posix())
            patterns.add(f"{(SPARSE_PATH / 'raw/blobs/sha256' / attachment.sha256[:2] / attachment.sha256).as_posix()}*")
            patterns.add(f"{(SPARSE_PATH / 'raw/chunks/sha256' / attachment.sha256).as_posix()}/")
        return tuple(sorted(patterns))

    @staticmethod
    def _persisted_occurrence_targets(
        attachments: Iterable[PersistedRawAttachment],
    ) -> dict[str, str]:
        """Return exact raw occurrence paths with the expected immutable hash."""

        frozen = GitSparseWriter._canonical_persisted_raw_attachments(attachments)
        targets: dict[str, str] = {}
        for attachment in frozen:
            _, occurrence_path = RawMaterializer._message_and_occurrence_paths(
                attachment.message_at,
                attachment.message_id_hash,
                attachment.index,
            )
            key = str(occurrence_path)
            if key in targets and targets[key] != attachment.sha256:
                raise IngestionError("RAW_OCCURRENCE_COLLISION")
            targets[key] = attachment.sha256
        return targets

    @staticmethod
    def _publication_sparse_patterns(business_date: str) -> tuple[str, ...]:
        return (f"{(SPARSE_PATH / 'publications' / business_date).as_posix()}/",)

    # The archive audit deliberately enumerates only Git *tree names* first,
    # then materialises an exact, bounded set of manifests and blobs.  This
    # keeps the worker from turning a routine parser-capability check into an
    # uncontrolled historic raw checkout as the private authority grows.
    # The first production full-history census contains 526 occurrences.  Keep
    # the audit explicitly bounded while leaving enough headroom for ordinary
    # growth instead of rejecting that verified source set before readback.
    _RAW_ARCHIVE_MAX_OCCURRENCES = 1024
    _RAW_ARCHIVE_MAX_BATCHES = 512
    _RAW_ARCHIVE_MAX_TREE_OUTPUT_BYTES = 512 * 1024
    # A full historic image census can contain hundreds of multi-megabyte
    # screenshots.  Retaining their payloads in one Python tuple makes the
    # otherwise read-only audit vulnerable to the worker's memory ceiling.
    # Keep a complete metadata census, then hydrate this many immutable raw
    # occurrences at a time from the same pinned Git tree.
    _RAW_ARCHIVE_READBACK_BATCH_SIZE = 16

    # The raw-archive audit is strictly read-only.  A single Git/OpenSSH
    # transport interruption may be retried from a fresh sparse clone, but
    # raw-integrity, configuration and scope failures may never be retried or
    # downgraded.  Each audit pins its later clones to the first tree commit,
    # so a normal branch advance cannot be misclassified as an integrity error.
    _AUDIT_RETRYABLE_GIT_MARKERS = (
        "connection reset",
        "connection timed out",
        "connection refused",
        "connection closed",
        "connection unexpectedly closed",
        "could not resolve host",
        "early eof",
        "failed to connect",
        "kex_exchange_identification",
        "network is unreachable",
        "operation timed out",
        "remote end hung up unexpectedly",
        "remote hung up unexpectedly",
        "ssh_exchange_identification",
    )

    @staticmethod
    def _raw_archive_occurrence_path(path: str) -> tuple[int, int, int, str, int]:
        """Validate one exact raw occurrence path from ``git ls-tree``."""

        candidate = Path(path)
        prefix = (*SPARSE_PATH.parts, "raw", "occurrences")
        parts = candidate.parts
        if (
            not isinstance(path, str)
            or path != candidate.as_posix()
            or candidate.is_absolute()
            or ".." in parts
            or len(parts) != len(prefix) + 5
            or parts[:len(prefix)] != prefix
            or not parts[-1].endswith(".json")
        ):
            raise IngestionError("GIT_READBACK_FAILED")
        year_text, month_text, day_text, message_id_hash, index_filename = parts[-5:]
        index_text = index_filename[:-5]
        try:
            year, month, day = int(year_text), int(month_text), int(day_text)
            datetime(year, month, day)
            index = int(index_text)
        except ValueError as exc:
            raise IngestionError("GIT_READBACK_FAILED") from exc
        if (
            not (2000 <= year <= 2999)
            or year_text != f"{year:04d}"
            or month_text != f"{month:02d}"
            or day_text != f"{day:02d}"
            or len(message_id_hash) != 64
            or any(character not in "0123456789abcdef" for character in message_id_hash)
            or index < 0
            or index_text != str(index)
        ):
            raise IngestionError("GIT_READBACK_FAILED")
        return year, month, day, message_id_hash, index

    @staticmethod
    def _raw_archive_batch_path(path: str) -> str:
        """Validate one immutable batch-manifest path from ``git ls-tree``."""

        candidate = Path(path)
        prefix = (*SPARSE_PATH.parts, "raw", "batches")
        parts = candidate.parts
        if (
            not isinstance(path, str)
            or path != candidate.as_posix()
            or candidate.is_absolute()
            or ".." in parts
            or len(parts) != len(prefix) + 1
            or parts[:len(prefix)] != prefix
            or not parts[-1].endswith(".json")
        ):
            raise IngestionError("GIT_READBACK_FAILED")
        batch_id = parts[-1][:-5]
        if len(batch_id) != 64 or any(character not in "0123456789abcdef" for character in batch_id):
            raise IngestionError("GIT_READBACK_FAILED")
        return batch_id

    def _raw_archive_tree_paths(
        self,
        repo: Path,
        *,
        env: Mapping[str, str],
        commit_sha: str,
        relative_root: Path,
        audit_read: bool = False,
    ) -> tuple[str, ...]:
        """List only names below one approved raw subtree, never its values."""

        tree_root = (SPARSE_PATH / relative_root).as_posix()
        output = self._git(
            ["ls-tree", "-r", "--name-only", commit_sha, "--", tree_root],
            cwd=repo,
            env=env,
            audit_read=audit_read,
        )
        if len(output.encode("utf-8", errors="ignore")) > self._RAW_ARCHIVE_MAX_TREE_OUTPUT_BYTES:
            raise IngestionError("RAW_ARCHIVE_CENSUS_LIMIT_EXCEEDED")
        return tuple(line for line in output.splitlines() if line)

    @staticmethod
    def _archive_occurrence_metadata(root: Path, occurrence_path: str) -> _RawArchiveOccurrence:
        """Read the non-value identity needed to select an exact sparse set."""

        try:
            year, month, day, path_message_hash, path_index = GitSparseWriter._raw_archive_occurrence_path(occurrence_path)
            relative = Path(occurrence_path).relative_to(SPARSE_PATH)
            payload = json.loads(RawMaterializer._safe_path(root, relative).read_text(encoding="utf-8"))
            expected_keys = {
                "schema_version", "message_id_hash", "attachment_index", "attachment_sha256",
                "attachment_size_bytes", "filename", "mime", "family", "message_path",
                "object_paths", "reassembly_manifest", "message_at",
            }
            if not isinstance(payload, Mapping) or set(payload) != expected_keys:
                raise IngestionError("GIT_READBACK_FAILED")
            raw_at = payload.get("message_at")
            if not isinstance(raw_at, str):
                raise IngestionError("GIT_READBACK_FAILED")
            message_at = datetime.fromisoformat(raw_at.replace("Z", "+00:00"))
            if message_at.tzinfo is None or message_at.utcoffset() is None:
                raise IngestionError("GIT_READBACK_FAILED")
            message_at = message_at.astimezone(UTC)
            expected_message_path, expected_occurrence_path = RawMaterializer._message_and_occurrence_paths(
                message_at,
                path_message_hash,
                path_index,
            )
            if (
                message_at.astimezone(BEIJING).date().isoformat() != f"{year:04d}-{month:02d}-{day:02d}"
                or str(expected_occurrence_path) != str(relative)
                or payload.get("schema_version") != "kmfa.daily_funds.occurrence.v1"
                or payload.get("message_id_hash") != path_message_hash
                or payload.get("attachment_index") != path_index
                or not isinstance(payload.get("attachment_sha256"), str)
                or len(payload["attachment_sha256"]) != 64
                or any(character not in "0123456789abcdef" for character in payload["attachment_sha256"])
                or not isinstance(payload.get("attachment_size_bytes"), int)
                or isinstance(payload.get("attachment_size_bytes"), bool)
                or payload["attachment_size_bytes"] < 0
                or payload.get("message_path") != str(expected_message_path)
            ):
                raise IngestionError("GIT_READBACK_FAILED")
            return _RawArchiveOccurrence(
                occurrence_path=occurrence_path,
                message_path=str(expected_message_path),
                message_at=message_at,
                message_id_hash=path_message_hash,
                index=path_index,
                sha256=payload["attachment_sha256"],
            )
        except (OSError, KeyError, TypeError, ValueError, IngestionError) as exc:
            raise IngestionError("GIT_READBACK_FAILED") from exc

    def _archive_persisted_references(
        self,
        root: Path,
        occurrences: Iterable[_RawArchiveOccurrence],
    ) -> tuple[PersistedRawAttachment, ...]:
        """Re-establish the original source envelope gate without a DWS call."""

        source_gate = DwsHistoryClient(self.config)
        references: list[PersistedRawAttachment] = []
        try:
            for occurrence in occurrences:
                message = json.loads(
                    RawMaterializer._safe_path(root, Path(occurrence.message_path)).read_text(encoding="utf-8")
                )
                if not isinstance(message, Mapping):
                    raise IngestionError("GIT_READBACK_FAILED")
                candidate = source_gate.reopen_candidate(
                    dict(message),
                    occurrence.index,
                    occurrence.sha256,
                )
                if (
                    candidate is None
                    or candidate.message_id_hash != occurrence.message_id_hash
                    or candidate.message_at.astimezone(UTC) != occurrence.message_at
                ):
                    raise IngestionError("GIT_READBACK_FAILED")
                references.append(candidate)
            frozen = self._canonical_persisted_raw_attachments(references)
            if len(frozen) != len(references):
                raise IngestionError("GIT_READBACK_FAILED")
            return frozen
        except (OSError, KeyError, TypeError, ValueError, IngestionError) as exc:
            raise IngestionError("GIT_READBACK_FAILED") from exc

    @staticmethod
    def _raw_archive_sparse_patterns(
        occurrences: Iterable[_RawArchiveOccurrence],
        batch_paths: Iterable[str],
    ) -> tuple[str, ...]:
        """Materialise only the envelopes, manifests and objects under audit."""

        patterns: set[str] = set(batch_paths)
        for occurrence in occurrences:
            patterns.add(occurrence.occurrence_path)
            patterns.add((SPARSE_PATH / occurrence.message_path).as_posix())
            patterns.add(
                f"{(SPARSE_PATH / 'raw/blobs/sha256' / occurrence.sha256[:2] / occurrence.sha256).as_posix()}*"
            )
            patterns.add(f"{(SPARSE_PATH / 'raw/chunks/sha256' / occurrence.sha256).as_posix()}/")
        return tuple(sorted(patterns))

    @staticmethod
    def _verify_raw_archive_batches(
        root: Path,
        *,
        batch_paths: Iterable[str],
        attachments: Iterable[DownloadedAttachment],
    ) -> int:
        """Bind every acquired occurrence to at least one immutable batch."""

        attachment_by_occurrence: dict[str, DownloadedAttachment] = {}
        for attachment in RawMaterializer.canonical_attachments(attachments):
            _, occurrence_path = RawMaterializer._message_and_occurrence_paths(
                attachment.message_at,
                attachment.message_id_hash,
                attachment.index,
            )
            key = str(occurrence_path)
            if key in attachment_by_occurrence:
                raise IngestionError("GIT_READBACK_FAILED")
            attachment_by_occurrence[key] = attachment

        referenced_occurrences: set[str] = set()
        reference_count = 0
        try:
            for full_path in batch_paths:
                batch_id_from_path = GitSparseWriter._raw_archive_batch_path(full_path)
                relative = Path(full_path).relative_to(SPARSE_PATH)
                payload = json.loads(RawMaterializer._safe_path(root, relative).read_text(encoding="utf-8"))
                if (
                    not isinstance(payload, Mapping)
                    or set(payload) != {"schema_version", "batch_id", "occurrences"}
                    or payload.get("schema_version") != "kmfa.daily_funds.batch.v1"
                    or payload.get("batch_id") != batch_id_from_path
                    or not isinstance(payload.get("occurrences"), list)
                    or not payload["occurrences"]
                ):
                    raise IngestionError("GIT_READBACK_FAILED")
                batch_attachments: list[DownloadedAttachment] = []
                rows: list[dict[str, Any]] = []
                seen_rows: set[tuple[str, int, str, str]] = set()
                for raw_row in payload["occurrences"]:
                    if not isinstance(raw_row, Mapping) or set(raw_row) != {
                        "message_id_hash", "attachment_index", "attachment_sha256", "occurrence_path",
                    }:
                        raise IngestionError("GIT_READBACK_FAILED")
                    message_id_hash = raw_row.get("message_id_hash")
                    index = raw_row.get("attachment_index")
                    attachment_sha256 = raw_row.get("attachment_sha256")
                    occurrence_path = raw_row.get("occurrence_path")
                    if (
                        not isinstance(message_id_hash, str)
                        or len(message_id_hash) != 64
                        or any(character not in "0123456789abcdef" for character in message_id_hash)
                        or not isinstance(index, int)
                        or isinstance(index, bool)
                        or index < 0
                        or not isinstance(attachment_sha256, str)
                        or len(attachment_sha256) != 64
                        or any(character not in "0123456789abcdef" for character in attachment_sha256)
                        or not isinstance(occurrence_path, str)
                    ):
                        raise IngestionError("GIT_READBACK_FAILED")
                    identity = (message_id_hash, index, attachment_sha256, occurrence_path)
                    if identity in seen_rows:
                        raise IngestionError("GIT_READBACK_FAILED")
                    seen_rows.add(identity)
                    attachment = attachment_by_occurrence.get(occurrence_path)
                    if (
                        attachment is None
                        or attachment.message_id_hash != message_id_hash
                        or attachment.index != index
                        or attachment.sha256 != attachment_sha256
                    ):
                        raise IngestionError("GIT_READBACK_FAILED")
                    batch_attachments.append(attachment)
                    rows.append(dict(raw_row))
                    referenced_occurrences.add(occurrence_path)
                    reference_count += 1
                batch_id, expected_rows, expected_path = RawMaterializer._batch_details(batch_attachments)
                if (
                    batch_id != batch_id_from_path
                    or str(expected_path) != str(relative)
                    or expected_rows != rows
                ):
                    raise IngestionError("GIT_READBACK_FAILED")
                staged = StagedRawBatch(
                    batch_id=batch_id,
                    paths=(str(expected_path),),
                    attachment_hashes=tuple(sorted({attachment.sha256 for attachment in batch_attachments})),
                    occurrences=len(batch_attachments),
                    reassembly_manifest_paths=(),
                )
                RawMaterializer.readback_batch(root, batch_attachments, staged)
            if set(attachment_by_occurrence) != referenced_occurrences:
                raise IngestionError("GIT_READBACK_FAILED")
            return reference_count
        except (OSError, KeyError, TypeError, ValueError, IngestionError) as exc:
            raise IngestionError("GIT_READBACK_FAILED") from exc

    @staticmethod
    def _verify_persisted_raw_batches(
        root: Path,
        *,
        batch_paths: Iterable[str],
        attachments: Iterable[PersistedRawAttachment],
    ) -> int:
        """Verify every batch binding before byte payloads are hydrated.

        The immutable batch manifest contains occurrence identity and the
        payload digest, not the payload itself.  Verifying it from the pinned
        metadata checkout first lets the later readback open one bounded group
        of blobs at a time.  Every individual byte is still reopened and
        verified by :meth:`RawMaterializer.hydrate_persisted_raw_attachment`
        before it reaches a parser callback.
        """

        attachment_by_occurrence: dict[str, PersistedRawAttachment] = {}
        try:
            frozen = GitSparseWriter._canonical_persisted_raw_attachments(attachments)
            for attachment in frozen:
                RawMaterializer.validate_persisted_raw_attachment(attachment)
                _, occurrence_path = RawMaterializer._message_and_occurrence_paths(
                    attachment.message_at,
                    attachment.message_id_hash,
                    attachment.index,
                )
                key = str(occurrence_path)
                if key in attachment_by_occurrence:
                    raise IngestionError("GIT_READBACK_FAILED")
                attachment_by_occurrence[key] = attachment

            referenced_occurrences: set[str] = set()
            reference_count = 0
            for full_path in batch_paths:
                batch_id_from_path = GitSparseWriter._raw_archive_batch_path(full_path)
                relative = Path(full_path).relative_to(SPARSE_PATH)
                payload = json.loads(RawMaterializer._safe_path(root, relative).read_text(encoding="utf-8"))
                if (
                    not isinstance(payload, Mapping)
                    or set(payload) != {"schema_version", "batch_id", "occurrences"}
                    or payload.get("schema_version") != "kmfa.daily_funds.batch.v1"
                    or payload.get("batch_id") != batch_id_from_path
                    or not isinstance(payload.get("occurrences"), list)
                    or not payload["occurrences"]
                ):
                    raise IngestionError("GIT_READBACK_FAILED")

                batch_attachments: list[PersistedRawAttachment] = []
                rows: list[dict[str, Any]] = []
                seen_rows: set[tuple[str, int, str, str]] = set()
                for raw_row in payload["occurrences"]:
                    if not isinstance(raw_row, Mapping) or set(raw_row) != {
                        "message_id_hash", "attachment_index", "attachment_sha256", "occurrence_path",
                    }:
                        raise IngestionError("GIT_READBACK_FAILED")
                    message_id_hash = raw_row.get("message_id_hash")
                    index = raw_row.get("attachment_index")
                    attachment_sha256 = raw_row.get("attachment_sha256")
                    occurrence_path = raw_row.get("occurrence_path")
                    if (
                        not isinstance(message_id_hash, str)
                        or len(message_id_hash) != 64
                        or any(character not in "0123456789abcdef" for character in message_id_hash)
                        or not isinstance(index, int)
                        or isinstance(index, bool)
                        or index < 0
                        or not isinstance(attachment_sha256, str)
                        or len(attachment_sha256) != 64
                        or any(character not in "0123456789abcdef" for character in attachment_sha256)
                        or not isinstance(occurrence_path, str)
                    ):
                        raise IngestionError("GIT_READBACK_FAILED")
                    identity = (message_id_hash, index, attachment_sha256, occurrence_path)
                    if identity in seen_rows:
                        raise IngestionError("GIT_READBACK_FAILED")
                    seen_rows.add(identity)
                    attachment = attachment_by_occurrence.get(occurrence_path)
                    if (
                        attachment is None
                        or attachment.message_id_hash != message_id_hash
                        or attachment.index != index
                        or attachment.sha256 != attachment_sha256
                    ):
                        raise IngestionError("GIT_READBACK_FAILED")
                    batch_attachments.append(attachment)
                    rows.append(dict(raw_row))
                    referenced_occurrences.add(occurrence_path)
                    reference_count += 1

                batch_id, expected_rows, expected_path = RawMaterializer.persisted_batch_details(batch_attachments)
                if (
                    batch_id != batch_id_from_path
                    or str(expected_path) != str(relative)
                    or expected_rows != rows
                ):
                    raise IngestionError("GIT_READBACK_FAILED")
            if set(attachment_by_occurrence) != referenced_occurrences:
                raise IngestionError("GIT_READBACK_FAILED")
            return reference_count
        except (OSError, KeyError, TypeError, ValueError, IngestionError) as exc:
            raise IngestionError("GIT_READBACK_FAILED") from exc

    def audit_raw_archive(
        self,
        *,
        on_attachment: Callable[[DownloadedAttachment], None] | None = None,
    ) -> RawArchiveAudit:
        """Re-open the acquired raw authority for deterministic capability audit.

        This is a cloud-worker-only read path.  It never lists DWS history,
        writes Git, mirrors R2, changes a publication pointer, or emits raw
        metadata.  A source-message envelope is still checked against the
        configured group/sender gate before its stored bytes can reach a
        parser.
        """

        try:
            if on_attachment is None:
                return self._audit_raw_archive_once()
            return self._audit_raw_archive_once(on_attachment=on_attachment)
        except IngestionError as exc:
            # The retry creates a new temporary HOME, deploy-key file,
            # known-hosts file and sparse checkout.  No partial checkout or
            # failed transport state is carried into the second attempt.
            # Integrity, source, scope and every second-attempt error remain
            # fail-closed.
            if exc.code != "GIT_AUDIT_TRANSPORT_RETRYABLE":
                raise
        if on_attachment is None:
            return self._audit_raw_archive_once()
        return self._audit_raw_archive_once(on_attachment=on_attachment)

    def audit_raw_archive_metadata(
        self,
        *,
        on_attachment: Callable[[PersistedRawAttachment], None] | None = None,
        commit_sha: str | None = None,
    ) -> RawArchiveAudit:
        """Census source-gated raw occurrences without hydrating every blob.

        This is intentionally narrower than :meth:`audit_raw_archive`: it
        validates the commit-pinned occurrence, message and immutable-batch
        metadata, then exposes only persisted occurrence identities to the
        caller.  It never gives a parser any payload bytes.  A later
        publication still has to use :meth:`reopen_persisted` for its exact
        account/transaction pair, which reopens and verifies those bytes from
        the same pinned commit before reconciliation.

        Coverage reconciliation needs identities, not a 360-day OCR replay.
        Avoiding one sparse Git transport per payload batch keeps that
        maintenance path bounded without weakening the byte-readback gate on
        the only facts that can reach a publication.  A caller that already
        holds an immutable coverage receipt may pin this census to that exact
        commit, so a later append to the private branch cannot turn the same
        evidence snapshot into a false stale failure.
        """

        if commit_sha is not None and not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
            raise IngestionError("GIT_READBACK_FAILED")

        try:
            return self._audit_raw_archive_once(
                on_attachment=on_attachment,
                metadata_only=True,
                commit_sha=commit_sha,
            )
        except IngestionError as exc:
            if exc.code != "GIT_AUDIT_TRANSPORT_RETRYABLE":
                raise
        return self._audit_raw_archive_once(
            on_attachment=on_attachment,
            metadata_only=True,
            commit_sha=commit_sha,
        )

    def _audit_raw_archive_once(
        self,
        *,
        on_attachment: Callable[[DownloadedAttachment], None]
        | Callable[[PersistedRawAttachment], None]
        | None = None,
        metadata_only: bool = False,
        commit_sha: str | None = None,
    ) -> RawArchiveAudit:
        """Perform one fresh, bounded sparse read of the private raw authority."""

        self.config.validate(include_storage=False)
        if not self.config.state_dir.exists():
            self.config.state_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="daily-funds-git-raw-audit-", dir=self.config.state_dir) as temp:
            temp_root = Path(temp)
            key_path = self._write_deploy_key(temp_root, self.config.git_ssh_key_b64)
            env = self._git_environment(temp_root, key_path)
            tree_repo = temp_root / "private-db-tree"
            # A non-existent exact path materialises no raw object.  The
            # following ``ls-tree`` examines names only and is bounded before
            # any selected manifest or blob is checked out.
            sentinel = (SPARSE_PATH / "raw" / ".raw-audit-sentinel").as_posix()
            self._clone_sparse(
                tree_repo,
                env=env,
                ref=self.config.private_branch,
                patterns=(sentinel,),
                audit_read=True,
                commit_sha=commit_sha,
            )
            commit_sha = self._git(["rev-parse", "HEAD"], cwd=tree_repo, env=env, audit_read=True)
            occurrence_paths = self._raw_archive_tree_paths(
                tree_repo,
                env=env,
                commit_sha=commit_sha,
                relative_root=Path("raw/occurrences"),
                audit_read=True,
            )
            batch_paths = self._raw_archive_tree_paths(
                tree_repo,
                env=env,
                commit_sha=commit_sha,
                relative_root=Path("raw/batches"),
                audit_read=True,
            )
            if (
                not occurrence_paths
                or not batch_paths
                or len(occurrence_paths) > self._RAW_ARCHIVE_MAX_OCCURRENCES
                or len(batch_paths) > self._RAW_ARCHIVE_MAX_BATCHES
            ):
                raise IngestionError("RAW_ARCHIVE_CENSUS_LIMIT_EXCEEDED" if (
                    len(occurrence_paths) > self._RAW_ARCHIVE_MAX_OCCURRENCES
                    or len(batch_paths) > self._RAW_ARCHIVE_MAX_BATCHES
                ) else "SOURCE_MISSING")
            for path in occurrence_paths:
                self._raw_archive_occurrence_path(path)
            for path in batch_paths:
                self._raw_archive_batch_path(path)

            metadata_repo = temp_root / "private-db-metadata"
            metadata_message_paths = []
            for occurrence_path in occurrence_paths:
                year, month, day, message_id_hash, _ = self._raw_archive_occurrence_path(occurrence_path)
                metadata_message_paths.append(
                    (SPARSE_PATH / "raw" / "messages" / f"{year:04d}" / f"{month:02d}" / f"{day:02d}" / f"{message_id_hash}.json").as_posix()
                )
            metadata_patterns = tuple(sorted((
                *occurrence_paths,
                *batch_paths,
                *metadata_message_paths,
            )))
            self._clone_sparse(
                metadata_repo,
                env=env,
                ref=self.config.private_branch,
                patterns=metadata_patterns,
                audit_read=True,
                commit_sha=commit_sha,
            )
            if self._git(["rev-parse", "HEAD"], cwd=metadata_repo, env=env, audit_read=True) != commit_sha:
                raise IngestionError("GIT_READBACK_FAILED")
            metadata_root = metadata_repo / SPARSE_PATH
            occurrences = tuple(
                self._archive_occurrence_metadata(metadata_root, path)
                for path in occurrence_paths
            )

            references = self._archive_persisted_references(metadata_root, occurrences)
            batch_references = self._verify_persisted_raw_batches(
                metadata_root,
                batch_paths=batch_paths,
                attachments=references,
            )

            if metadata_only:
                if on_attachment is not None:
                    for attachment in references:
                        on_attachment(attachment)
                return RawArchiveAudit(
                    commit_sha=commit_sha,
                    verified_attachments=(),
                    occurrence_count=len(references),
                    batch_count=len(batch_paths),
                    batch_occurrence_references=batch_references,
                )

            if on_attachment is not None:
                for start in range(0, len(references), self._RAW_ARCHIVE_READBACK_BATCH_SIZE):
                    batch = references[start:start + self._RAW_ARCHIVE_READBACK_BATCH_SIZE]
                    readback_repo = temp_root / f"private-db-readback-{start:04d}"
                    try:
                        self._clone_sparse(
                            readback_repo,
                            env=env,
                            ref=self.config.private_branch,
                            patterns=self._persisted_raw_sparse_patterns(batch),
                            audit_read=True,
                            commit_sha=commit_sha,
                        )
                        if self._git(["rev-parse", "HEAD"], cwd=readback_repo, env=env, audit_read=True) != commit_sha:
                            raise IngestionError("GIT_READBACK_FAILED")
                        root = readback_repo / SPARSE_PATH
                        for attachment in batch:
                            on_attachment(RawMaterializer.hydrate_persisted_raw_attachment(root, attachment))
                    finally:
                        # This directory is an exact child of the active
                        # TemporaryDirectory.  Removing it between groups
                        # bounds both checkout disk and process page cache.
                        if readback_repo.exists():
                            shutil.rmtree(readback_repo)
                return RawArchiveAudit(
                    commit_sha=commit_sha,
                    verified_attachments=(),
                    occurrence_count=len(references),
                    batch_count=len(batch_paths),
                    batch_occurrence_references=batch_references,
                )

            readback_repo = temp_root / "private-db-readback"
            readback_patterns = self._raw_archive_sparse_patterns(occurrences, batch_paths)
            self._clone_sparse(
                readback_repo,
                env=env,
                ref=self.config.private_branch,
                patterns=readback_patterns,
                audit_read=True,
                commit_sha=commit_sha,
            )
            if self._git(["rev-parse", "HEAD"], cwd=readback_repo, env=env, audit_read=True) != commit_sha:
                raise IngestionError("GIT_READBACK_FAILED")
            root = readback_repo / SPARSE_PATH
            # The metadata-only verification above and this full payload
            # readback must agree on the same exact source references.
            verified = tuple(
                RawMaterializer.hydrate_persisted_raw_attachment(root, attachment)
                for attachment in references
            )
            # Retain the historic full-payload batch verifier for callers
            # without a streaming callback (including local contract tests).
            if self._verify_raw_archive_batches(root, batch_paths=batch_paths, attachments=verified) != batch_references:
                raise IngestionError("GIT_READBACK_FAILED")
            return RawArchiveAudit(
                commit_sha=commit_sha,
                verified_attachments=verified,
                occurrence_count=len(verified),
                batch_count=len(batch_paths),
                batch_occurrence_references=batch_references,
            )

    def _clone_sparse(
        self,
        repo: Path,
        *,
        env: Mapping[str, str],
        ref: str,
        patterns: Sequence[str] | None = None,
        audit_read: bool = False,
        failure_code: str = "GIT_WRITE_FAILED",
        commit_sha: str | None = None,
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
        # A shallow clone normally fetches only the remote symbolic HEAD.  A
        # newly-created private repository can still have that HEAD pointing
        # at ``master`` even though this single-writer contract permits only
        # ``main``.  Bind the clone itself to ``ref`` so Git-version-specific
        # shallow-clone behavior cannot turn that server-default mismatch into
        # a write-path failure.  When an audit already selected one immutable
        # tree commit, it fetches and detaches that commit *before* checkout so
        # a concurrent branch advance cannot mix manifests across snapshots.
        if commit_sha is not None and not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
            raise IngestionError("GIT_READBACK_FAILED")
        self._git([
            "clone", "--branch", ref, "--depth=1", "--filter=blob:none", "--sparse", "--no-checkout",
            self.config.private_repo, str(repo),
        ], env=env, audit_read=audit_read, failure_code=failure_code)
        # Cone mode always includes root-level files.  Non-cone mode is used
        # deliberately so an exact-path writer never checks out unrelated
        # repository material before it handles financial evidence.
        self._git(
            ["sparse-checkout", "set", "--no-cone", *selected],
            cwd=repo,
            env=env,
            audit_read=audit_read,
            failure_code=failure_code,
        )
        if commit_sha is not None:
            self._git(
                ["fetch", "--depth=1", "origin", commit_sha],
                cwd=repo,
                env=env,
                audit_read=audit_read,
                failure_code=failure_code,
            )
            self._git(
                ["checkout", "--detach", commit_sha],
                cwd=repo,
                env=env,
                audit_read=audit_read,
                failure_code=failure_code,
            )
        else:
            self._git(["checkout", ref], cwd=repo, env=env, audit_read=audit_read, failure_code=failure_code)
        self._assert_sparse_checkout_scope(repo)

    def _prepare_sparse_clone_with_single_retry(
        self,
        repo: Path,
        *,
        env: Mapping[str, str],
        ref: str,
        patterns: Sequence[str] | None = None,
        failure_code: str = "GIT_ARCHIVE_PREPARE_FAILED",
    ) -> Path:
        """Make one fresh retry of the pre-mutation sparse preparation.

        A GitHub/OpenSSH transport can transiently fail while the private
        authority is being cloned.  At this point neither raw bytes nor a Git
        commit have been written, so one retry in a separate empty directory
        is safe and idempotent.  Scope/integrity failures retain their own
        codes and are never retried; a second prepare failure remains
        fail-closed with the same fixed public-safe stage code.
        """

        try:
            self._clone_sparse(
                repo,
                env=env,
                ref=ref,
                patterns=patterns,
                failure_code=failure_code,
            )
            return repo
        except IngestionError as exc:
            if exc.code != failure_code:
                raise
        retry_repo = repo.with_name(f"{repo.name}-retry")
        self._clone_sparse(
            retry_repo,
            env=env,
            ref=ref,
            patterns=patterns,
            failure_code=failure_code,
        )
        return retry_repo

    def _push_with_single_rebase(
        self,
        repo: Path,
        *,
        env: Mapping[str, str],
        failure_code: str = "GIT_WRITE_FAILED",
    ) -> None:
        """Retry the expected main race once, never with a force push."""

        try:
            self._git(
                ["push", "origin", f"HEAD:{self.config.private_branch}"],
                cwd=repo,
                env=env,
                failure_code=failure_code,
            )
        except IngestionError as exc:
            if exc.code != "GIT_NON_FAST_FORWARD":
                raise
            self._git(
                ["fetch", "origin", self.config.private_branch],
                cwd=repo,
                env=env,
                failure_code="GIT_ARCHIVE_REBASE_FAILED",
            )
            self._git(
                ["rebase", f"origin/{self.config.private_branch}"],
                cwd=repo,
                env=env,
                failure_code="GIT_ARCHIVE_REBASE_FAILED",
            )
            self._git(
                ["push", "origin", f"HEAD:{self.config.private_branch}"],
                cwd=repo,
                env=env,
                failure_code=failure_code,
            )

    def _readback_sparse_root(
        self,
        temp_root: Path,
        *,
        env: Mapping[str, str],
        commit_sha: str,
        patterns: Sequence[str] | None = None,
        failure_code: str = "GIT_WRITE_FAILED",
    ) -> Path:
        """Reopen the pushed commit through a new sparse clone.

        ``ls-remote`` only proves that a ref points at a SHA.  This extra clone
        proves that the actual objects which will feed R2/parser can be fetched
        and opened from GitHub after the push succeeds (F-008).
        """

        repo = temp_root / "private-db-readback"
        # Clone first on the permitted branch so sparse setup remains identical
        # to the writer, then detach at the pushed SHA for the actual readback.
        # This is still strictly pre-validation: one failed network/checkout
        # preparation can be retried in a fresh directory, but no materialized
        # raw object or integrity assertion is ever retried or downgraded.
        for candidate in (repo, repo.with_name(f"{repo.name}-retry")):
            try:
                self._clone_sparse(
                    candidate,
                    env=env,
                    ref=self.config.private_branch,
                    patterns=patterns,
                    failure_code=failure_code,
                    commit_sha=commit_sha,
                )
                return candidate / SPARSE_PATH
            except IngestionError as exc:
                if candidate == repo and exc.code == failure_code:
                    continue
                raise
        raise IngestionError(failure_code)

    def _readback_attachments(
        self,
        temp_root: Path,
        *,
        env: Mapping[str, str],
        commit_sha: str,
        attachments: Iterable[DownloadedAttachment],
        staged: StagedRawBatch,
        patterns: Sequence[str],
    ) -> tuple[DownloadedAttachment, ...]:
        root = self._readback_sparse_root(
            temp_root,
            env=env,
            commit_sha=commit_sha,
            patterns=patterns,
            failure_code="GIT_ARCHIVE_READBACK_FAILED",
        )
        frozen = RawMaterializer.canonical_attachments(attachments)
        verified = tuple(RawMaterializer.readback_attachment(root, attachment) for attachment in frozen)
        RawMaterializer.readback_batch(root, frozen, staged)
        return verified

    def _readback_persisted_batch_membership(
        self,
        temp_root: Path,
        *,
        repo: Path,
        env: Mapping[str, str],
        commit_sha: str,
        attachments: Iterable[PersistedRawAttachment],
    ) -> tuple[str, ...]:
        """Prove each reopened occurrence belongs to a real raw batch.

        A DWS overlap is a query result, not an immutable archive batch.  It
        can span batches that were first persisted by earlier pages, so a
        synthetic combined batch manifest must never be required or invented.
        This method reads only bounded batch manifests from the same pinned
        commit as the exact attachment clone and verifies every target
        occurrence/hash pair against at least one canonical stored batch.
        """

        targets = self._persisted_occurrence_targets(attachments)
        tree_root = (SPARSE_PATH / "raw/batches").as_posix()
        output = self._git(
            ["ls-tree", "-r", "--name-only", commit_sha, "--", tree_root],
            cwd=repo,
            env=env,
            failure_code="GIT_ARCHIVE_READBACK_FAILED",
        )
        if len(output.encode("utf-8", errors="ignore")) > self._RAW_ARCHIVE_MAX_TREE_OUTPUT_BYTES:
            raise IngestionError("GIT_ARCHIVE_READBACK_FAILED")
        batch_paths = tuple(line for line in output.splitlines() if line)
        if not batch_paths or len(batch_paths) > self._RAW_ARCHIVE_MAX_BATCHES:
            raise IngestionError("GIT_ARCHIVE_READBACK_FAILED")
        for path in batch_paths:
            self._raw_archive_batch_path(path)

        metadata_repo = temp_root / "private-db-reopen-batches"
        self._clone_sparse(
            metadata_repo,
            env=env,
            ref=self.config.private_branch,
            patterns=batch_paths,
            failure_code="GIT_ARCHIVE_READBACK_FAILED",
            commit_sha=commit_sha,
        )
        if self._git(
            ["rev-parse", "HEAD"],
            cwd=metadata_repo,
            env=env,
            failure_code="GIT_ARCHIVE_READBACK_FAILED",
        ) != commit_sha:
            raise IngestionError("GIT_ARCHIVE_READBACK_FAILED")

        covered: dict[str, str] = {}
        root = metadata_repo / SPARSE_PATH
        try:
            for full_path in batch_paths:
                batch_id = self._raw_archive_batch_path(full_path)
                relative_path = Path(full_path).relative_to(SPARSE_PATH)
                payload = json.loads(RawMaterializer._safe_path(root, relative_path).read_text(encoding="utf-8"))
                if (
                    not isinstance(payload, Mapping)
                    or set(payload) != {"schema_version", "batch_id", "occurrences"}
                    or payload.get("schema_version") != "kmfa.daily_funds.batch.v1"
                    or payload.get("batch_id") != batch_id
                    or not isinstance(payload.get("occurrences"), list)
                    or not payload["occurrences"]
                ):
                    raise IngestionError("GIT_ARCHIVE_READBACK_FAILED")

                rows: list[dict[str, Any]] = []
                seen_rows: set[tuple[str, int, str, str]] = set()
                for raw_row in payload["occurrences"]:
                    if not isinstance(raw_row, Mapping) or set(raw_row) != {
                        "message_id_hash", "attachment_index", "attachment_sha256", "occurrence_path",
                    }:
                        raise IngestionError("GIT_ARCHIVE_READBACK_FAILED")
                    message_id_hash = raw_row.get("message_id_hash")
                    index = raw_row.get("attachment_index")
                    attachment_sha256 = raw_row.get("attachment_sha256")
                    occurrence_path = raw_row.get("occurrence_path")
                    if (
                        not isinstance(message_id_hash, str)
                        or len(message_id_hash) != 64
                        or any(character not in "0123456789abcdef" for character in message_id_hash)
                        or not isinstance(index, int)
                        or isinstance(index, bool)
                        or index < 0
                        or not isinstance(attachment_sha256, str)
                        or len(attachment_sha256) != 64
                        or any(character not in "0123456789abcdef" for character in attachment_sha256)
                        or not isinstance(occurrence_path, str)
                    ):
                        raise IngestionError("GIT_ARCHIVE_READBACK_FAILED")
                    year, month, day, path_message_hash, path_index = self._raw_archive_occurrence_path(
                        (SPARSE_PATH / occurrence_path).as_posix()
                    )
                    if (
                        path_message_hash != message_id_hash
                        or path_index != index
                        or not (2000 <= year <= 2999)
                        or not (1 <= month <= 12)
                        or not (1 <= day <= 31)
                    ):
                        raise IngestionError("GIT_ARCHIVE_READBACK_FAILED")
                    identity = (message_id_hash, index, attachment_sha256, occurrence_path)
                    if identity in seen_rows:
                        raise IngestionError("GIT_ARCHIVE_READBACK_FAILED")
                    seen_rows.add(identity)
                    rows.append(dict(raw_row))

                computed_batch_id, computed_rows, computed_path = RawMaterializer._batch_details_from_rows(rows)
                if (
                    computed_batch_id != batch_id
                    or str(computed_path) != str(relative_path)
                    or rows != computed_rows
                ):
                    raise IngestionError("GIT_ARCHIVE_READBACK_FAILED")
                for row in computed_rows:
                    expected_hash = targets.get(row["occurrence_path"])
                    if expected_hash is None:
                        continue
                    if row["attachment_sha256"] != expected_hash:
                        raise IngestionError("GIT_ARCHIVE_READBACK_FAILED")
                    covered.setdefault(row["occurrence_path"], str(relative_path))
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, IngestionError) as exc:
            raise IngestionError("GIT_ARCHIVE_READBACK_FAILED") from exc

        if set(covered) != set(targets):
            raise IngestionError("GIT_ARCHIVE_READBACK_FAILED")
        return tuple(sorted(set(covered.values())))

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
            repo = self._prepare_sparse_clone_with_single_retry(
                temp_root / "private-db",
                env=env,
                ref=self.config.private_branch,
                patterns=sparse_patterns,
                failure_code="GIT_ARCHIVE_PREPARE_FAILED",
            )
            self._git(
                ["config", "user.name", "kmfa-daily-funds-writer"],
                cwd=repo,
                env=env,
                failure_code="GIT_ARCHIVE_PREPARE_FAILED",
            )
            self._git(
                ["config", "user.email", "kmfa-daily-funds@localhost"],
                cwd=repo,
                env=env,
                failure_code="GIT_ARCHIVE_PREPARE_FAILED",
            )
            materializer = RawMaterializer()
            canonical_attachments = materializer.canonicalize_existing_occurrences(
                repo / SPARSE_PATH,
                frozen_attachments,
            )
            staged = materializer.stage(repo / SPARSE_PATH, canonical_attachments)
            self._git(
                ["add", "--sparse", "--", str(SPARSE_PATH)],
                cwd=repo,
                env=env,
                failure_code="GIT_ARCHIVE_STAGE_FAILED",
            )
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
                self._git(
                    ["commit", "-m", f"data(kmfa): daily funds raw batch {staged.batch_id[:12]}"],
                    cwd=repo,
                    env=env,
                    failure_code="GIT_ARCHIVE_COMMIT_FAILED",
                )
                self._push_with_single_rebase(
                    repo,
                    env=env,
                    failure_code="GIT_ARCHIVE_PUSH_FAILED",
                )
            commit_sha = self._git(
                ["rev-parse", "HEAD"],
                cwd=repo,
                env=env,
                failure_code="GIT_ARCHIVE_VERIFY_FAILED",
            )
            remote_head = self._git(
                ["ls-remote", "origin", f"refs/heads/{self.config.private_branch}"],
                cwd=repo,
                env=env,
                failure_code="GIT_ARCHIVE_VERIFY_FAILED",
            ).split()
            if not remote_head or remote_head[0] != commit_sha:
                raise IngestionError("GIT_READBACK_FAILED")
            verified_attachments = self._readback_attachments(
                temp_root,
                env=env,
                commit_sha=commit_sha,
                attachments=canonical_attachments,
                staged=staged,
                patterns=sparse_patterns,
            )
            # OCI's full recovery bundle is deliberately produced only after a
            # valid two-fact publication (``bundle_head``).  Creating a second
            # bundle here is unused by every downstream consumer and can
            # materialise the entire historic private tree during raw intake.
            return GitCommit(
                commit_sha=commit_sha,
                staged=staged,
                verified_attachments=verified_attachments,
            )

    def reopen_persisted(
        self,
        attachments: Iterable[PersistedRawAttachment],
        *,
        commit_sha: str | None = None,
    ) -> GitCommit:
        """Re-open already-persisted overlap evidence without a Git mutation.

        The live cadence deliberately re-queries a short historical window.
        A repeated attachment is never trusted from the OVH journal: its
        current source envelope and bytes must be proved again through a new,
        exact-path sparse clone of the private Git authority.
        """

        self.config.validate(include_storage=False)
        frozen_attachments = self._canonical_persisted_raw_attachments(attachments)
        sparse_patterns = self._persisted_raw_sparse_patterns(frozen_attachments)
        if commit_sha is not None and not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
            raise IngestionError("GIT_ARCHIVE_READBACK_FAILED")
        if not self.config.state_dir.exists():
            self.config.state_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="daily-funds-git-reopen-", dir=self.config.state_dir) as temp:
            temp_root = Path(temp)
            key_path = self._write_deploy_key(temp_root, self.config.git_ssh_key_b64)
            env = self._git_environment(temp_root, key_path)
            repo = temp_root / "private-db-readback"
            try:
                self._clone_sparse(
                    repo,
                    env=env,
                    ref=self.config.private_branch,
                    patterns=sparse_patterns,
                    failure_code="GIT_ARCHIVE_READBACK_FAILED",
                    commit_sha=commit_sha,
                )
                reopened_commit_sha = self._git(
                    ["rev-parse", "HEAD"],
                    cwd=repo,
                    env=env,
                    failure_code="GIT_ARCHIVE_READBACK_FAILED",
                )
                if commit_sha is not None and reopened_commit_sha != commit_sha:
                    raise IngestionError("GIT_ARCHIVE_READBACK_FAILED")
                source_batch_paths = self._readback_persisted_batch_membership(
                    temp_root,
                    repo=repo,
                    env=env,
                    commit_sha=reopened_commit_sha,
                    attachments=frozen_attachments,
                )
                root = repo / SPARSE_PATH
                verified_attachments = tuple(
                    RawMaterializer.hydrate_persisted_raw_attachment(root, attachment)
                    for attachment in frozen_attachments
                )
                reopened = ReopenedRawEvidence(
                    source_batch_paths=source_batch_paths,
                    attachment_hashes=tuple(sorted({attachment.sha256 for attachment in verified_attachments})),
                    occurrences=len(verified_attachments),
                )
                return GitCommit(
                    commit_sha=reopened_commit_sha,
                    staged=reopened,
                    verified_attachments=verified_attachments,
                )
            except IngestionError as exc:
                if exc.code == "GIT_ARCHIVE_READBACK_FAILED":
                    raise
                raise IngestionError("GIT_ARCHIVE_READBACK_FAILED") from exc

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
        """Produce a self-contained private Git bundle for OCI recovery.

        Normal raw writes deliberately use a shallow sparse clone.  A bundle
        made directly from that clone can omit the raw commit's ancestry and
        then fail ``git bundle verify`` in an empty recovery repository.  The
        recovery-only path therefore completes the private history before
        packing it; its temporary checkout is removed immediately afterwards.
        """

        self.config.validate(include_storage=False)
        with tempfile.TemporaryDirectory(prefix="daily-funds-bundle-", dir=self.config.state_dir) as temp:
            temp_root = Path(temp)
            key_path = self._write_deploy_key(temp_root, self.config.git_ssh_key_b64)
            env = self._git_environment(temp_root, key_path)
            repo = temp_root / "private-db"
            self._clone_sparse(repo, env=env, ref=self.config.private_branch)
            # Do not reuse the shallow raw-ingestion boundary for a disaster
            # recovery artifact.  A standalone bundle must contain the raw
            # commit and its full ancestor closure so an empty Git repository
            # can verify it without depending on a live GitHub remote.
            shallow = self._git(["rev-parse", "--is-shallow-repository"], cwd=repo, env=env).strip()
            if shallow == "true":
                self._git(["fetch", "--unshallow", "origin", self.config.private_branch], cwd=repo, env=env)
            elif shallow != "false":
                raise IngestionError("GIT_BUNDLE_INVALID")
            bundle = temp_root / "daily-funds.bundle"
            self._git(["bundle", "create", str(bundle), "HEAD"], cwd=repo, env=env)
            payload = bundle.read_bytes()
            if not payload:
                raise IngestionError("GIT_BUNDLE_EMPTY")
            return payload
