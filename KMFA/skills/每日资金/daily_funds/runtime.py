"""Executable jobs for the cloud-only daily-funds worker."""

from __future__ import annotations

import json
import subprocess
import uuid
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping

from .config import ConfigError, DailyFundsConfig
from .control import ControlError, ThresholdControl
from .contracts import DailyBalance
from .ingestion import (
    ALLOWED_SUFFIXES,
    DownloadedAttachment,
    DwsHistoryClient,
    GitCommit,
    GitSparseWriter,
    HistoryPoller,
    IngestionError,
)
from .models import ParsedFacts, SourceRef, Transaction
from .parsing import ACCOUNT_FAMILY, ParseError, parse_attachment
from .publication import (
    D1Projection,
    OciColdBackup,
    PublicationCoordinator,
    PublicationError,
    R2Mirror,
    RestoreCoordinator,
    S3CompatibleStore,
)
from .reconcile import ReconciliationError, ReconciliationReport, account_key, account_key_hash, reconcile
from .state import RuntimeState, StatusWriter, atomic_json_write, iso_now

UTC = timezone.utc


@dataclass(frozen=True)
class TimedFacts:
    facts: ParsedFacts
    received_at: datetime


class DailyFundsRuntime:
    def __init__(self, config: DailyFundsConfig | None = None):
        self.config = config or DailyFundsConfig.from_env()
        self.state = RuntimeState(self.config.state_dir)
        self.status = StatusWriter(self.config.publication_dir)

    def _lease_call(self, name: str, *, ttl_seconds: int, code: str, callback):
        """Run one critical section under the persisted single-writer lease."""

        holder = str(uuid.uuid4())
        if not self.state.acquire_lease(name, holder, ttl_seconds=ttl_seconds):
            raise IngestionError(code)
        try:
            return callback()
        finally:
            self.state.release_lease(name, holder)

    def _current(self) -> dict[str, Any] | None:
        path = self.config.publication_dir / "current.json"
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if payload.get("publication", {}).get("status") != "VALID":
            return None
        return payload

    @property
    def _history_path(self) -> Path:
        return self.config.publication_dir / "history.json"

    def _history(self) -> dict[str, Any]:
        if not self._history_path.exists():
            return {"schema_version": "kmfa.daily_funds.history.v1", "days": {}}
        try:
            payload = json.loads(self._history_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"schema_version": "kmfa.daily_funds.history.v1", "days": {}}
        if not isinstance(payload, Mapping) or not isinstance(payload.get("days"), Mapping):
            return {"schema_version": "kmfa.daily_funds.history.v1", "days": {}}
        return {"schema_version": "kmfa.daily_funds.history.v1", "days": dict(payload["days"])}

    def _record_history(self, report: ReconciliationReport, publication_id: str | None = None) -> None:
        history = self._history()
        history["days"][report.business_date.isoformat()] = {
            "ending_available_fen": report.total_ending_fen,
            "direct_observation": True,
            "coverage_gap": False,
            "carried_forward": False,
            "account_ending_by_hash": {row.account_key_hash: row.ending_fen for row in report.account_reports},
            "publication_id": publication_id,
        }
        atomic_json_write(self._history_path, history)

    def _status_from_current(self, *, fallback_code: str, backup_state: str | None = None) -> dict[str, Any]:
        current = self._current()
        if current:
            publication = current["publication"]
            runtime = current.get("runtime") if isinstance(current.get("runtime"), Mapping) else {}
            return self.status.write(
                "已更新",
                fallback_code,
                effective_business_date=publication.get("business_date"),
                last_verified_at=publication.get("created_at"),
                publication_id=publication.get("publication_id"),
                backup_state=backup_state or str(runtime.get("oci_backup_state") or publication.get("oci_backup_state") or "UNKNOWN"),
            )
        return self.status.write("需处理", fallback_code, backup_state=backup_state or "UNKNOWN")

    def preflight(self) -> dict[str, Any]:
        """Record configuration readiness without issuing external requests."""

        missing = self.config.missing()
        if missing:
            return self.status.write("需处理", "CONFIG_INVALID", backup_state="UNKNOWN")
        try:
            self.config.validate()
        except ConfigError:
            return self.status.write("需处理", "CONFIG_INVALID", backup_state="UNKNOWN")
        # This only proves configuration shape, not credentials or source access.
        current = self._current()
        return self.status.write(
            "处理中" if current is None else "已更新",
            "CONFIG_READY",
            effective_business_date=current and current["publication"].get("business_date"),
            last_verified_at=current and current["publication"].get("created_at"),
            publication_id=current and current["publication"].get("publication_id"),
            backup_state="UNKNOWN",
        )

    @staticmethod
    def _source_ref(attachment: DownloadedAttachment) -> SourceRef:
        from zoneinfo import ZoneInfo

        day = attachment.message_at.astimezone(ZoneInfo("Asia/Shanghai")).date().strftime("%Y/%m/%d")
        occurrence = (
            f"Private-KMDatabase/KMFA/daily_funds/raw/occurrences/{day}/"
            f"{attachment.message_id_hash}/{attachment.index}.json"
        )
        return SourceRef(
            attachment_sha256=attachment.sha256,
            message_id_hash=attachment.message_id_hash,
            occurrence_path=occurrence,
            source_version=attachment.sha256,
        )

    def _parse(self, attachments: Iterable[DownloadedAttachment]) -> list[TimedFacts]:
        parsed: list[TimedFacts] = []
        for attachment in attachments:
            if attachment.family is None or Path(attachment.filename).suffix.lower() not in ALLOWED_SUFFIXES:
                raise ParseError("UNSUPPORTED_ATTACHMENT")
            parsed.append(TimedFacts(
                parse_attachment(
                    family=attachment.family,
                    filename=attachment.filename,
                    payload=attachment.payload,
                    source=self._source_ref(attachment),
                ),
                attachment.message_at,
            ))
        return parsed

    @staticmethod
    def _latest_complete_pair(parsed: Iterable[TimedFacts]) -> tuple[TimedFacts, TimedFacts]:
        """Return exactly one source-gated account/flow pair for one day.

        A repeated same occurrence is deduplicated before this function.  Two
        distinct candidate versions for either family are not "latest wins":
        the frozen unique-source gate requires an explicit source profile, so
        the run blocks rather than arbitrarily combining or discarding facts.
        """

        buckets: dict[str, dict[str, list[TimedFacts]]] = {}
        for item in parsed:
            category = "accounts" if item.facts.family == ACCOUNT_FAMILY else "transactions"
            buckets.setdefault(item.facts.business_date.isoformat(), {}).setdefault(category, []).append(item)
        candidates = [business_day for business_day, groups in buckets.items() if groups.get("accounts") and groups.get("transactions")]
        if not candidates:
            raise ReconciliationError("SOURCE_MATCH_ZERO")
        selected_day = max(candidates)
        groups = buckets[selected_day]
        if len(groups["accounts"]) != 1 or len(groups["transactions"]) != 1:
            raise ReconciliationError("SOURCE_MATCH_MULTIPLE")
        accounts = groups["accounts"][0]
        transactions = groups["transactions"][0]
        if accounts.facts.business_date != transactions.facts.business_date:
            raise ReconciliationError("BUSINESS_DATE_MISMATCH")
        return accounts, transactions

    def _prior_account_balances(self, business_date: date | None = None) -> Mapping[str, int]:
        if business_date is not None:
            previous_day = (business_date - timedelta(days=1)).isoformat()
            record = self._history().get("days", {}).get(previous_day)
            if isinstance(record, Mapping) and isinstance(record.get("account_ending_by_hash"), Mapping):
                return {str(key): int(value) for key, value in record["account_ending_by_hash"].items() if isinstance(value, int)}
        current = self._current()
        if not current:
            return {}
        values = current.get("summary", {}).get("account_ending_by_hash")
        if not isinstance(values, Mapping):
            return {}
        return {str(key): int(value) for key, value in values.items() if isinstance(value, int)}

    def _daily_balances(self, report: ReconciliationReport) -> tuple[DailyBalance, ...]:
        """Build the daily-balance series without inventing missing business days.

        The only primary evidence is a valid daily publication.  Saturday and
        Sunday are the frozen non-reporting default and may carry the last
        valid balance forward.  Every missing weekday remains explicitly
        ``coverage_gap`` (using the last value only as a graph continuity
        placeholder) and is excluded from floating-threshold coverage.  A
        public holiday is intentionally treated as a weekday gap unless a
        future, approved reporting calendar says otherwise; silently calling it
        non-reporting would overstate coverage.
        """

        existing: dict[str, DailyBalance] = {}
        for business_day, row in self._history().get("days", {}).items():
            try:
                day = datetime.fromisoformat(str(business_day)).date()
                if day > report.business_date:
                    continue
                existing[day.isoformat()] = DailyBalance(
                    day,
                    int(row["ending_available_fen"]),
                    bool(row.get("direct_observation")),
                    bool(row.get("coverage_gap")),
                    bool(row.get("carried_forward")),
                )
            except (KeyError, TypeError, ValueError):
                continue
        current = self._current()
        if current:
            for row in current.get("daily_balances", []):
                try:
                    business_day = datetime.fromisoformat(str(row["business_date"])).date()
                    # A historical backfill publication must not include a
                    # later live day merely because the local UI pointer is
                    # newer.  Only direct rows are source evidence; gaps and
                    # carries are deterministically rebuilt below.
                    if business_day > report.business_date or not bool(row.get("direct_observation")):
                        continue
                    existing[business_day.isoformat()] = DailyBalance(
                        business_day,
                        int(row["ending_available_fen"]),
                        True,
                        False,
                        False,
                    )
                except (KeyError, TypeError, ValueError):
                    continue
        existing[report.business_date.isoformat()] = DailyBalance(report.business_date, report.total_ending_fen, True, False)
        if not existing:
            return ()
        direct_days = sorted(date.fromisoformat(key) for key in existing)
        first_day = direct_days[0]
        last_day = report.business_date
        normalized: list[DailyBalance] = []
        previous: DailyBalance | None = None
        day = first_day
        while day <= last_day:
            direct = existing.get(day.isoformat())
            if direct is not None:
                normalized.append(direct)
                previous = direct
            elif previous is not None:
                if day.weekday() >= 5:
                    normalized.append(DailyBalance(
                        day,
                        previous.ending_available_fen,
                        False,
                        False,
                        True,
                    ))
                else:
                    # Preserve the last known amount only to make the gap
                    # inspectable in the graph.  It cannot affect threshold
                    # math because ``coverage_gap`` rows are excluded.
                    normalized.append(DailyBalance(
                        day,
                        previous.ending_available_fen,
                        False,
                        True,
                        False,
                    ))
            day += timedelta(days=1)
        return tuple(normalized)

    @staticmethod
    def _transaction_projection_rows(facts: ParsedFacts) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for transaction in facts.transactions:
            identity = "\x1f".join((transaction.source.attachment_sha256, transaction.company, transaction.bank, transaction.account, transaction.transaction_id))
            rows.append({
                "transaction_key_hash": sha256(identity.encode("utf-8")).hexdigest(),
                "business_date": transaction.business_date.isoformat(),
                "inflow_fen": transaction.inflow_fen,
                "outflow_fen": transaction.outflow_fen,
                "adjustment_fen": transaction.adjustment_fen,
                "internal_transfer": transaction.is_internal_transfer,
                "source_version": transaction.source.source_version,
                "message_id_hash": transaction.source.message_id_hash,
            })
        return rows

    @staticmethod
    def _account_projection_rows(facts: ParsedFacts) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for account in facts.accounts:
            key = account_key(account.company, account.bank, account.account)
            key_hash = account_key_hash(key)
            rows.append({
                "account_key_hash": key_hash,
                "business_date": account.business_date.isoformat(),
                "company_id": account.company,
                "bank_id": account.bank,
                # D1 and the browser never receive a plaintext account number.
                "account_alias": key_hash,
                "opening_available_fen": account.opening_available_fen,
                "ending_available_fen": account.ending_available_fen,
                "source_version": account.source.source_version,
                "message_id_hash": account.source.message_id_hash,
            })
        return rows

    @staticmethod
    def _deduplicated_attachments(attachments: Iterable[DownloadedAttachment]) -> tuple[DownloadedAttachment, ...]:
        seen: set[tuple[str, int, str]] = set()
        unique: list[DownloadedAttachment] = []
        for attachment in attachments:
            key = (attachment.message_id_hash, attachment.index, attachment.sha256)
            if key not in seen:
                seen.add(key)
                unique.append(attachment)
        return tuple(unique)

    def _coordinator(self) -> PublicationCoordinator:
        r2 = S3CompatibleStore(
            endpoint_url=self.config.r2_endpoint_url,
            bucket=self.config.r2_bucket,
            access_key_id=self.config.r2_access_key_id,
            secret_access_key=self.config.r2_secret_access_key,
            region="auto",
        )
        oci = S3CompatibleStore(
            endpoint_url=self.config.oci_endpoint_url,
            bucket=self.config.oci_bucket,
            access_key_id=self.config.oci_access_key_id,
            secret_access_key=self.config.oci_secret_access_key,
            region=self.config.oci_region,
        )
        return PublicationCoordinator(
            publication_dir=self.config.publication_dir,
            status=self.status,
            d1=D1Projection(self.config),
            r2=R2Mirror(r2),
            oci=OciColdBackup(oci),
        )

    def poll(
        self,
        *,
        now: datetime | None = None,
        start_override: datetime | None = None,
        cursor_key: str = "history_next_cursor",
        high_water_key: str = "history_high_water_at",
        advance_pointer: bool = True,
    ) -> dict[str, Any]:
        try:
            self.config.validate()
        except ConfigError:
            return self.status.write("需处理", "CONFIG_INVALID")
        now = now or datetime.now(UTC)
        holder = str(uuid.uuid4())
        client = DwsHistoryClient(self.config)
        poller = HistoryPoller(self.state, client)
        writer = GitSparseWriter(self.config)
        all_attachments: list[DownloadedAttachment] = []
        commits: list[GitCommit] = []
        self.status.write("处理中", "POLLING")

        def persist_page(page) -> None:
            selected = client.selected_messages(page)
            page_attachments: list[DownloadedAttachment] = []
            for message in selected:
                attachment_count = client.attachment_count(message)
                if attachment_count == 0:
                    raise IngestionError("SOURCE_ATTACHMENT_MISSING")
                for index in range(attachment_count):
                    page_attachments.append(client.download(message, index))
            if page_attachments:
                commit = self._lease_call(
                    "git_writer_lock",
                    ttl_seconds=13 * 60,
                    code="GIT_WRITER_LOCK_HELD",
                    callback=lambda: writer.persist(page_attachments),
                )
                commits.append(commit)
                for attachment in page_attachments:
                    occurrence_key = f"{attachment.message_id_hash}:{attachment.index}:{attachment.sha256}"
                    self.state.note_inbox(occurrence_key, attachment.message_id_hash, attachment.sha256, "GIT_PERSISTED")
                all_attachments.extend(commit.verified_attachments)

        try:
            pages = poller.poll(
                now=now,
                persist_page=persist_page,
                holder=holder,
                cursor_key=cursor_key,
                high_water_key=high_water_key,
                start_override=start_override,
            )
            if not all_attachments:
                raise IngestionError("SOURCE_MATCH_ZERO")
            verified_attachments = self._deduplicated_attachments(all_attachments)
            # The raw Git authority has been re-opened before this point.  R2
            # must mirror those exact bytes before parsing or reconciliation.
            coordinator = self._coordinator()
            r2_result = self._lease_call(
                "publisher_lock",
                ttl_seconds=13 * 60,
                code="PUBLISHER_LOCK_HELD",
                callback=lambda: coordinator.r2.mirror(verified_attachments, git_commit_sha=commits[-1].commit_sha),
            )
            parsed = self._parse(verified_attachments)
            account_facts, transaction_facts = self._latest_complete_pair(parsed)
            report = reconcile(
                (account_facts.facts, transaction_facts.facts),
                previous_ending_by_account=self._prior_account_balances(account_facts.facts.business_date),
            )
            balances = self._daily_balances(report)
            custom_line = ThresholdControl(self.config.control_dir).line(balances, report.business_date)
            projection = self._lease_call(
                "publisher_lock",
                ttl_seconds=13 * 60,
                code="PUBLISHER_LOCK_HELD",
                callback=lambda: coordinator.publish(
                    report=report,
                    git_commit=commits[-1],
                    attachments=verified_attachments,
                    daily_balances=balances,
                    transaction_rows=self._transaction_projection_rows(transaction_facts.facts),
                    account_rows=self._account_projection_rows(account_facts.facts),
                    private_publication_sink=lambda publication: self._lease_call(
                        "git_writer_lock",
                        ttl_seconds=13 * 60,
                        code="GIT_WRITER_LOCK_HELD",
                        callback=lambda: writer.persist_publication(publication),
                    ),
                    git_bundle_sink=lambda: self._lease_call(
                        "git_writer_lock",
                        ttl_seconds=13 * 60,
                        code="GIT_WRITER_LOCK_HELD",
                        callback=writer.bundle_head,
                    ),
                    advance_pointer=advance_pointer,
                    extra_floating_lines=(custom_line,) if custom_line is not None else (),
                    pre_mirrored=r2_result,
                ),
            )
            self._record_history(report, str(projection.publication["publication_id"]))
            if not advance_pointer:
                self._status_from_current(fallback_code="BACKFILLING")
            for attachment in verified_attachments:
                occurrence_key = f"{attachment.message_id_hash}:{attachment.index}:{attachment.sha256}"
                self.state.mark_inbox(occurrence_key, "VALID_PUBLISHED")
            return {
                "ok": True,
                "pages": pages,
                "attachments": len(verified_attachments),
                "publication_id": projection.publication["publication_id"],
                "backup_state": projection.oci_backup_state,
            }
        except (IngestionError, ParseError, ReconciliationError, PublicationError, ControlError) as exc:
            code = getattr(exc, "code", str(exc).split(":", 1)[0])
            human_status = "处理中" if str(code).endswith("_LOCK_HELD") else "需处理"
            self.status.write(human_status, str(code))
            return {"ok": False, "code": str(code)}

    def auth_probe(self) -> dict[str, Any]:
        try:
            self.config.validate(include_storage=False)
        except ConfigError:
            return self.status.write("需处理", "CONFIG_INVALID")
        client = DwsHistoryClient(self.config)
        now = datetime.now(UTC)
        try:
            self._lease_call(
                "auth_probe_lock",
                ttl_seconds=55,
                code="AUTH_PROBE_LOCK_HELD",
                callback=lambda: client.search(now - timedelta(minutes=1), now, "0"),
            )
        except IngestionError as exc:
            if exc.code == "AUTH_PROBE_LOCK_HELD":
                return self.status.write("处理中", exc.code)
            self.state.queue_incident(exc.code)
            return self.status.write("需处理", exc.code)
        return self._status_from_current(fallback_code="AUTH_OK")

    def backfill(self, *, now: datetime | None = None, max_days: int = 7) -> dict[str, Any]:
        """Process bounded historical days without replacing the live pointer.

        The live ``*/15`` job always owns the current day.  This job starts at
        the oldest required day and advances its durable planner only after a
        full window has been handled, so a restart cannot skip a date.
        """

        now = now or datetime.now(UTC)
        try:
            from zoneinfo import ZoneInfo
            local_today = now.astimezone(ZoneInfo("Asia/Shanghai")).date()
            local_zone = ZoneInfo("Asia/Shanghai")
        except Exception:  # zoneinfo is part of Python, but keep fail-closed
            return self.status.write("需处理", "TIMEZONE_UNAVAILABLE")
        first_required = local_today - timedelta(days=360)
        raw_cursor = self.state.get("backfill_next_business_date")
        try:
            next_day = date.fromisoformat(raw_cursor) if raw_cursor else first_required
        except ValueError:
            return self.status.write("需处理", "BACKFILL_CURSOR_INVALID")
        completed: list[str] = []
        for _ in range(max(1, min(max_days, 14))):
            if next_day >= local_today:
                break
            start = datetime.combine(next_day, time.min, tzinfo=local_zone).astimezone(UTC)
            end = datetime.combine(next_day, time.max, tzinfo=local_zone).astimezone(UTC)
            key_day = next_day.strftime("%Y%m%d")
            result = self.poll(
                now=end,
                start_override=start,
                cursor_key=f"backfill_cursor_{key_day}",
                high_water_key=f"backfill_high_water_{key_day}",
                advance_pointer=False,
            )
            if not result.get("ok"):
                return {"ok": False, "completed_days": completed, "code": result.get("code", "BACKFILL_FAILED")}
            completed.append(next_day.isoformat())
            next_day += timedelta(days=1)
            self.state.put("backfill_next_business_date", next_day.isoformat())
        status = self._status_from_current(fallback_code="BACKFILL_COMPLETE" if next_day >= local_today else "BACKFILLING")
        return {
            "ok": True,
            "completed_days": completed,
            "next_business_date": next_day.isoformat(),
            "complete": next_day >= local_today,
            "status": status["human_status"],
        }

    def keepalive(self) -> dict[str, Any]:
        try:
            self.config.validate(include_storage=False)
        except ConfigError:
            return self.status.write("需处理", "CONFIG_INVALID")
        env = DwsHistoryClient(self.config)._environment()
        try:
            completed = self._lease_call(
                "keepalive_lock",
                ttl_seconds=55,
                code="KEEPALIVE_LOCK_HELD",
                callback=lambda: subprocess.run(
                    [self.config.dws_bin, "auth", "status", "--format", "json"],
                    capture_output=True, text=True, check=False, timeout=60, env=env,
                ),
            )
            payload = json.loads(completed.stdout) if completed.returncode == 0 else {}
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            payload = {}
            completed = None
        except IngestionError as exc:
            if exc.code == "KEEPALIVE_LOCK_HELD":
                return self.status.write("处理中", exc.code)
            payload = {}
            completed = None
        explicit_ok = bool(isinstance(payload, Mapping) and (payload.get("authenticated") is True or payload.get("loggedIn") is True))
        if completed is None or not explicit_ok:
            self.state.queue_incident("AUTH_REQUIRED")
            return self.status.write("需处理", "AUTH_REQUIRED")
        return self._status_from_current(fallback_code="KEEPALIVE_OK")

    def observer(self) -> dict[str, Any]:
        """Autonomous post-deploy observer; it never invokes another skill."""

        current = self._current()
        if current is None:
            return self.status.write("需处理", "SOURCE_MISSING")
        publication = current.get("publication", {})
        try:
            business_date = datetime.fromisoformat(str(publication["business_date"])).date()
        except (KeyError, ValueError):
            return self.status.write("需处理", "PUBLICATION_INVALID")
        stale = (datetime.now(UTC).date() - business_date).days > 1
        status = self.status.write(
            "需处理" if stale else "已更新",
            "STALE" if stale else "OBSERVER_OK",
            effective_business_date=business_date.isoformat(),
            last_verified_at=iso_now(),
            publication_id=publication.get("publication_id"),
            backup_state=str(current.get("runtime", {}).get("oci_backup_state") or publication.get("oci_backup_state") or "UNKNOWN"),
        )
        atomic_json_write(self.config.publication_dir / "observer.json", {
            "schema_version": "kmfa.daily_funds.observer.v1",
            "observed_at": iso_now(),
            "publication_id": publication.get("publication_id"),
            "result": "STALE" if stale else "OK",
        })
        return status

    def cold_backup(self) -> dict[str, Any]:
        """Retry OCI recovery artifacts without moving the publication pointer."""

        try:
            self.config.validate()
        except ConfigError:
            return self.status.write("需处理", "CONFIG_INVALID")
        current = self._current()
        if current is None:
            return self.status.write("需处理", "SOURCE_MISSING")
        publication = current.get("publication", {})
        publication_id = str(publication.get("publication_id") or "")
        r2_sha = str(publication.get("r2_manifest_sha256") or "")
        if len(publication_id) != 64 or len(r2_sha) != 64:
            return self.status.write("需处理", "PUBLICATION_INVALID")
        try:
            r2_store = S3CompatibleStore(
                endpoint_url=self.config.r2_endpoint_url,
                bucket=self.config.r2_bucket,
                access_key_id=self.config.r2_access_key_id,
                secret_access_key=self.config.r2_secret_access_key,
                region="auto",
            )
            d1 = D1Projection(self.config)
            oci_store = S3CompatibleStore(
                endpoint_url=self.config.oci_endpoint_url,
                bucket=self.config.oci_bucket,
                access_key_id=self.config.oci_access_key_id,
                secret_access_key=self.config.oci_secret_access_key,
                region=self.config.oci_region,
            )
            OciColdBackup(oci_store).backup(
                publication_id=publication_id,
                publication_sha256=sha256(json.dumps(publication, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n").hexdigest(),
                git_bundle=self._lease_call(
                    "git_writer_lock",
                    ttl_seconds=13 * 60,
                    code="GIT_WRITER_LOCK_HELD",
                    callback=GitSparseWriter(self.config).bundle_head,
                ),
                d1_export=d1.export(publication_id),
                r2_inventory=r2_store.get_bytes(f"daily-funds/manifests/{r2_sha}.json"),
            )
        except (IngestionError, PublicationError) as exc:
            return self._status_from_current(fallback_code="OCI_BACKUP_LAG", backup_state="LAG")
        # Keep the canonical publication byte-identical to its D1/Git form;
        # only the operational hand-off changes after a retry succeeds.
        current["runtime"] = {"oci_backup_state": "OK"}
        atomic_json_write(self.config.publication_dir / "current.json", current)
        return self.status.write(
            "已更新",
            "OCI_BACKUP_OK",
            effective_business_date=publication.get("business_date"),
            last_verified_at=publication.get("created_at"),
            publication_id=publication_id,
            backup_state="OK",
        )

    def restore_drill(self) -> dict[str, Any]:
        """Monthly non-production D1 rebuild; it never moves the live pointer."""

        try:
            self.config.validate()
        except ConfigError:
            return self.status.write("需处理", "CONFIG_INVALID")
        drill_database_id = self.config.restore_drill_d1_database_id
        if not drill_database_id or drill_database_id == self.config.d1_database_id:
            return self.status.write("需处理", "RESTORE_DRILL_CONFIG_INVALID")
        current = self._current()
        if current is None:
            return self.status.write("需处理", "SOURCE_MISSING")
        publication_id = str(current.get("publication", {}).get("publication_id") or "")
        if len(publication_id) != 64:
            return self.status.write("需处理", "PUBLICATION_INVALID")
        try:
            oci_store = S3CompatibleStore(
                endpoint_url=self.config.oci_endpoint_url,
                bucket=self.config.oci_bucket,
                access_key_id=self.config.oci_access_key_id,
                secret_access_key=self.config.oci_secret_access_key,
                region=self.config.oci_region,
            )
            self._lease_call(
                "publisher_lock",
                ttl_seconds=13 * 60,
                code="PUBLISHER_LOCK_HELD",
                callback=lambda: RestoreCoordinator(
                    d1=D1Projection(replace(self.config, d1_database_id=drill_database_id)),
                    oci=OciColdBackup(oci_store),
                ).restore(publication_id),
            )
        except (IngestionError, PublicationError) as exc:
            code = getattr(exc, "code", "RESTORE_DRILL_FAILED")
            status = "处理中" if code == "PUBLISHER_LOCK_HELD" else "需处理"
            return self.status.write(status, code)
        return self._status_from_current(fallback_code="RESTORE_DRILL_OK")

    def restore(self, *, publication_id: str) -> dict[str, Any]:
        """Rebuild an empty/corrupt D1 and private pointer from OCI artifacts.

        This is the only rollback path: it validates the immutable OCI
        manifest, rebuilds D1, reads its Oracle, and only then atomically moves
        the local UI pointer.  It never trusts a previous SQLite journal.
        """

        try:
            self.config.validate()
        except ConfigError:
            return self.status.write("需处理", "CONFIG_INVALID")
        if len(publication_id) != 64 or any(char not in "0123456789abcdef" for char in publication_id):
            return self.status.write("需处理", "RESTORE_PUBLICATION_ID_INVALID")
        try:
            oci_store = S3CompatibleStore(
                endpoint_url=self.config.oci_endpoint_url,
                bucket=self.config.oci_bucket,
                access_key_id=self.config.oci_access_key_id,
                secret_access_key=self.config.oci_secret_access_key,
                region=self.config.oci_region,
            )
            restored = self._lease_call(
                "publisher_lock",
                ttl_seconds=13 * 60,
                code="PUBLISHER_LOCK_HELD",
                callback=lambda: RestoreCoordinator(
                    d1=D1Projection(self.config),
                    oci=OciColdBackup(oci_store),
                ).restore(publication_id),
            )
        except (IngestionError, PublicationError) as exc:
            code = getattr(exc, "code", "RESTORE_FAILED")
            status = "处理中" if code == "PUBLISHER_LOCK_HELD" else "需处理"
            return self.status.write(status, code, backup_state="LAG")

        by_company: dict[str, int] = {}
        by_bank: dict[str, int] = {}
        by_account: dict[str, int] = {}
        for account in restored.account_rows:
            ending = int(account["ending_available_fen"])
            by_company[str(account["company_id"])] = by_company.get(str(account["company_id"]), 0) + ending
            by_bank[str(account["bank_id"])] = by_bank.get(str(account["bank_id"]), 0) + ending
            by_account[str(account["account_key_hash"])] = ending
        snapshot = {
            "schema_version": "kmfa.daily_funds.current_projection.v1",
            "publication": dict(restored.publication),
            "summary": {
                "total_available_fen": sum(by_account.values()),
                "risk_label": restored.publication.get("threshold_snapshot", {}).get("fixed_risk"),
                "dynamic_flag": restored.publication.get("threshold_snapshot", {}).get("dynamic_flag"),
                "by_company_ending_fen": dict(sorted(by_company.items())),
                "by_bank_ending_fen": dict(sorted(by_bank.items())),
                "account_ending_by_hash": dict(sorted(by_account.items())),
            },
            "daily_balances": [
                {
                    "business_date": row.business_day.isoformat(),
                    "ending_available_fen": row.ending_available_fen,
                    "direct_observation": row.direct_observation,
                    "coverage_gap": row.coverage_gap,
                    "carried_forward": row.carried_forward,
                }
                for row in restored.daily_balances
            ],
            "transactions": [dict(row) for row in restored.transaction_rows],
            "runtime": {"oci_backup_state": "OK", "restored_at": iso_now()},
        }
        atomic_json_write(self.config.publication_dir / "current.json", snapshot)
        return self.status.write(
            "已更新",
            "RESTORE_OK",
            effective_business_date=str(restored.publication.get("business_date") or "") or None,
            last_verified_at=iso_now(),
            publication_id=publication_id,
            backup_state="OK",
        )

    def healthcheck(self) -> dict[str, Any]:
        """Container liveness check deliberately does not claim source readiness."""

        self.config.state_dir.mkdir(parents=True, exist_ok=True)
        self.config.publication_dir.mkdir(parents=True, exist_ok=True)
        return {
            "status": "ok",
            "runtime": "daily-funds-independent",
            # Config shape is not an authenticated source.  A real source is
            # only evidenced by a verified publication/status record.
            "config_complete": not bool(self.config.missing()),
            "source_ready": False,
            "recorded_status": self.status.read(),
        }
