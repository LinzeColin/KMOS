"""Executable jobs for the cloud-only daily-funds worker."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from .config import ConfigError, DailyFundsConfig
from .control import ControlError, ThresholdControl
from .contracts import HARD_THRESHOLD_FEN, RISK_LABELS, SOFT_THRESHOLD_FEN, DailyBalance
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
from .parsing import (
    ACCOUNT_FAMILY,
    PARSER_VERSION,
    ParseError,
    TRANSACTION_FAMILIES,
    attachment_capability_metadata,
    parse_attachment,
)
from .publication import (
    D1Projection,
    OciColdBackup,
    OciParStore,
    PublicationCoordinator,
    PublicationError,
    R2Mirror,
    RestoreCoordinator,
    S3CompatibleStore,
)
from .reconcile import ReconciliationError, ReconciliationReport, account_key, account_key_hash, reconcile
from .state import RuntimeState, StatusWriter, atomic_json_write, iso_now

UTC = timezone.utc

_CLOUD_RUNTIME_PATHS = {
    "state": Path("/var/lib/kmfa/daily-funds-state"),
    "publication": Path("/var/lib/kmfa/daily-funds-publication"),
    "control": Path("/var/lib/kmfa/daily-funds-control"),
    "dws_config": Path("/var/lib/kmfa/daily-funds-dws/config"),
    "dws_keyring": Path("/var/lib/kmfa/daily-funds-dws/keyring"),
}
_FORBIDDEN_MOUNT_PREFIXES = ("/Users", "/Volumes", "/home", "/mnt", "/media")
_COUPLED_PROCESS_MARKERS = (
    b"/opt/kmfa/kmos/kmfa/skills/",
    b"run_skill.sh",
    b"onedrive",
    b"launchd",
)
_POST_DEPLOY_OBSERVER_REQUIRED_BUSINESS_DAYS = 5
_FLOW_STATE_SCHEMA = "kmfa.daily_funds.flow_state.v1"
_OPERATION_RECEIPT_JOBS = frozenset({
    "preflight",
    "bootstrap-dws-auth",
    "runtime-audit",
    "poll",
    "auth-probe",
    "keepalive",
    "backfill",
    "observer",
    "cold-backup",
    "restore-drill",
    "restore",
    "healthcheck",
})
_OPERATION_RECEIPT_STATES = frozenset({"SUCCEEDED", "FAILED"})
_SOURCE_INTEGRITY_PARSE_CODES = frozenset({
    "SOURCE_LINEAGE_INVALID",
    "SOURCE_VERSION_MISMATCH",
    "SOURCE_PAYLOAD_HASH_MISMATCH",
})


@dataclass(frozen=True)
class TimedFacts:
    facts: ParsedFacts
    received_at: datetime


@dataclass(frozen=True)
class AttachmentCapabilityInspection:
    """Values-free outcome of opening Git-readback attachment bytes.

    A successful parser-open is evidence that a format is available to the
    deterministic pipeline.  A non-integrity parser failure is equally useful
    evidence during historical discovery, but it must never be mistaken for a
    reconciled, publishable fact set.
    """

    parsed: tuple[TimedFacts, ...]
    failures: tuple[ParseError, ...]


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

    def _dws_client(self) -> DwsHistoryClient:
        return DwsHistoryClient(self.config, event_sink=self.state.record_network_event)

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

    def _oci_store(self):
        """Return the one configured OCI cold-backup transport.

        A bucket-scoped PAR is preferred because it cannot grant the runtime
        access outside the dedicated daily-funds bucket.  The S3/HMAC path is
        retained only for explicitly configured legacy recovery deployments.
        """

        if self.config.oci_par_url:
            return OciParStore(par_url=self.config.oci_par_url)
        return S3CompatibleStore(
            endpoint_url=self.config.oci_endpoint_url,
            bucket=self.config.oci_bucket,
            access_key_id=self.config.oci_access_key_id,
            secret_access_key=self.config.oci_secret_access_key,
            region=self.config.oci_region,
        )

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

    @staticmethod
    def _read_json_object(path: Path) -> dict[str, Any] | None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return dict(payload) if isinstance(payload, Mapping) else None

    @staticmethod
    def _lower_hex(value: object, length: int) -> str | None:
        if not isinstance(value, str) or len(value) != length:
            return None
        return value if all(character in "0123456789abcdef" for character in value) else None

    @staticmethod
    def _flow_code(value: object, *, default: str = "UNKNOWN") -> str:
        text = str(value or default).strip().upper()
        token = "".join(
            character for character in text
            if character.isascii() and (character.isupper() or character.isdigit() or character == "_")
        )
        return token[:80] or default

    @staticmethod
    def _flow_timestamp(value: object) -> str | None:
        if not isinstance(value, str) or not value or len(value) > 40:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return value if parsed.tzinfo is not None else None

    def _deployment_marker(self) -> str | None:
        """Hash a container-instance marker without persisting its raw value.

        A named volume survives a redeploy, so a five-day observation window
        cannot be keyed merely to the SQLite file.  Docker provides a fresh
        container hostname for a replacement deployment; operators may supply
        a more explicit marker, but either source is one-way hashed before it
        reaches the journal or shared status projection.  This is intentionally
        *not* a source/image identity assertion; those remain production-Oracle
        evidence owned by T10.
        """

        raw = os.environ.get("DAILY_FUNDS_DEPLOYMENT_MARKER", "").strip()
        if not raw:
            raw = os.environ.get("HOSTNAME", "").strip()
        if not raw:
            try:
                raw = Path("/etc/hostname").read_text(encoding="utf-8").strip()
            except OSError:
                raw = ""
        if not raw or len(raw) > 512:
            return None
        return sha256(raw.encode("utf-8")).hexdigest()

    def _restore_drill_state(self) -> tuple[str, str | None]:
        receipt = self._read_json_object(self.config.publication_dir / "restore_drill.json")
        if receipt is None:
            return "NOT_YET_RUN", None
        result = self._flow_code(receipt.get("result"))
        observed_at = self._flow_timestamp(receipt.get("observed_at"))
        if result not in {"OK", "IN_PROGRESS", "NEEDS_ATTENTION"}:
            return "UNKNOWN", observed_at
        return result, observed_at

    def _write_flow_state(
        self,
        *,
        stage: str | None,
        status: Mapping[str, Any] | None = None,
        observer_state: str | None = None,
        observer_result: str | None = None,
        operation_job: str | None = None,
        operation_state: str | None = None,
        operation_code: str | None = None,
        operation_finished_at: str | None = None,
    ) -> dict[str, Any]:
        """Write the sole values-free business-flow hand-off for KMFA status.

        It is deliberately a worker projection, not a second health service:
        the existing KMFA ``/api/排程健康`` endpoint consumes this file along
        with the canonical runtime status.  No source payload, account, amount,
        message/group ID, attachment hash or deployment identifier is written.
        """

        previous = self._read_json_object(self.config.publication_dir / "flow_state.json") or {}
        prior_observer = previous.get("post_deploy_observer")
        if not isinstance(prior_observer, Mapping):
            prior_observer = {}
        prior_business = previous.get("business_flow")
        if not isinstance(prior_business, Mapping):
            prior_business = {}
        current_status = dict(status or self.status.read() or {})
        human_status = str(current_status.get("human_status") or "需处理")
        if human_status not in {"已更新", "处理中", "需处理"}:
            human_status = "需处理"
        current = self._current()
        audit = self._read_json_object(self.config.publication_dir / "runtime_audit.json") or {}
        audit_result = self._flow_code(audit.get("result"))
        runtime_state = {
            "OK": "RUNTIME_AUDITED",
            "NEEDS_ATTENTION": "RUNTIME_NEEDS_ATTENTION",
        }.get(audit_result, "UNKNOWN")
        window = self.state.observer_window()
        comparisons = self.state.observer_days(limit=_POST_DEPLOY_OBSERVER_REQUIRED_BUSINESS_DAYS)
        restore_state, restore_at = self._restore_drill_state()
        resolved_observer_state = self._flow_code(
            observer_state if observer_state is not None else prior_observer.get("state"),
            default="NOT_STARTED",
        )
        resolved_observer_result = self._flow_code(
            observer_result if observer_result is not None else prior_observer.get("last_comparison"),
            default="NOT_STARTED",
        )
        last_observed_at = (
            comparisons[-1]["observed_at"] if comparisons else self._flow_timestamp(prior_observer.get("last_observed_at"))
        )
        # Each cron invocation has a distinct operational meaning.  In
        # particular a healthy minute-level auth probe must not overwrite the
        # most recent 15-minute source-poll outcome just because both jobs
        # share the same status writer.  Keep only a bounded, values-free last
        # receipt per known job in the existing flow-state hand-off.
        operations: dict[str, dict[str, str]] = {}
        prior_operations = previous.get("operations")
        if isinstance(prior_operations, Mapping):
            for job in _OPERATION_RECEIPT_JOBS:
                row = prior_operations.get(job)
                if not isinstance(row, Mapping):
                    continue
                receipt_state = self._flow_code(row.get("state"))
                receipt_code = self._flow_code(row.get("code"))
                finished_at = self._flow_timestamp(row.get("finished_at"))
                if receipt_state in _OPERATION_RECEIPT_STATES and finished_at is not None:
                    operations[job] = {
                        "state": receipt_state,
                        "code": receipt_code,
                        "finished_at": finished_at,
                    }
        if operation_job is not None:
            if operation_job not in _OPERATION_RECEIPT_JOBS:
                raise ValueError("invalid operation receipt job")
            receipt_state = self._flow_code(operation_state)
            finished_at = self._flow_timestamp(operation_finished_at) or iso_now()
            if receipt_state not in _OPERATION_RECEIPT_STATES:
                raise ValueError("invalid operation receipt state")
            operations[operation_job] = {
                "state": receipt_state,
                "code": self._flow_code(operation_code),
                "finished_at": finished_at,
            }
        if stage is None and prior_business:
            prior_human_status = str(prior_business.get("human_status") or "需处理")
            if prior_human_status not in {"已更新", "处理中", "需处理"}:
                prior_human_status = "需处理"
            business_flow = {
                "stage": self._flow_code(prior_business.get("stage")),
                "human_status": prior_human_status,
                "machine_code": self._flow_code(prior_business.get("machine_code")),
                "effective_business_date": str(prior_business.get("effective_business_date") or "")[:10] or None,
                "last_verified_at": self._flow_timestamp(prior_business.get("last_verified_at")),
                "last_status_at": self._flow_timestamp(prior_business.get("last_status_at")),
                # The pointer is still read afresh: a stale flow receipt cannot
                # claim that a current valid publication exists.
                "publication_present": current is not None,
            }
        else:
            business_flow = {
                "stage": self._flow_code(stage),
                "human_status": human_status,
                "machine_code": self._flow_code(current_status.get("machine_code")),
                "effective_business_date": str(current_status.get("effective_business_date") or "")[:10] or None,
                "last_verified_at": self._flow_timestamp(current_status.get("last_verified_at")),
                "last_status_at": self._flow_timestamp(current_status.get("updated_at")),
                "publication_present": current is not None,
            }
        payload = {
            "schema_version": _FLOW_STATE_SCHEMA,
            "updated_at": iso_now(),
            "deployment": {
                "runtime_state": runtime_state,
                "instance_state": "OBSERVED" if window is not None else "UNKNOWN",
                # The worker can prove a running instance but cannot infer the
                # live source SHA/image digest from that fact.
                "identity_state": "UNKNOWN",
                "runtime_audit_at": self._flow_timestamp(audit.get("observed_at")),
            },
            "schedules": dict(StatusWriter.SCHEDULES),
            "business_flow": business_flow,
            "operations": operations,
            # This aggregate is intentionally values-free: it reveals only
            # parser type/outcome counts, never source IDs, filenames, hashes,
            # document text or financial amounts.
            "attachment_capabilities": self.state.capability_matrix(),
            "self_healing": {
                "state": "JOURNAL_READY",
                "restart_recovery": "CURSOR_INBOX_LEASES",
                "restore_drill": restore_state,
                "restore_drill_at": restore_at,
            },
            "post_deploy_observer": {
                "schedule": StatusWriter.SCHEDULES["observer"],
                "state": resolved_observer_state,
                "last_comparison": resolved_observer_result,
                "required_business_days": _POST_DEPLOY_OBSERVER_REQUIRED_BUSINESS_DAYS,
                "completed_business_days": len(comparisons) if window is not None else 0,
                "baseline_business_date": window["baseline_business_date"] if window is not None else None,
                "started_at": window["started_at"] if window is not None else None,
                "last_observed_at": last_observed_at,
                "comparisons": comparisons,
            },
        }
        atomic_json_write(self.config.publication_dir / "flow_state.json", payload)
        return payload

    def record_operation_receipt(self, *, job: str, succeeded: bool, code: str) -> dict[str, Any]:
        """Persist one redacted scheduler receipt without changing business truth.

        The runner calls this only after a job has reached a terminal result.
        It records operational success separately from a financial publication:
        ``auth-probe=SUCCEEDED`` means the isolated DWS session was usable, not
        that any account balance or transaction pair was published.
        """

        if job not in _OPERATION_RECEIPT_JOBS:
            raise ValueError("invalid operation receipt job")
        stage = None
        if job == "poll":
            # A normal live poll only succeeds after a valid publication has
            # been produced; all no-source/parse/storage outcomes are explicit
            # non-publication states.
            stage = "POLL_PUBLISHED" if succeeded else "POLL_NEEDS_ATTENTION"
        return self._write_flow_state(
            stage=stage,
            operation_job=job,
            operation_state="SUCCEEDED" if succeeded else "FAILED",
            operation_code=code,
            operation_finished_at=iso_now(),
        )

    def _record_restore_drill(
        self,
        *,
        status: Mapping[str, Any],
        code: str,
    ) -> dict[str, Any]:
        human_status = str(status.get("human_status") or "需处理")
        result = "OK" if human_status == "已更新" and code == "RESTORE_DRILL_OK" else (
            "IN_PROGRESS" if human_status == "处理中" else "NEEDS_ATTENTION"
        )
        atomic_json_write(
            self.config.publication_dir / "restore_drill.json",
            {
                "schema_version": "kmfa.daily_funds.restore_drill.v1",
                "observed_at": iso_now(),
                "result": result,
                "machine_code": self._flow_code(code),
                "non_production": True,
            },
        )
        self._write_flow_state(
            stage="RESTORE_DRILL" if result == "OK" else "RESTORE_DRILL_NEEDS_ATTENTION",
            status=status,
        )
        return dict(status)

    def _observer_status(
        self,
        human_status: str,
        machine_code: str,
        *,
        stage: str,
        observer_state: str,
        observer_result: str,
        effective_business_date: str | None = None,
        last_verified_at: str | None = None,
        publication_id: str | None = None,
        backup_state: str = "UNKNOWN",
    ) -> dict[str, Any]:
        status = self.status.write(
            human_status,
            machine_code,
            effective_business_date=effective_business_date,
            last_verified_at=last_verified_at,
            publication_id=publication_id,
            backup_state=backup_state,
        )
        self._write_flow_state(
            stage=stage,
            status=status,
            observer_state=observer_state,
            observer_result=observer_result,
        )
        return status

    def _observer_inputs(self, current: Mapping[str, Any], *, observed_at: datetime) -> dict[str, Any]:
        """Validate the values-free predicates needed for a shadow comparison."""

        publication = current.get("publication")
        summary = current.get("summary")
        balances = current.get("daily_balances")
        if not isinstance(publication, Mapping) or not isinstance(summary, Mapping) or not isinstance(balances, list):
            raise ValueError("current projection structure invalid")
        publication_id = self._lower_hex(publication.get("publication_id"), 64)
        if publication_id is None or publication.get("status") != "VALID":
            raise ValueError("publication invalid")
        try:
            business_date = date.fromisoformat(str(publication.get("business_date") or ""))
        except ValueError as exc:
            raise ValueError("business date invalid") from exc
        difference = publication.get("reconciliation_difference_fen")
        if isinstance(difference, bool) or not isinstance(difference, int) or difference != 0:
            raise ValueError("publication reconciliation invalid")
        source_versions = publication.get("source_versions")
        if not isinstance(source_versions, list) or len(source_versions) != 2:
            raise ValueError("source pair invalid")
        versions = {
            self._lower_hex(row.get("source_version"), 64)
            for row in source_versions if isinstance(row, Mapping)
        }
        if len(versions) != 2 or None in versions:
            raise ValueError("source pair invalid")
        threshold = publication.get("threshold_snapshot")
        fixed = threshold.get("fixed") if isinstance(threshold, Mapping) else None
        if (
            not isinstance(fixed, Mapping)
            or fixed.get("hard_fen") != HARD_THRESHOLD_FEN
            or fixed.get("soft_fen") != SOFT_THRESHOLD_FEN
            or publication.get("threshold_snapshot", {}).get("fixed_risk") not in RISK_LABELS
        ):
            raise ValueError("threshold snapshot invalid")
        total = summary.get("total_available_fen")
        if isinstance(total, bool) or not isinstance(total, int):
            raise ValueError("summary total invalid")
        current_rows = [
            row for row in balances
            if isinstance(row, Mapping) and row.get("business_date") == business_date.isoformat()
        ]
        if len(current_rows) != 1:
            raise ValueError("current balance missing")
        current_row = current_rows[0]
        ending = current_row.get("ending_available_fen")
        if (
            isinstance(ending, bool)
            or not isinstance(ending, int)
            or ending != total
            or current_row.get("direct_observation") is not True
            or current_row.get("coverage_gap") is not False
            or current_row.get("carried_forward") is not False
        ):
            raise ValueError("current balance invalid")
        history = self._history().get("days", {})
        history_row = history.get(business_date.isoformat()) if isinstance(history, Mapping) else None
        if (
            not isinstance(history_row, Mapping)
            or history_row.get("publication_id") != publication_id
            or history_row.get("ending_available_fen") != total
            or history_row.get("direct_observation") is not True
            or history_row.get("coverage_gap") is not False
            or history_row.get("carried_forward") is not False
        ):
            raise ValueError("history comparison invalid")
        created_at = self._flow_timestamp(publication.get("created_at"))
        if created_at is None:
            raise ValueError("publication timestamp invalid")
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        latency_seconds = (observed_at.astimezone(UTC) - created.astimezone(UTC)).total_seconds()
        if latency_seconds < 0:
            raise ValueError("publication timestamp invalid")
        runtime = current.get("runtime") if isinstance(current.get("runtime"), Mapping) else {}
        backup_state = self._flow_code(runtime.get("oci_backup_state") or publication.get("oci_backup_state"))
        if backup_state not in {"OK", "LAG", "PENDING", "UNKNOWN"}:
            backup_state = "UNKNOWN"
        restore_state, _ = self._restore_drill_state()
        return {
            "publication": dict(publication),
            "publication_id": publication_id,
            "business_date": business_date,
            "backup_state": backup_state,
            "restore_state": restore_state,
            "latency_minutes": int(latency_seconds // 60),
        }

    def preflight(self) -> dict[str, Any]:
        """Record configuration readiness without issuing external requests."""

        missing = self.config.missing()
        if missing:
            return self.status.write("需处理", "CONFIG_INVALID", backup_state="UNKNOWN")
        try:
            self.config.validate()
        except ConfigError:
            return self.status.write("需处理", "CONFIG_INVALID", backup_state="UNKNOWN")
        # A new cloud volume has neither a profile receipt nor a recovery
        # bundle.  Do not describe that state as "CONFIG_READY": it needs the
        # one-time protected cloud-terminal bootstrap before any scheduled
        # source work can legitimately begin.  The DWS CLI owns its profile
        # layout (v1.0.52 creates identity.json, not a public app.json).
        if not self.config.dws_auth_bundle_b64 and not (self.config.control_dir / "dws_bootstrap.json").is_file():
            return self.status.write("需处理", "DWS_BOOTSTRAP_REQUIRED", backup_state="UNKNOWN")
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

    def bootstrap_dws_auth(self) -> dict[str, Any]:
        """Create this cloud slice's DWS login once, outside all schedules.

        The device code remains solely in the protected interactive terminal
        used to execute this command.  This method records only a redacted
        receipt after DWS independently reports a refreshable login.  The
        receipt records whether DWS used its official default or an isolated
        deployment override; the subsequent exact source query remains the
        authority for access.
        """

        try:
            self.config.validate_dws_bootstrap()
        except ConfigError:
            return self.status.write("需处理", "CONFIG_INVALID")
        client = self._dws_client()
        try:
            self._lease_call(
                "dws_bootstrap_lock",
                ttl_seconds=1_800,
                code="DWS_BOOTSTRAP_LOCK_HELD",
                callback=client.bootstrap_device_auth,
            )
        except IngestionError as exc:
            if exc.code == "DWS_BOOTSTRAP_LOCK_HELD":
                return self.status.write("处理中", exc.code)
            self.state.queue_incident(exc.code)
            return self.status.write("需处理", exc.code)
        client_mode = "configured-override" if self.config.dws_client_id else "official-default"
        client_identity = self.config.dws_client_id or "dws-official-default"
        atomic_json_write(
            self.config.control_dir / "dws_bootstrap.json",
            {
                "schema_version": "kmfa.daily_funds.dws_bootstrap.v1",
                "completed_at": iso_now(),
                "configured_client_fingerprint": sha256(client_identity.encode("utf-8")).hexdigest(),
                "dws_client_mode": client_mode,
                "cloud_volume_only": True,
            },
        )
        status = self.status.write("处理中", "DWS_BOOTSTRAP_READY")
        return {"ok": True, "status": "DWS_BOOTSTRAP_READY", "human_status": status["human_status"]}

    @staticmethod
    def _mount_targets(proc_root: Path) -> set[str] | None:
        """Read only mount targets, never host sources or mount options."""

        try:
            lines = (proc_root / "self" / "mountinfo").read_text(encoding="utf-8").splitlines()
        except OSError:
            return None
        targets: set[str] = set()
        for line in lines:
            fields = line.split()
            if len(fields) >= 5:
                targets.add(fields[4].replace(r"\040", " "))
        return targets

    @staticmethod
    def _process_summary(proc_root: Path) -> dict[str, int] | None:
        """Inspect process categories without persisting argv, IDs or values."""

        try:
            entries = list(proc_root.iterdir())
        except OSError:
            return None
        scanned = daily_funds = coupled = 0
        for entry in entries:
            if not entry.name.isdigit():
                continue
            try:
                command = (entry / "cmdline").read_bytes().lower()
            except OSError:
                continue
            scanned += 1
            if b"/opt/daily-funds/" in command:
                daily_funds += 1
            if any(marker in command for marker in _COUPLED_PROCESS_MARKERS):
                coupled += 1
        return {
            "scanned_processes": scanned,
            "daily_funds_processes": daily_funds,
            "coupled_skill_processes": coupled,
        }

    def runtime_audit(
        self,
        *,
        proc_root: Path = Path("/proc"),
        mount_checker: Callable[[str], bool] = os.path.ismount,
        expected_paths: Mapping[str, Path] | None = None,
    ) -> dict[str, Any]:
        """Persist a redacted T01 isolation receipt without changing status.

        The protected publication volume receives only booleans, counts and
        operation codes.  It deliberately excludes raw command lines, host
        mount sources, identifiers, URLs, credentials and message content.
        """

        expected = dict(_CLOUD_RUNTIME_PATHS if expected_paths is None else expected_paths)
        actual = {
            "state": self.config.state_dir,
            "publication": self.config.publication_dir,
            "control": self.config.control_dir,
            "dws_config": self.config.dws_config_dir,
            "dws_keyring": self.config.dws_keyring_dir,
        }
        path_layout_exact = actual == expected
        dws_volume_shared = actual["dws_config"].parent == actual["dws_keyring"].parent
        mount_targets = self._mount_targets(proc_root)
        process_summary = self._process_summary(proc_root)
        mount_roots = {
            "state": actual["state"],
            "publication": actual["publication"],
            "control": actual["control"],
            "dws": actual["dws_config"].parent,
        }
        mount_checks = {
            name: bool(mount_checker(str(path))) and mount_targets is not None and str(path) in mount_targets
            for name, path in mount_roots.items()
        }
        forbidden_mount = bool(mount_targets is not None and any(
            target == prefix or target.startswith(prefix + "/")
            for target in mount_targets
            for prefix in _FORBIDDEN_MOUNT_PREFIXES
        ))
        try:
            # A green topology receipt is meaningful only when every runtime
            # secret/config slot (including D1/R2/OCI) has a valid shape.
            self.config.validate()
            config_state = "VALID"
            config_fingerprint = self.config.redacted_fingerprint()
        except ConfigError:
            config_state = "INVALID"
            config_fingerprint = None

        if not path_layout_exact:
            code = "RUNTIME_PATH_INVALID"
        elif not dws_volume_shared:
            code = "DWS_VOLUME_LAYOUT_INVALID"
        elif mount_targets is None or process_summary is None:
            code = "RUNTIME_AUDIT_UNAVAILABLE"
        elif forbidden_mount:
            code = "FORBIDDEN_HOST_MOUNT"
        elif not all(mount_checks.values()):
            code = "MOUNT_LAYOUT_INVALID"
        elif process_summary["coupled_skill_processes"]:
            code = "COUPLED_SKILL_PROCESS"
        elif process_summary["daily_funds_processes"] < 1:
            code = "DAILY_FUNDS_PROCESS_MISSING"
        elif config_state != "VALID":
            code = "CONFIG_INVALID"
        else:
            code = "RUNTIME_AUDIT_OK"

        audit = {
            "schema_version": "kmfa.daily_funds.runtime_audit.v1",
            "observed_at": iso_now(),
            "result": "OK" if code == "RUNTIME_AUDIT_OK" else "NEEDS_ATTENTION",
            "machine_code": code,
            "config_state": config_state,
            "redacted_config_fingerprint": config_fingerprint,
            "path_layout_exact": path_layout_exact,
            "dws_volume_shared": dws_volume_shared,
            "mounts": mount_checks,
            "forbidden_host_mount_detected": forbidden_mount,
            "processes": process_summary,
            "network_ledger": self.state.network_ledger_summary(),
        }
        atomic_json_write(self.config.publication_dir / "runtime_audit.json", audit)
        # T08: this joins the existing KMFA status center through the same
        # values-free projection volume; it does not create a parallel health
        # endpoint or claim a production source/image identity.
        self._write_flow_state(
            stage="RUNTIME_AUDITED" if code == "RUNTIME_AUDIT_OK" else "RUNTIME_NEEDS_ATTENTION",
        )
        return {"ok": code == "RUNTIME_AUDIT_OK", "code": code}

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

    @staticmethod
    def _parse_failure_code(error: ParseError) -> str:
        return str(error).split(":", 1)[0]

    def _inspect_attachment_capabilities(
        self,
        attachments: Iterable[DownloadedAttachment],
    ) -> AttachmentCapabilityInspection:
        """Open every Git-readback attachment and persist capability receipts.

        This method is deliberately not a lenient parser: callers receive all
        failures and must decide whether their contract permits a discovery
        result.  The normal live path continues to fail closed through
        :meth:`_parse`; only a historical raw-archive pass may retain a
        non-integrity failure as ``NEEDS_REVIEW``.
        """

        parsed: list[TimedFacts] = []
        failures: list[ParseError] = []
        for attachment in attachments:
            # ``attachments`` here come only from GitSparseWriter's fresh
            # sparse-clone readback.  The capability receipt covers supported
            # and unsupported real types, but a type is marked SUPPORTED only
            # after exact source SHA + MIME/magic + parser-open validation.
            family = attachment.family if attachment.family in TRANSACTION_FAMILIES | {ACCOUNT_FAMILY} else "UNCLASSIFIED"
            suffix, declared_mime, magic = attachment_capability_metadata(
                filename=attachment.filename,
                payload=attachment.payload,
                mime=attachment.mime,
            )
            try:
                if attachment.family is None or Path(attachment.filename).suffix.lower() not in ALLOWED_SUFFIXES:
                    raise ParseError("UNSUPPORTED_ATTACHMENT")
                facts = parse_attachment(
                    family=attachment.family,
                    filename=attachment.filename,
                    payload=attachment.payload,
                    source=self._source_ref(attachment),
                    mime=attachment.mime,
                )
            except ParseError as exc:
                # A failed lineage check means this was not a proven Git
                # readback object.  Do not let such bytes masquerade as real
                # capability evidence even in NEEDS_REVIEW state.
                failure_code = self._parse_failure_code(exc)
                if failure_code not in _SOURCE_INTEGRITY_PARSE_CODES:
                    self.state.record_capability_evidence(
                        attachment_sha256=attachment.sha256,
                        family=family,
                        suffix=suffix,
                        declared_mime=declared_mime,
                        magic=magic,
                        parser_version=PARSER_VERSION,
                        outcome="NEEDS_REVIEW",
                        code=failure_code,
                    )
                failures.append(exc)
                continue
            evidence = facts.parser_evidence
            self.state.record_parser_evidence(
                attachment_sha256=attachment.sha256,
                family=facts.family,
                suffix=evidence.suffix,
                declared_mime=evidence.declared_mime,
                magic=evidence.magic,
                parser_version=evidence.parser_version,
            )
            self.state.record_capability_evidence(
                attachment_sha256=attachment.sha256,
                family=facts.family,
                suffix=evidence.suffix,
                declared_mime=evidence.declared_mime,
                magic=evidence.magic,
                parser_version=evidence.parser_version,
                outcome="SUPPORTED",
                code="PARSER_OPEN_OK",
            )
            parsed.append(TimedFacts(
                facts,
                attachment.message_at,
            ))
        return AttachmentCapabilityInspection(tuple(parsed), tuple(failures))

    def _parse(self, attachments: Iterable[DownloadedAttachment]) -> list[TimedFacts]:
        """Strict live parse gate: one failed attachment rejects the batch."""

        inspection = self._inspect_attachment_capabilities(attachments)
        if inspection.failures:
            raise inspection.failures[0]
        return list(inspection.parsed)

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

    @staticmethod
    def _journal_fen(value: object, code: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ReconciliationError(code)
        return value

    @staticmethod
    def _journal_flag(value: object, code: str) -> bool:
        if not isinstance(value, bool):
            raise ReconciliationError(code)
        return value

    def _prior_balance_mapping(self, values: object) -> Mapping[str, int]:
        if not isinstance(values, Mapping):
            return {}
        result: dict[str, int] = {}
        for key, value in values.items():
            if not isinstance(key, str) or not key:
                raise ReconciliationError("PRIOR_BALANCE_KEY_INVALID")
            result[key] = self._journal_fen(value, "PRIOR_BALANCE_NOT_INTEGER_FEN")
        return result

    def _prior_account_balances(self, business_date: date | None = None) -> Mapping[str, int]:
        if business_date is not None:
            previous_day = (business_date - timedelta(days=1)).isoformat()
            record = self._history().get("days", {}).get(previous_day)
            if isinstance(record, Mapping) and isinstance(record.get("account_ending_by_hash"), Mapping):
                return self._prior_balance_mapping(record["account_ending_by_hash"])
        current = self._current()
        if not current:
            return {}
        if business_date is not None:
            try:
                current_business_date = date.fromisoformat(str(current["publication"]["business_date"]))
            except (KeyError, TypeError, ValueError) as exc:
                raise ReconciliationError("PRIOR_PUBLICATION_INVALID") from exc
            # Historical backfill must never borrow a newer (or older)
            # pointer just because it happens to have account aliases.  Only
            # the immediately preceding VALID date is a permissible fallback.
            if current_business_date != business_date - timedelta(days=1):
                return {}
        values = current.get("summary", {}).get("account_ending_by_hash")
        return self._prior_balance_mapping(values)

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
                ending = self._journal_fen(row["ending_available_fen"], "HISTORY_BALANCE_NOT_INTEGER_FEN")
                direct_observation = self._journal_flag(row.get("direct_observation"), "HISTORY_BALANCE_FLAG_INVALID")
                coverage_gap = self._journal_flag(row.get("coverage_gap", False), "HISTORY_BALANCE_FLAG_INVALID")
                carried_forward = self._journal_flag(row.get("carried_forward", False), "HISTORY_BALANCE_FLAG_INVALID")
                existing[day.isoformat()] = DailyBalance(
                    day,
                    ending,
                    direct_observation,
                    coverage_gap,
                    carried_forward,
                )
            except ReconciliationError:
                raise
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
                    if business_day > report.business_date:
                        continue
                    direct_observation = self._journal_flag(row.get("direct_observation"), "CURRENT_BALANCE_FLAG_INVALID")
                    if not direct_observation:
                        continue
                    ending = self._journal_fen(row["ending_available_fen"], "CURRENT_BALANCE_NOT_INTEGER_FEN")
                    coverage_gap = self._journal_flag(row.get("coverage_gap", False), "CURRENT_BALANCE_FLAG_INVALID")
                    carried_forward = self._journal_flag(row.get("carried_forward", False), "CURRENT_BALANCE_FLAG_INVALID")
                    existing[business_day.isoformat()] = DailyBalance(
                        business_day,
                        ending,
                        direct_observation,
                        coverage_gap,
                        carried_forward,
                    )
                except ReconciliationError:
                    raise
                except (KeyError, TypeError, ValueError):
                    continue
        report_ending = self._journal_fen(report.total_ending_fen, "REPORT_BALANCE_NOT_INTEGER_FEN")
        existing[report.business_date.isoformat()] = DailyBalance(report.business_date, report_ending, True, False)
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
        oci = self._oci_store()
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
        allow_empty_window: bool = False,
        archive_only: bool = False,
    ) -> dict[str, Any]:
        # A caller must opt into the historical mode explicitly.  It is never
        # legal for the current/live job to silently turn into a raw-only scan:
        # that would make a missing publication look like successful funding
        # processing.
        if archive_only and advance_pointer:
            status = self.status.write("需处理", "ARCHIVE_ONLY_POINTER_FORBIDDEN")
            self._write_flow_state(stage="POLL_NEEDS_ATTENTION", status=status)
            return {"ok": False, "code": "ARCHIVE_ONLY_POINTER_FORBIDDEN"}
        try:
            # Historical discovery owns no R2/D1/OCI output.  It still
            # validates the exact DWS source and private-Git writer contract,
            # then persists and freshly re-opens the raw authority before any
            # capability result is accepted.
            self.config.validate(include_storage=not archive_only)
        except ConfigError:
            return self.status.write("需处理", "CONFIG_INVALID")
        now = now or datetime.now(UTC)
        holder = str(uuid.uuid4())
        client = self._dws_client()
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
                # A historic calendar day can be a complete, valid scan with
                # no selected source document (for example a non-reporting
                # day).  That is not permission to weaken the live source
                # gate: only bounded backfill explicitly opts in and it never
                # advances the current publication pointer.
                if allow_empty_window and not advance_pointer:
                    status = self._status_from_current(fallback_code="BACKFILL_EMPTY_WINDOW")
                    if archive_only:
                        self._write_flow_state(stage="BACKFILL_EMPTY_WINDOW", status=status)
                    result = {
                        "ok": True,
                        "pages": pages,
                        "attachments": 0,
                        "empty_window": True,
                    }
                    if archive_only:
                        result["archive_only"] = True
                    return result
                raise IngestionError("SOURCE_MATCH_ZERO")
            verified_attachments = self._deduplicated_attachments(all_attachments)
            if archive_only:
                # The raw Git authority has been re-opened before this point.
                # A historical format census is allowed to retain a genuine
                # unsupported file as NEEDS_REVIEW, but a source-lineage/hash
                # failure is still fatal: no downstream receipt can upgrade
                # unverified bytes into a successful archive scan.
                inspection = self._inspect_attachment_capabilities(verified_attachments)
                integrity_failures = tuple(
                    failure
                    for failure in inspection.failures
                    if self._parse_failure_code(failure) in _SOURCE_INTEGRITY_PARSE_CODES
                )
                if integrity_failures:
                    raise integrity_failures[0]
                for attachment in verified_attachments:
                    occurrence_key = f"{attachment.message_id_hash}:{attachment.index}:{attachment.sha256}"
                    self.state.mark_inbox(occurrence_key, "ARCHIVED_CAPABILITY_RECORDED")
                needs_review = len(inspection.failures)
                code = "BACKFILL_ARCHIVED_NEEDS_REVIEW" if needs_review else "BACKFILL_ARCHIVED"
                status = self._status_from_current(fallback_code=code)
                self._write_flow_state(
                    stage="BACKFILL_ARCHIVED_NEEDS_REVIEW" if needs_review else "BACKFILL_ARCHIVED",
                    status=status,
                )
                return {
                    "ok": True,
                    "pages": pages,
                    "attachments": len(verified_attachments),
                    "archive_only": True,
                    "capability_supported": len(inspection.parsed),
                    "capability_needs_review": needs_review,
                }
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
            status = self.status.write(human_status, str(code))
            self._write_flow_state(
                stage="PARSER_NEEDS_REVIEW" if isinstance(exc, ParseError) else "POLL_NEEDS_ATTENTION",
                status=status,
            )
            return {"ok": False, "code": str(code)}

    def auth_probe(self) -> dict[str, Any]:
        try:
            self.config.validate(include_storage=False)
        except ConfigError:
            return self.status.write("需处理", "CONFIG_INVALID")
        client = self._dws_client()
        now = datetime.now(UTC)
        try:
            self._lease_call(
                "auth_probe_lock",
                ttl_seconds=55,
                code="AUTH_PROBE_LOCK_HELD",
                callback=lambda: client.search(now - timedelta(minutes=1), now, None),
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
        empty_days: list[str] = []
        needs_review_days: list[str] = []
        needs_review_attachments = 0
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
                allow_empty_window=True,
                archive_only=True,
            )
            if not result.get("ok"):
                return {"ok": False, "completed_days": completed, "code": result.get("code", "BACKFILL_FAILED")}
            completed.append(next_day.isoformat())
            if result.get("empty_window"):
                empty_days.append(next_day.isoformat())
            needs_review = result.get("capability_needs_review", 0)
            if isinstance(needs_review, bool) or not isinstance(needs_review, int) or needs_review < 0:
                return {"ok": False, "completed_days": completed, "code": "BACKFILL_CAPABILITY_RESULT_INVALID"}
            if needs_review:
                needs_review_days.append(next_day.isoformat())
                needs_review_attachments += needs_review
            next_day += timedelta(days=1)
            self.state.put("backfill_next_business_date", next_day.isoformat())
        base_code = "BACKFILL_COMPLETE" if next_day >= local_today else "BACKFILLING"
        outcome_code = f"{base_code}_NEEDS_REVIEW" if needs_review_attachments else base_code
        status = self._status_from_current(fallback_code=outcome_code)
        self._write_flow_state(
            stage="BACKFILL_COMPLETE_NEEDS_REVIEW" if next_day >= local_today and needs_review_attachments else (
                "BACKFILLING_NEEDS_REVIEW" if needs_review_attachments else base_code
            ),
            status=status,
        )
        return {
            "ok": True,
            "completed_days": completed,
            "empty_days": empty_days,
            "needs_review_days": needs_review_days,
            "needs_review_attachments": needs_review_attachments,
            "next_business_date": next_day.isoformat(),
            "complete": next_day >= local_today,
            "code": outcome_code,
            "status": status["human_status"],
        }

    def keepalive(self) -> dict[str, Any]:
        try:
            self.config.validate(include_storage=False)
        except ConfigError:
            return self.status.write("需处理", "CONFIG_INVALID")
        client = self._dws_client()
        try:
            self._lease_call(
                "keepalive_lock",
                ttl_seconds=55,
                code="KEEPALIVE_LOCK_HELD",
                callback=client.ensure_authenticated,
            )
        except IngestionError as exc:
            if exc.code == "KEEPALIVE_LOCK_HELD":
                return self.status.write("处理中", exc.code)
            self.state.queue_incident(exc.code)
            return self.status.write("需处理", exc.code)
        return self._status_from_current(fallback_code="KEEPALIVE_OK")

    def observer(self, *, now: datetime | None = None) -> dict[str, Any]:
        """Record one autonomous, deployment-bound shadow comparison.

        Progress is counted only for a *new source-validated business date*
        after the current container deployment's verified baseline.  Cron runs,
        retries and historic backfill can therefore never manufacture the
        required five post-deploy business days.
        """

        observed_at = now or datetime.now(UTC)
        if observed_at.tzinfo is None:
            return self._observer_status(
                "需处理", "PUBLICATION_INVALID",
                stage="OBSERVER_NEEDS_ATTENTION",
                observer_state="NEEDS_ATTENTION",
                observer_result="OBSERVATION_CLOCK_INVALID",
            )
        observed_at = observed_at.astimezone(UTC)
        observed_at_text = observed_at.isoformat(timespec="seconds").replace("+00:00", "Z")
        try:
            self.config.validate()
        except ConfigError:
            return self._observer_status(
                "需处理", "CONFIG_INVALID",
                stage="OBSERVER_NEEDS_ATTENTION",
                observer_state="NEEDS_ATTENTION",
                observer_result="CONFIG_INVALID",
            )
        deployment_marker = self._deployment_marker()
        if deployment_marker is None:
            return self._observer_status(
                "需处理", "DEPLOYMENT_MARKER_UNAVAILABLE",
                stage="OBSERVER_NEEDS_ATTENTION",
                observer_state="NEEDS_ATTENTION",
                observer_result="DEPLOYMENT_MARKER_UNAVAILABLE",
            )

        def observe_under_lock() -> dict[str, Any]:
            def verify_d1_and_pointer() -> dict[str, Any]:
                # Load the pointer only after taking the same publication lock
                # used by publish/restore.  Otherwise a new pointer could land
                # between a local read and the D1 oracle and be miscounted as
                # a verified observation for the wrong day.
                current = self._current()
                if current is None:
                    raise PublicationError("SOURCE_MISSING")
                try:
                    inputs = self._observer_inputs(current, observed_at=observed_at)
                except (TypeError, ValueError) as exc:
                    raise PublicationError("PUBLICATION_INVALID") from exc
                publication_id = str(inputs["publication_id"])
                row = D1Projection(self.config).oracle(publication_id)
                payload_json = row.get("payload_json") if isinstance(row, Mapping) else None
                if not isinstance(payload_json, str):
                    raise PublicationError("D1_ORACLE_PUBLICATION_INVALID")
                try:
                    stored_publication = json.loads(payload_json)
                except json.JSONDecodeError as exc:
                    raise PublicationError("D1_ORACLE_PUBLICATION_INVALID") from exc
                if (
                    not isinstance(stored_publication, Mapping)
                    or dict(stored_publication) != inputs["publication"]
                    or json.dumps(stored_publication, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" != payload_json
                ):
                    raise PublicationError("D1_ORACLE_PUBLICATION_INVALID")
                return inputs

            try:
                inputs = self._lease_call(
                    "publisher_lock",
                    ttl_seconds=13 * 60,
                    code="PUBLISHER_LOCK_HELD",
                    callback=verify_d1_and_pointer,
                )
            except IngestionError as exc:
                if exc.code == "PUBLISHER_LOCK_HELD":
                    return self._observer_status(
                        "处理中", "POLLING",
                        stage="OBSERVER_WAITING_FOR_PUBLICATION_LOCK",
                        observer_state="WAITING_FOR_LOCK",
                        observer_result="PUBLISHER_LOCK_HELD",
                    )
                return self._observer_status(
                    "需处理", "D1_FAILED",
                    stage="OBSERVER_NEEDS_ATTENTION",
                    observer_state="NEEDS_ATTENTION",
                    observer_result="D1_ORACLE_FAILED",
                )
            except PublicationError as exc:
                if exc.code == "SOURCE_MISSING":
                    return self._observer_status(
                        "需处理", "SOURCE_MISSING",
                        stage="WAITING_FOR_VALID_PUBLICATION",
                        observer_state="WAITING_FOR_VALID_PUBLICATION",
                        observer_result="SOURCE_MISSING",
                    )
                if exc.code == "PUBLICATION_INVALID":
                    return self._observer_status(
                        "需处理", "PUBLICATION_INVALID",
                        stage="OBSERVER_NEEDS_ATTENTION",
                        observer_state="NEEDS_ATTENTION",
                        observer_result="POINTER_OR_HISTORY_INVALID",
                    )
                return self._observer_status(
                    "需处理", "D1_FAILED",
                    stage="OBSERVER_NEEDS_ATTENTION",
                    observer_state="NEEDS_ATTENTION",
                    observer_result="D1_ORACLE_FAILED",
                )

            business_date = inputs["business_date"]
            assert isinstance(business_date, date)
            publication_id = str(inputs["publication_id"])
            backup_state = str(inputs["backup_state"])
            # Do not label a lagging pointer as a fresh daily comparison.  Its
            # date stays visible in the existing status center for follow-up.
            if (observed_at.date() - business_date).days > 1:
                return self._observer_status(
                    "需处理", "STALE",
                    stage="OBSERVER_NEEDS_ATTENTION",
                    observer_state="NEEDS_ATTENTION",
                    observer_result="STALE",
                    effective_business_date=business_date.isoformat(),
                    last_verified_at=observed_at_text,
                    publication_id=publication_id,
                    backup_state=backup_state,
                )

            window = self.state.observer_window()
            if window is None or window["deployment_marker"] != deployment_marker:
                self.state.begin_observer_window(
                    deployment_marker=deployment_marker,
                    baseline_business_date=business_date.isoformat(),
                    started_at=observed_at_text,
                )
                return self._observer_status(
                    "已更新", "VALID_PUBLISHED",
                    stage="OBSERVER_BASELINE_CAPTURED",
                    observer_state="BASELINE_CAPTURED",
                    observer_result="D1_AND_POINTER_VERIFIED",
                    effective_business_date=business_date.isoformat(),
                    last_verified_at=observed_at_text,
                    publication_id=publication_id,
                    backup_state=backup_state,
                )

            baseline = date.fromisoformat(window["baseline_business_date"])
            if business_date < baseline:
                return self._observer_status(
                    "需处理", "STALE",
                    stage="OBSERVER_NEEDS_ATTENTION",
                    observer_state="NEEDS_ATTENTION",
                    observer_result="POINTER_BEFORE_DEPLOYMENT_BASELINE",
                    effective_business_date=business_date.isoformat(),
                    last_verified_at=observed_at_text,
                    publication_id=publication_id,
                    backup_state=backup_state,
                )
            if business_date == baseline:
                return self._observer_status(
                    "已更新", "VALID_PUBLISHED",
                    stage="OBSERVER_WAITING_FOR_NEXT_BUSINESS_DATE",
                    observer_state="WAITING_FOR_NEXT_BUSINESS_DATE",
                    observer_result="D1_AND_POINTER_VERIFIED",
                    effective_business_date=business_date.isoformat(),
                    last_verified_at=observed_at_text,
                    publication_id=publication_id,
                    backup_state=backup_state,
                )

            self.state.record_observer_day(
                business_date=business_date.isoformat(),
                publication_id=publication_id,
                comparison_state="D1_AND_POINTER_VERIFIED",
                coverage_state="DIRECT_OBSERVATION",
                amount_state="ZERO_FEN",
                threshold_state="VALID",
                retrieval_state="COMPLETE_PAIR",
                duplicate_state="SOURCE_VERSION_UNIQUE",
                backup_state=backup_state,
                restore_state=str(inputs["restore_state"]),
                latency_minutes=int(inputs["latency_minutes"]),
                observed_at=observed_at_text,
            )
            completed = len(self.state.observer_days(limit=_POST_DEPLOY_OBSERVER_REQUIRED_BUSINESS_DAYS))
            observer_state = "COMPLETE" if completed >= _POST_DEPLOY_OBSERVER_REQUIRED_BUSINESS_DAYS else "OBSERVING"
            return self._observer_status(
                "已更新", "VALID_PUBLISHED",
                stage="POST_DEPLOY_OBSERVATION_COMPLETE" if observer_state == "COMPLETE" else "POST_DEPLOY_OBSERVING",
                observer_state=observer_state,
                observer_result="D1_AND_POINTER_VERIFIED",
                effective_business_date=business_date.isoformat(),
                last_verified_at=observed_at_text,
                publication_id=publication_id,
                backup_state=backup_state,
            )

        try:
            return self._lease_call(
                "observer_lock",
                ttl_seconds=13 * 60,
                code="OBSERVER_LOCK_HELD",
                callback=observe_under_lock,
            )
        except IngestionError as exc:
            if exc.code == "OBSERVER_LOCK_HELD":
                return self._observer_status(
                    "处理中", "POLLING",
                    stage="OBSERVER_WAITING_FOR_LOCK",
                    observer_state="WAITING_FOR_LOCK",
                    observer_result="OBSERVER_LOCK_HELD",
                )
            return self._observer_status(
                "需处理", "D1_FAILED",
                stage="OBSERVER_NEEDS_ATTENTION",
                observer_state="NEEDS_ATTENTION",
                observer_result="OBSERVER_FAILED",
            )

    def cold_backup(self) -> dict[str, Any]:
        """Retry OCI recovery artifacts without moving the publication pointer."""

        try:
            self.config.validate()
        except ConfigError:
            return self.status.write("需处理", "CONFIG_INVALID")

        def backup_under_publisher_lock() -> dict[str, Any]:
            # Reload after acquiring the same lease used by publish/restore so
            # a retry can neither back up a stale pointer nor race a new one.
            current = self._current()
            if current is None:
                raise PublicationError("SOURCE_MISSING")
            publication = current.get("publication", {})
            publication_id = str(publication.get("publication_id") or "")
            r2_sha = str(publication.get("r2_manifest_sha256") or "")
            if (
                len(publication_id) != 64
                or len(r2_sha) != 64
                or any(char not in "0123456789abcdef" for char in publication_id)
                or any(char not in "0123456789abcdef" for char in r2_sha)
            ):
                raise PublicationError("PUBLICATION_INVALID")
            r2_store = S3CompatibleStore(
                endpoint_url=self.config.r2_endpoint_url,
                bucket=self.config.r2_bucket,
                access_key_id=self.config.r2_access_key_id,
                secret_access_key=self.config.r2_secret_access_key,
                region="auto",
            )
            d1 = D1Projection(self.config)
            oci_store = self._oci_store()
            r2_inventory = R2Mirror(r2_store).verify_manifest(
                r2_sha,
                expected_git_commit_sha=str(publication.get("git_commit_sha") or ""),
            )
            restore_manifest_sha = OciColdBackup(oci_store).backup(
                publication_id=publication_id,
                publication_sha256=sha256(json.dumps(publication, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n").hexdigest(),
                publication_created_at=str(publication.get("created_at") or ""),
                git_bundle=self._lease_call(
                    "git_writer_lock",
                    ttl_seconds=13 * 60,
                    code="GIT_WRITER_LOCK_HELD",
                    callback=GitSparseWriter(self.config).bundle_head,
                ),
                d1_export=d1.export(publication_id),
                r2_inventory=r2_inventory,
            )
            # Keep the canonical publication byte-identical to its D1/Git
            # form; only the operational hand-off changes after a retry.
            runtime = current.get("runtime") if isinstance(current.get("runtime"), Mapping) else {}
            current["runtime"] = {
                **dict(runtime),
                "oci_backup_state": "OK",
                "oci_restore_manifest_sha": restore_manifest_sha,
            }
            atomic_json_write(self.config.publication_dir / "current.json", current)
            return self.status.write(
                "已更新",
                "OCI_BACKUP_OK",
                effective_business_date=publication.get("business_date"),
                last_verified_at=publication.get("created_at"),
                publication_id=publication_id,
                backup_state="OK",
            )

        try:
            return self._lease_call(
                "publisher_lock",
                ttl_seconds=13 * 60,
                code="PUBLISHER_LOCK_HELD",
                callback=backup_under_publisher_lock,
            )
        except IngestionError as exc:
            if getattr(exc, "code", str(exc)) == "PUBLISHER_LOCK_HELD":
                return self.status.write("处理中", "PUBLISHER_LOCK_HELD", backup_state="LAG")
            return self._status_from_current(fallback_code="OCI_BACKUP_LAG", backup_state="LAG")
        except PublicationError as exc:
            if exc.code in {"SOURCE_MISSING", "PUBLICATION_INVALID"}:
                return self.status.write("需处理", exc.code, backup_state="LAG")
            return self._status_from_current(fallback_code="OCI_BACKUP_LAG", backup_state="LAG")

    def restore_drill(self) -> dict[str, Any]:
        """Monthly non-production D1 rebuild; it never moves the live pointer."""

        try:
            self.config.validate()
        except ConfigError as exc:
            # Preserve the drill-specific, operator-actionable status while
            # enforcing the same full runtime config contract as every other
            # command.  Other missing storage/source values remain generic
            # CONFIG_INVALID rather than falsely implying a restore attempt.
            if str(exc) in {
                "CONFIG_INVALID:DAILY_FUNDS_RESTORE_DRILL_D1_DATABASE_ID",
                "RESTORE_DRILL_D1_MUST_DIFFER",
            }:
                return self._record_restore_drill(
                    status=self.status.write("需处理", "RESTORE_DRILL_CONFIG_INVALID"),
                    code="RESTORE_DRILL_CONFIG_INVALID",
                )
            return self._record_restore_drill(
                status=self.status.write("需处理", "CONFIG_INVALID"),
                code="CONFIG_INVALID",
            )
        drill_database_id = self.config.restore_drill_d1_database_id
        if not drill_database_id or drill_database_id == self.config.d1_database_id:
            return self._record_restore_drill(
                status=self.status.write("需处理", "RESTORE_DRILL_CONFIG_INVALID"),
                code="RESTORE_DRILL_CONFIG_INVALID",
            )
        current = self._current()
        if current is None:
            return self._record_restore_drill(
                status=self.status.write("需处理", "SOURCE_MISSING"),
                code="SOURCE_MISSING",
            )
        publication_id = str(current.get("publication", {}).get("publication_id") or "")
        if len(publication_id) != 64:
            return self._record_restore_drill(
                status=self.status.write("需处理", "PUBLICATION_INVALID"),
                code="PUBLICATION_INVALID",
            )
        try:
            oci_store = self._oci_store()
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
            return self._record_restore_drill(
                status=self.status.write(status, code),
                code=str(code),
            )
        status = self._status_from_current(fallback_code="RESTORE_DRILL_OK")
        return self._record_restore_drill(status=status, code="RESTORE_DRILL_OK")

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
            oci_store = self._oci_store()
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
