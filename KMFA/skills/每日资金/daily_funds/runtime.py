"""Executable jobs for the cloud-only daily-funds worker."""

from __future__ import annotations

import fcntl
import json
import os
import uuid
from contextlib import contextmanager
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
    PersistedRawAttachment,
    _family,
)
from .models import CashflowObservation, PaymentRequestObservation, ParsedFacts, SourceRef, Transaction
from .parsing import (
    ACCOUNT_FAMILY,
    CASHFLOW_OBSERVATION_PARSER_VERSION,
    PAYMENT_REQUEST_OBSERVATION_PARSER_VERSION,
    PARSER_VERSION,
    ParseError,
    TRANSACTION_FAMILIES,
    attachment_capability_metadata,
    deterministic_ocr_runtime_ready,
    is_ocr_attachment,
    parse_attachment,
    parse_cashflow_observation,
    parse_generic_structured_attachment,
    parse_ocr_attachment,
    parse_payment_request_observation,
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
from .r2_guard import R2FreeTierGuard, R2GuardError
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
_BACKFILL_WINDOW_DAYS = 360
# The sealed daily-funds contract permits at most seven historical calendar
# days per staggered batch.  Keep the runtime cap independent of the CLI so a
# direct caller cannot silently schedule a longer run than the cloud contract.
_BACKFILL_BATCH_MAX_DAYS = 7
# The private raw-audit reader has the same ceiling.  Keep the source-side
# repair census bounded before it can download an unbounded provider reply.
_RAW_COVERAGE_MAX_OCCURRENCES = 1024
_RAW_COVERAGE_RECEIPT_KEY = "raw_coverage_360d_receipt"
_RAW_COVERAGE_RECEIPT_SCHEMA = "kmfa.daily_funds.raw_coverage_receipt.v1"
_FLOW_STATE_SCHEMA = "kmfa.daily_funds.flow_state.v1"
_CASHFLOW_OBSERVATION_SCHEMA = "kmfa.daily_funds.cashflow_observation.v2"
_CASHFLOW_OBSERVATION_MIN_DAYS = 2
_PAYMENT_REQUEST_OBSERVATION_SCHEMA = "kmfa.daily_funds.payment_request_observation.v1"
_BUILD_SOURCE_COMMIT_FILE = Path(__file__).with_name(".kmfa-source-commit")
_OPERATION_RECEIPT_JOBS = frozenset({
    "preflight",
    "bootstrap-dws-auth",
    "runtime-audit",
    "r2-guard",
    "raw-archive-audit",
    "raw-coverage-repair",
    "raw-fact-replay",
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
_OPERATION_RECEIPT_STATES = frozenset({"RUNNING", "SUCCEEDED", "FAILED"})
_SOURCE_INTEGRITY_PARSE_CODES = frozenset({
    "SOURCE_LINEAGE_INVALID",
    "SOURCE_VERSION_MISMATCH",
    "SOURCE_PAYLOAD_HASH_MISMATCH",
})
# Historical discovery cannot manufacture an attachment that a source message
# did not contain.  It must retain that gap as an incident, but one malformed
# old source message must not strand the durable 360-day planner before it can
# inspect later dates.  Integrity, transport and parser failures are *not* in
# this set and continue to stop the planner fail-closed.
_BACKFILL_CONTINUABLE_SOURCE_CODES = frozenset({"SOURCE_ATTACHMENT_MISSING"})
# This is intentionally an ordinal, values-free diagnostic.  It lets the
# protected status surface distinguish an empty group-history window from a
# selector, attachment, or account/transaction-pair gate without retaining a
# group ID, sender ID, filename, message text, attachment hash, or count.
_SOURCE_DISCOVERY_STATES = frozenset({
    "UNKNOWN",
    "HISTORY_EMPTY",
    "TARGET_DOCUMENT_NOT_FOUND",
    "TARGET_ATTACHMENT_MISSING",
    "ATTACHMENT_ACQUIRED",
    "DOCUMENT_PAIR_MISSING",
    "ACCOUNT_SNAPSHOT_MISSING",
    "TRANSACTION_FACT_MISSING",
    "SOURCE_FACT_DATE_MISMATCH",
    "COMPLETE_PAIR_READY",
    "GENERIC_DOCUMENT_UNRESOLVED",
})
_EXPLICIT_FACT_FAMILIES = frozenset({ACCOUNT_FAMILY, "资金流水明细"})
_GENERIC_DOCUMENT_FAMILY = "资金明细"
# A raw-archive failure reaches the recovery broker through a fixed session
# schema.  Preserve the privacy boundary by projecting only decision-relevant
# operational classes.  The projection contains no provider response, source
# identity, filename, byte count, hash, amount, or exception text.
_RAW_ARCHIVE_AUDIT_FAILURE_PROJECTIONS = {
    "GIT_AUDIT_TRANSPORT_RETRYABLE": "RAW_ARCHIVE_AUDIT_TRANSPORT_UNAVAILABLE",
    "SOURCE_MISSING": "RAW_ARCHIVE_AUDIT_SOURCE_MISSING",
    "RAW_ARCHIVE_CENSUS_LIMIT_EXCEEDED": "RAW_ARCHIVE_AUDIT_CENSUS_LIMIT",
    "GIT_READBACK_FAILED": "RAW_ARCHIVE_AUDIT_INTEGRITY_NEEDS_REVIEW",
    "GIT_SPARSE_SCOPE_VIOLATION": "RAW_ARCHIVE_AUDIT_INTEGRITY_NEEDS_REVIEW",
}


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


@dataclass(frozen=True)
class _RawFactReplayCandidate:
    """One parser-open fact plus the identity required for a fresh reopen."""

    timed_facts: TimedFacts
    persisted: PersistedRawAttachment


@dataclass(frozen=True)
class _RawFactReplayPair:
    """The sole account/transaction pair eligible for one business day."""

    business_day: date
    accounts: _RawFactReplayCandidate
    transactions: _RawFactReplayCandidate


class _RawFactReplayAccumulator:
    """Select declared source facts, then index only their fresh byte readback.

    The raw coverage receipt is a complete source-envelope/occurrence/batch
    census.  A formal replay has a narrower job: it must open every explicit
    account or flow candidate from that pinned authority, while title-less raw
    evidence stays quarantined.  Hydrating unrelated screenshots first is not
    a stronger source proof and can turn a bounded recovery into an
    hours-long OCR sweep.
    """

    def __init__(self, runtime: "DailyFundsRuntime"):
        self.runtime = runtime
        self.occurrence_count = 0
        self.parsed_occurrences = 0
        self.needs_review_occurrences = 0
        self._by_day: dict[date, dict[str, list[_RawFactReplayCandidate]]] = {}

        self._declared_candidates: list[PersistedRawAttachment] = []

    def index_persisted(self, attachment: PersistedRawAttachment) -> None:
        """Keep only source-gated formal candidates from a metadata census."""

        self.occurrence_count += 1
        if _family(attachment.message) not in _EXPLICIT_FACT_FAMILIES | {_GENERIC_DOCUMENT_FAMILY}:
            return
        self._declared_candidates.append(attachment)

    @property
    def declared_candidates(self) -> tuple[PersistedRawAttachment, ...]:
        return tuple(self._declared_candidates)

    def consume(self, attachment: DownloadedAttachment) -> None:
        # The raw authority deliberately retains every exact-source attachment,
        # including the quarantined title-less material.  DF-004 does not let
        # that retention become a financial-source admission: only the three
        # explicitly declared document families may enter a formal
        # account/transaction replay.  Generic or missing-title raw evidence
        # remains available to the separate capability audit, but it cannot
        # manufacture a pair simply because its bytes happen to resemble a
        # supported spreadsheet.
        if attachment.family not in _EXPLICIT_FACT_FAMILIES | {_GENERIC_DOCUMENT_FAMILY}:
            raise IngestionError("GIT_READBACK_FAILED")
        inspection = self.runtime._inspect_attachment_capabilities((attachment,))
        integrity_failures = tuple(
            failure
            for failure in inspection.failures
            if self.runtime._parse_failure_code(failure) in _SOURCE_INTEGRITY_PARSE_CODES
        )
        if integrity_failures:
            raise IngestionError("GIT_READBACK_FAILED")
        self.needs_review_occurrences += len(inspection.failures)
        for timed in inspection.parsed:
            family = timed.facts.family
            if family == ACCOUNT_FAMILY:
                category = "accounts"
            elif family in TRANSACTION_FAMILIES:
                category = "transactions"
            else:
                raise IngestionError("GIT_READBACK_FAILED")
            if timed.facts.source_version != attachment.sha256:
                raise IngestionError("GIT_READBACK_FAILED")
            candidate = _RawFactReplayCandidate(
                timed_facts=timed,
                persisted=PersistedRawAttachment(
                    message=attachment.message,
                    message_id=attachment.message_id,
                    message_id_hash=attachment.message_id_hash,
                    message_at=attachment.message_at,
                    index=attachment.index,
                    sha256=attachment.sha256,
                ),
            )
            self._by_day.setdefault(timed.facts.business_date, {}).setdefault(category, []).append(candidate)
            self.parsed_occurrences += 1

    def pairs(self) -> tuple[tuple[_RawFactReplayPair, ...], int, int]:
        """Return exact one-to-one pairs plus incomplete/ambiguous day counts."""

        eligible: list[_RawFactReplayPair] = []
        incomplete_days = 0
        ambiguous_days = 0
        for business_day, groups in sorted(self._by_day.items()):
            accounts = tuple(groups.get("accounts", ()))
            transactions = tuple(groups.get("transactions", ()))
            if not accounts or not transactions:
                incomplete_days += 1
                continue
            if len(accounts) != 1 or len(transactions) != 1:
                ambiguous_days += 1
                continue
            eligible.append(_RawFactReplayPair(business_day, accounts[0], transactions[0]))
        return tuple(eligible), incomplete_days, ambiguous_days


class _CashflowObservationAccumulator:
    """Build one chart-only result without retaining raw screenshot bytes."""

    def __init__(self, runtime: "DailyFundsRuntime"):
        self.runtime = runtime
        self.eligible_shas: set[str] = set()
        self.observations: list[CashflowObservation] = []
        self.rejection_categories: dict[str, int] = {}
        self.ocr_ready: bool | None = None

    def add(self, attachment: DownloadedAttachment) -> None:
        if (
            attachment.family not in TRANSACTION_FAMILIES
            or not is_ocr_attachment(attachment.filename, payload=attachment.payload)
            or attachment.sha256 in self.eligible_shas
        ):
            return
        self.eligible_shas.add(attachment.sha256)
        if not self.runtime.config.ocr_enabled:
            return
        if self.ocr_ready is None:
            self.ocr_ready = deterministic_ocr_runtime_ready()
        if not self.ocr_ready:
            return
        try:
            self.observations.append(parse_cashflow_observation(
                family=attachment.family or "",
                filename=attachment.filename,
                payload=attachment.payload,
                source=self.runtime._source_ref(attachment),
                received_at=attachment.message_at,
                mime=attachment.mime,
                min_confidence_bps=self.runtime.config.ocr_min_confidence_bps,
            ))
        except ParseError as exc:
            category = self.runtime._cashflow_observation_rejection_category(exc)
            self.rejection_categories[category] = self.rejection_categories.get(category, 0) + 1

    def write(self) -> dict[str, Any]:
        source_fingerprint = (
            sha256("\n".join(sorted(self.eligible_shas)).encode("ascii")).hexdigest()
            if self.eligible_shas else None
        )
        coverage: dict[str, int] = {
            "eligible_documents": len(self.eligible_shas),
            "parsed_documents": len(self.observations),
            "rejected_documents": sum(self.rejection_categories.values()),
            "distinct_business_days": 0,
        }
        base: dict[str, Any] = {
            "schema_version": _CASHFLOW_OBSERVATION_SCHEMA,
            "generated_at": iso_now(),
            "parser_version": CASHFLOW_OBSERVATION_PARSER_VERSION,
            "source_coverage": coverage,
            "rejection_categories": self.rejection_categories,
            "evidence_version": source_fingerprint[-12:] if source_fingerprint is not None else None,
            "points": [],
        }
        if not self.eligible_shas:
            payload = {**base, "status": "NOT_AVAILABLE", "machine_code": "CASHFLOW_OBSERVATION_SOURCE_EMPTY"}
            atomic_json_write(self.runtime.config.publication_dir / "cashflow_observation.json", payload)
            return payload
        if not self.runtime.config.ocr_enabled:
            coverage["rejected_documents"] = len(self.eligible_shas)
            payload = {**base, "status": "NEEDS_REVIEW", "machine_code": "CASHFLOW_OBSERVATION_OCR_DISABLED"}
            atomic_json_write(self.runtime.config.publication_dir / "cashflow_observation.json", payload)
            return payload
        if self.ocr_ready is False:
            coverage["rejected_documents"] = len(self.eligible_shas)
            payload = {**base, "status": "NEEDS_REVIEW", "machine_code": "CASHFLOW_OBSERVATION_OCR_UNAVAILABLE"}
            atomic_json_write(self.runtime.config.publication_dir / "cashflow_observation.json", payload)
            return payload

        by_day: dict[date, CashflowObservation] = {}
        duplicate_day = False
        for observation in self.observations:
            if observation.business_date in by_day:
                duplicate_day = True
                continue
            by_day[observation.business_date] = observation
        coverage["distinct_business_days"] = len(by_day)
        if coverage["rejected_documents"]:
            code = "CASHFLOW_OBSERVATION_PARSE_NEEDS_REVIEW"
        elif duplicate_day:
            code = "CASHFLOW_OBSERVATION_DUPLICATE_DAY"
        elif len(by_day) < _CASHFLOW_OBSERVATION_MIN_DAYS:
            code = "CASHFLOW_OBSERVATION_COVERAGE_INSUFFICIENT"
        else:
            code = "CASHFLOW_OBSERVATION_VERIFIED"
        if code != "CASHFLOW_OBSERVATION_VERIFIED":
            payload = {**base, "status": "NEEDS_REVIEW", "machine_code": code}
            atomic_json_write(self.runtime.config.publication_dir / "cashflow_observation.json", payload)
            return payload
        points = [
            {
                "business_date": business_day.isoformat(),
                "inflow_fen": observation.inflow_fen,
                "outflow_fen": observation.outflow_fen,
                "net_change_fen": observation.inflow_fen - observation.outflow_fen,
            }
            for business_day, observation in sorted(by_day.items())
        ]
        payload = {**base, "status": "VERIFIED", "machine_code": code, "points": points}
        atomic_json_write(self.runtime.config.publication_dir / "cashflow_observation.json", payload)
        return payload


class _PaymentRequestObservationAccumulator:
    """Build the separate payment-request trend from exact-group screenshots.

    A payment request is a pending operational outflow, not a bank balance and
    not a completed cash movement.  The accumulator therefore owns its own
    JSON projection and never feeds the formal reconciliation or the existing
    receipt/payment cashflow view.
    """

    def __init__(self, runtime: "DailyFundsRuntime"):
        self.runtime = runtime
        self.eligible_shas: set[str] = set()
        self.observations: list[tuple[datetime, PaymentRequestObservation]] = []
        self.rejection_categories: dict[str, int] = {}
        self.ocr_ready: bool | None = None

    def add(self, attachment: DownloadedAttachment) -> None:
        if (
            not is_ocr_attachment(attachment.filename, payload=attachment.payload)
            or attachment.sha256 in self.eligible_shas
        ):
            return
        if not self.runtime.config.ocr_enabled:
            return
        if self.ocr_ready is None:
            self.ocr_ready = deterministic_ocr_runtime_ready()
        if not self.ocr_ready:
            return
        try:
            observation = parse_payment_request_observation(
                filename=attachment.filename,
                payload=attachment.payload,
                source=self.runtime._source_ref(attachment),
                received_at=attachment.message_at,
                mime=attachment.mime,
            )
        except ParseError as exc:
            # ``None`` below is the only non-candidate outcome.  Once a
            # fixed title cell has identified a payment request, every error
            # remains visible as a values-free rejection rather than silently
            # allowing an older amount to masquerade as today\'s report.
            code = self.runtime._parse_failure_code(exc)
            if code.startswith("PAYMENT_REQUEST_"):
                self.eligible_shas.add(attachment.sha256)
                category = self.runtime._payment_request_rejection_category(exc)
                self.rejection_categories[category] = self.rejection_categories.get(category, 0) + 1
            return
        if observation is None:
            return
        self.eligible_shas.add(attachment.sha256)
        self.observations.append((attachment.message_at, observation))

    def write(self) -> dict[str, Any]:
        source_fingerprint = (
            sha256("\n".join(sorted(self.eligible_shas)).encode("ascii")).hexdigest()
            if self.eligible_shas else None
        )
        coverage: dict[str, int] = {
            "eligible_documents": len(self.eligible_shas),
            "parsed_documents": len(self.observations),
            "rejected_documents": sum(self.rejection_categories.values()),
            "distinct_business_days": 0,
            "superseded_reports": 0,
        }
        base: dict[str, Any] = {
            "schema_version": _PAYMENT_REQUEST_OBSERVATION_SCHEMA,
            "generated_at": iso_now(),
            "parser_version": PAYMENT_REQUEST_OBSERVATION_PARSER_VERSION,
            "source_coverage": coverage,
            "rejection_categories": self.rejection_categories,
            "evidence_version": source_fingerprint[-12:] if source_fingerprint is not None else None,
            "points": [],
        }
        if not self.eligible_shas:
            payload = {**base, "status": "NOT_AVAILABLE", "machine_code": "PAYMENT_REQUEST_OBSERVATION_SOURCE_EMPTY"}
            atomic_json_write(self.runtime.config.publication_dir / "payment_request_observation.json", payload)
            return payload
        if self.ocr_ready is False:
            coverage["rejected_documents"] = len(self.eligible_shas)
            payload = {**base, "status": "NEEDS_REVIEW", "machine_code": "PAYMENT_REQUEST_OBSERVATION_OCR_UNAVAILABLE"}
            atomic_json_write(self.runtime.config.publication_dir / "payment_request_observation.json", payload)
            return payload
        if coverage["rejected_documents"]:
            payload = {**base, "status": "NEEDS_REVIEW", "machine_code": "PAYMENT_REQUEST_OBSERVATION_PARSE_NEEDS_REVIEW"}
            atomic_json_write(self.runtime.config.publication_dir / "payment_request_observation.json", payload)
            return payload

        latest_by_day: dict[date, tuple[datetime, PaymentRequestObservation]] = {}
        for received_at, observation in self.observations:
            prior = latest_by_day.get(observation.business_date)
            if prior is not None:
                if received_at <= prior[0]:
                    payload = {**base, "status": "NEEDS_REVIEW", "machine_code": "PAYMENT_REQUEST_OBSERVATION_DUPLICATE_AMBIGUOUS"}
                    atomic_json_write(self.runtime.config.publication_dir / "payment_request_observation.json", payload)
                    return payload
                coverage["superseded_reports"] += 1
            latest_by_day[observation.business_date] = (received_at, observation)
        coverage["distinct_business_days"] = len(latest_by_day)
        if not latest_by_day:
            payload = {**base, "status": "NEEDS_REVIEW", "machine_code": "PAYMENT_REQUEST_OBSERVATION_PARSE_NEEDS_REVIEW"}
            atomic_json_write(self.runtime.config.publication_dir / "payment_request_observation.json", payload)
            return payload
        points = [
            {
                "business_date": business_day.isoformat(),
                "request_total_fen": observation.request_total_fen,
            }
            for business_day, (_received_at, observation) in sorted(latest_by_day.items())
        ]
        payload = {
            **base,
            "status": "VERIFIED",
            "machine_code": "PAYMENT_REQUEST_OBSERVATION_VERIFIED",
            "points": points,
        }
        atomic_json_write(self.runtime.config.publication_dir / "payment_request_observation.json", payload)
        return payload


class _RawArchiveAuditAccumulator:
    """Consume one fully verified raw attachment at a time.

    The object keeps only capability outcomes, immutable digest/family pairs
    and chart observations.  It deliberately never retains a collection of
    source payloads, so the complete historic audit remains feasible inside a
    bounded cloud worker.
    """

    def __init__(self, runtime: "DailyFundsRuntime"):
        self.runtime = runtime
        self.cashflow = _CashflowObservationAccumulator(runtime)
        self.payment_requests = _PaymentRequestObservationAccumulator(runtime)
        self.occurrence_count = 0
        self.capability_supported = 0
        self.capability_needs_review = 0
        self.integrity_failures: list[ParseError] = []
        self.resolved_families: dict[str, str] = {}
        self.scope: list[tuple[str, str]] = []
        self.inbox: list[tuple[str, int, str]] = []

    def consume(self, attachment: DownloadedAttachment) -> None:
        self.occurrence_count += 1
        self.inbox.append((attachment.message_id_hash, attachment.index, attachment.sha256))
        self.payment_requests.add(attachment)
        family = (
            attachment.family
            if attachment.family in TRANSACTION_FAMILIES | {ACCOUNT_FAMILY}
            else "UNCLASSIFIED"
        )
        prior = self.runtime.state.reusable_capability_scope_receipts(
            parser_version=PARSER_VERSION,
            attachment_sha256s=(attachment.sha256,),
        )
        previous = prior.get(attachment.sha256)
        if previous is not None:
            resolved_family, outcome = previous
            self.resolved_families[attachment.sha256] = resolved_family
            if outcome == "SUPPORTED":
                self.capability_supported += 1
            else:
                self.capability_needs_review += 1
        else:
            inspection = self.runtime._inspect_attachment_capabilities((attachment,))
            if len(inspection.parsed) + len(inspection.failures) != 1:
                raise IngestionError("GIT_READBACK_FAILED")
            self.capability_supported += len(inspection.parsed)
            self.capability_needs_review += len(inspection.failures)
            for item in inspection.parsed:
                if item.facts.source_version != attachment.sha256:
                    raise IngestionError("GIT_READBACK_FAILED")
                self.resolved_families[attachment.sha256] = item.facts.family
            self.integrity_failures.extend(
                failure
                for failure in inspection.failures
                if self.runtime._parse_failure_code(failure) in _SOURCE_INTEGRITY_PARSE_CODES
            )

        resolved_family = self.resolved_families.get(attachment.sha256)
        self.scope.append((attachment.sha256, resolved_family or family))
        if attachment.family in TRANSACTION_FAMILIES:
            self.cashflow.add(attachment)
        elif attachment.family is None and resolved_family in TRANSACTION_FAMILIES:
            self.cashflow.add(replace(attachment, family=resolved_family))


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

    def _current(self, *, strict: bool = False) -> dict[str, Any] | None:
        path = self.config.publication_dir / "current.json"
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            if strict:
                raise ReconciliationError("CURRENT_PROJECTION_INVALID") from exc
            return None
        if not isinstance(payload, Mapping):
            if strict:
                raise ReconciliationError("CURRENT_PROJECTION_INVALID")
            return None
        publication = payload.get("publication")
        if not isinstance(publication, Mapping) or publication.get("status") != "VALID":
            if strict:
                raise ReconciliationError("CURRENT_PROJECTION_INVALID")
            return None
        return dict(payload)

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

    def _history(self, *, strict: bool = False) -> dict[str, Any]:
        if not self._history_path.exists():
            return {"schema_version": "kmfa.daily_funds.history.v1", "days": {}}
        try:
            payload = json.loads(self._history_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            if strict:
                raise ReconciliationError("HISTORY_INVALID") from exc
            return {"schema_version": "kmfa.daily_funds.history.v1", "days": {}}
        if not isinstance(payload, Mapping) or not isinstance(payload.get("days"), Mapping):
            if strict:
                raise ReconciliationError("HISTORY_INVALID")
            return {"schema_version": "kmfa.daily_funds.history.v1", "days": {}}
        return {"schema_version": "kmfa.daily_funds.history.v1", "days": dict(payload["days"])}

    def _record_history(self, report: ReconciliationReport, publication_id: str) -> None:
        if not report.valid:
            raise ReconciliationError("HISTORY_REPORT_NOT_VALID")
        normalized_publication_id = self._lower_hex(publication_id, 64)
        if normalized_publication_id is None:
            raise ReconciliationError("HISTORY_PUBLICATION_ID_INVALID")
        history = self._history(strict=True)
        history["days"][report.business_date.isoformat()] = {
            "status": "VALID",
            "ending_available_fen": report.total_ending_fen,
            "direct_observation": True,
            "coverage_gap": False,
            "carried_forward": False,
            "account_ending_by_hash": {row.account_key_hash: row.ending_fen for row in report.account_reports},
            "publication_id": normalized_publication_id,
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

    @staticmethod
    def _build_source_identity() -> tuple[str, str | None]:
        """Return only a one-way image-layer source marker, or fail closed.

        ``SOURCE_COMMIT`` is supplied by Coolify only while building an image.
        The Dockerfile embeds a precisely formatted source SHA in the image
        layer; the runtime neither reads an environment value nor copies the
        raw SHA into a volume.  A malformed/missing marker is deliberately
        indistinguishable from unavailable build evidence.
        """

        try:
            raw = _BUILD_SOURCE_COMMIT_FILE.read_text(encoding="ascii")
        except (OSError, UnicodeError):
            return "UNKNOWN", None
        if len(raw) != 41 or not raw.endswith("\n"):
            return "UNKNOWN", None
        commit = raw[:-1]
        if len(commit) != 40 or not all(character in "0123456789abcdef" for character in commit):
            return "UNKNOWN", None
        return "BUILD_SOURCE_COMMIT_EMBEDDED", sha256(commit.encode("ascii")).hexdigest()

    def _restore_drill_state(self) -> tuple[str, str | None]:
        receipt = self._read_json_object(self.config.publication_dir / "restore_drill.json")
        if receipt is None:
            return "NOT_YET_RUN", None
        result = self._flow_code(receipt.get("result"))
        observed_at = self._flow_timestamp(receipt.get("observed_at"))
        if result not in {"OK", "IN_PROGRESS", "NEEDS_ATTENTION"}:
            return "UNKNOWN", observed_at
        return result, observed_at

    @staticmethod
    def _source_discovery_state(value: object) -> str:
        """Reduce a poll-stage diagnostic to a fixed values-free enum."""

        candidate = str(value or "UNKNOWN").strip().upper()
        return candidate if candidate in _SOURCE_DISCOVERY_STATES else "UNKNOWN"

    def _historical_backfill_coverage(self, *, now: datetime | None = None) -> dict[str, int | str]:
        """Project only planner coverage, never the historical cursor or dates.

        The cursor is private operational state: exposing it would disclose a
        business-date boundary without proving that any financial fact passed
        parsing or reconciliation.  The owner UI needs the bounded coverage
        count instead, so it can distinguish a healthy scheduler from a
        complete money publication without inventing an amount.
        """

        now = now or datetime.now(UTC)
        try:
            from zoneinfo import ZoneInfo

            local_today = now.astimezone(ZoneInfo("Asia/Shanghai")).date()
        except Exception:
            return {
                "state": "NEEDS_ATTENTION",
                "window_days": _BACKFILL_WINDOW_DAYS,
                "completed_days": 0,
                "remaining_days": _BACKFILL_WINDOW_DAYS,
            }
        first_required = local_today - timedelta(days=_BACKFILL_WINDOW_DAYS)
        raw_cursor = self.state.get("backfill_next_business_date")
        if raw_cursor is None:
            return {
                "state": "NOT_STARTED",
                "window_days": _BACKFILL_WINDOW_DAYS,
                "completed_days": 0,
                "remaining_days": _BACKFILL_WINDOW_DAYS,
            }
        try:
            next_day = date.fromisoformat(raw_cursor)
        except ValueError:
            return {
                "state": "NEEDS_ATTENTION",
                "window_days": _BACKFILL_WINDOW_DAYS,
                "completed_days": 0,
                "remaining_days": _BACKFILL_WINDOW_DAYS,
            }
        completed_days = min(
            _BACKFILL_WINDOW_DAYS,
            max(0, (next_day - first_required).days),
        )
        return {
            "state": "COMPLETE" if completed_days == _BACKFILL_WINDOW_DAYS else "IN_PROGRESS",
            "window_days": _BACKFILL_WINDOW_DAYS,
            "completed_days": completed_days,
            "remaining_days": _BACKFILL_WINDOW_DAYS - completed_days,
        }

    @contextmanager
    def _flow_state_write_lock(self):
        """Serialize flow-state read/modify/write cycles across cron jobs.

        ``atomic_json_write`` prevents a partially written projection, but it
        cannot prevent two independently scheduled jobs from both reading an
        old flow receipt and letting the later writer resurrect a stale
        ``RUNNING`` operation.  The lock lives in the worker-only state volume
        (rather than the app-readable projection volume) and contains no
        source data or configuration.
        """

        self.config.state_dir.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            self.config.state_dir / "flow_state.lock",
            os.O_CREAT | os.O_RDWR,
            0o600,
        )
        try:
            os.fchmod(descriptor, 0o600)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)

    @contextmanager
    def _raw_archive_audit_process_lock(self):
        """Keep a private raw-archive audit single-process for its full lifetime.

        This lock only serializes read-only audits.  It deliberately does not
        share the bounded ``git_writer_lock`` used by a live/archive writer:
        a full sparse census plus deterministic OCR can legitimately outlast a
        15-minute collection window.  The audit pins and rechecks one immutable
        Git commit, so a concurrent writer advancing ``main`` makes the audit
        fail closed rather than mixing snapshots or blocking source intake.
        The process lock has no expiry and remains held until the running audit
        actually exits; a second cron/startup attempt records
        ``RAW_ARCHIVE_AUDIT_LOCK_HELD`` instead of accumulating readers.
        """

        self.config.state_dir.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            self.config.state_dir / "raw_archive_audit.lock",
            os.O_CREAT | os.O_RDWR,
            0o600,
        )
        locked = False
        try:
            os.fchmod(descriptor, 0o600)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise IngestionError("RAW_ARCHIVE_AUDIT_LOCK_HELD") from exc
            locked = True
            yield
        finally:
            try:
                if locked:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)

    @contextmanager
    def _raw_coverage_repair_process_lock(self):
        """Serialize the bounded DWS-to-private-Git coverage reconciliation.

        This lock is deliberately separate from the raw-archive reader and
        the short Git writer lease.  It protects the complete source census so
        two repair requests cannot both download the same missing occurrence;
        the writer lease still serializes the only persistent raw mutation.
        """

        self.config.state_dir.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            self.config.state_dir / "raw_coverage_repair.lock",
            os.O_CREAT | os.O_RDWR,
            0o600,
        )
        locked = False
        try:
            os.fchmod(descriptor, 0o600)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise IngestionError("RAW_COVERAGE_REPAIR_LOCK_HELD") from exc
            locked = True
            yield
        finally:
            try:
                if locked:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)

    @contextmanager
    def _raw_fact_replay_process_lock(self):
        """Serialize a bounded private-raw fact replay and pointer hand-off."""

        self.config.state_dir.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            self.config.state_dir / "raw_fact_replay.lock",
            os.O_CREAT | os.O_RDWR,
            0o600,
        )
        locked = False
        try:
            os.fchmod(descriptor, 0o600)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise IngestionError("RAW_FACT_REPLAY_LOCK_HELD") from exc
            locked = True
            yield
        finally:
            try:
                if locked:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)

    @contextmanager
    def _backfill_process_lock(self):
        """Serialize one historical batch with an automatically releasable lock.

        A historical batch may legitimately take longer than a 15-minute
        trigger interval.  A process lock on the worker-only named volume
        serializes those invocations without leaving an active-looking lease
        behind when Coolify replaces or terminates the container.  The lock is
        deliberately separate from raw-audit and Git-writer locks: audits are
        commit-pinned reads, while Git persists only a short critical section.
        """

        self.config.state_dir.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            self.config.state_dir / "backfill.lock",
            os.O_CREAT | os.O_RDWR,
            0o600,
        )
        locked = False
        try:
            os.fchmod(descriptor, 0o600)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise IngestionError("BACKFILL_LOCK_HELD") from exc
            locked = True
            yield
        finally:
            try:
                if locked:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)

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
        operation_started_at: str | None = None,
        operation_finished_at: str | None = None,
        source_discovery_state: str | None = None,
    ) -> dict[str, Any]:
        with self._flow_state_write_lock():
            return self._write_flow_state_unlocked(
                stage=stage,
                status=status,
                observer_state=observer_state,
                observer_result=observer_result,
                operation_job=operation_job,
                operation_state=operation_state,
                operation_code=operation_code,
                operation_started_at=operation_started_at,
                operation_finished_at=operation_finished_at,
                source_discovery_state=source_discovery_state,
            )

    def _write_flow_state_unlocked(
        self,
        *,
        stage: str | None,
        status: Mapping[str, Any] | None = None,
        observer_state: str | None = None,
        observer_result: str | None = None,
        operation_job: str | None = None,
        operation_state: str | None = None,
        operation_code: str | None = None,
        operation_started_at: str | None = None,
        operation_finished_at: str | None = None,
        source_discovery_state: str | None = None,
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
        prior_source_discovery = previous.get("source_discovery")
        if not isinstance(prior_source_discovery, Mapping):
            prior_source_discovery = {}
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
        # start or terminal receipt per known job in the existing flow-state
        # hand-off.  A missing terminal receipt is operationally meaningful:
        # the owner UI must not turn it into a guessed success or failure.
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
                started_at = self._flow_timestamp(row.get("started_at"))
                if receipt_state == "RUNNING" and started_at is not None:
                    operations[job] = {
                        "state": receipt_state,
                        "code": receipt_code,
                        "started_at": started_at,
                    }
                elif receipt_state in {"SUCCEEDED", "FAILED"} and finished_at is not None:
                    operations[job] = {
                        "state": receipt_state,
                        "code": receipt_code,
                        "finished_at": finished_at,
                    }
        if operation_job is not None:
            if operation_job not in _OPERATION_RECEIPT_JOBS:
                raise ValueError("invalid operation receipt job")
            receipt_state = self._flow_code(operation_state)
            if receipt_state not in _OPERATION_RECEIPT_STATES:
                raise ValueError("invalid operation receipt state")
            if receipt_state == "RUNNING":
                operations[operation_job] = {
                    "state": receipt_state,
                    "code": self._flow_code(operation_code),
                    "started_at": self._flow_timestamp(operation_started_at) or iso_now(),
                }
            else:
                operations[operation_job] = {
                    "state": receipt_state,
                    "code": self._flow_code(operation_code),
                    "finished_at": self._flow_timestamp(operation_finished_at) or iso_now(),
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
        resolved_source_discovery = self._source_discovery_state(
            source_discovery_state
            if source_discovery_state is not None
            else prior_source_discovery.get("state")
        )
        historical_backfill = self._historical_backfill_coverage()
        identity_state, source_commit_fingerprint = self._build_source_identity()
        payload = {
            "schema_version": _FLOW_STATE_SCHEMA,
            "updated_at": iso_now(),
            "deployment": {
                "runtime_state": runtime_state,
                "instance_state": "OBSERVED" if window is not None else "UNKNOWN",
                # This is limited build evidence.  It does not prove the live
                # image digest or deployment record, and no raw source SHA is
                # written outside this immutable container layer.
                "identity_state": identity_state,
                "source_commit_fingerprint": source_commit_fingerprint,
                "runtime_audit_at": self._flow_timestamp(audit.get("observed_at")),
            },
            "schedules": dict(StatusWriter.SCHEDULES),
            "business_flow": business_flow,
            # A narrow diagnostic of the last *live* source poll.  This is
            # deliberately separate from publication truth: an acquired
            # attachment is not a reconciled or published amount.
            "source_discovery": {"state": resolved_source_discovery},
            "operations": operations,
            # This omits the durable cursor and every date/identifier.  It is
            # operational coverage only, never evidence of parsed financial
            # facts or an eligible publication.
            "historical_backfill": historical_backfill,
            # This aggregate is intentionally values-free: it reveals only
            # parser type/outcome counts, never source IDs, filenames, hashes,
            # document text or financial amounts.
            # A parser rule upgrade invalidates old support receipts until the
            # private raw bytes are re-opened under the current parser.  Keep
            # prior records in SQLite for audit, but never project them as
            # current production capability.
            "attachment_capabilities": self.state.capability_matrix(parser_version=PARSER_VERSION),
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

    def record_operation_start(self, *, job: str, code: str) -> dict[str, Any]:
        """Persist a values-free start receipt before dispatching one cron job.

        This makes a hung or interrupted source poll visible as ``RUNNING``
        instead of silently retaining an older terminal receipt.  It does not
        change financial publication truth; only a terminal poll receipt does.
        """

        if job not in _OPERATION_RECEIPT_JOBS:
            raise ValueError("invalid operation receipt job")
        return self._write_flow_state(
            stage=None,
            operation_job=job,
            operation_state="RUNNING",
            operation_code=code,
            operation_started_at=iso_now(),
        )

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
        if self.config.ocr_enabled and not deterministic_ocr_runtime_ready():
            return self.status.write("需处理", "OCR_RUNTIME_UNAVAILABLE", backup_state="UNKNOWN")
        # A new cloud volume has neither a profile receipt nor a recovery
        # bundle.  Do not describe that state as "CONFIG_READY": it needs the
        # one-time protected cloud-terminal bootstrap before any scheduled
        # source work can legitimately begin.  The pinned DWS CLI owns its
        # profile layout, so preflight must not invent an app.json requirement.
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
        ocr_runtime_state = "DISABLED"
        try:
            # A green topology receipt is meaningful only when every runtime
            # secret/config slot (including D1/R2/OCI) has a valid shape.
            self.config.validate()
            config_state = "VALID"
            config_fingerprint = self.config.redacted_fingerprint()
            if self.config.ocr_enabled:
                ocr_runtime_state = "READY" if deterministic_ocr_runtime_ready() else "UNAVAILABLE"
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
        elif ocr_runtime_state == "UNAVAILABLE":
            code = "OCR_RUNTIME_UNAVAILABLE"
        else:
            code = "RUNTIME_AUDIT_OK"

        audit = {
            "schema_version": "kmfa.daily_funds.runtime_audit.v1",
            "observed_at": iso_now(),
            "result": "OK" if code == "RUNTIME_AUDIT_OK" else "NEEDS_ATTENTION",
            "machine_code": code,
            "config_state": config_state,
            "ocr_runtime_state": ocr_runtime_state,
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

    def r2_free_tier_guard(self, *, now: datetime | None = None) -> dict[str, Any]:
        """Refresh the values-free proof required before R2 writes/readback.

        The check is intentionally independent of the 15-minute hot path: it
        issues only Cloudflare control-plane reads every six hours, stores no
        bucket names or amounts, and makes a stale/missing receipt block R2
        rather than guessing that a bucket remains free-tier safe.
        """

        try:
            self.config.validate()
        except ConfigError:
            return self.status.write("需处理", "CONFIG_INVALID", backup_state="UNKNOWN")
        try:
            self._lease_call(
                "r2_guard_lock",
                ttl_seconds=13 * 60,
                code="R2_GUARD_LOCK_HELD",
                callback=lambda: R2FreeTierGuard(self.config).verify_and_write(now=now),
            )
        except IngestionError as exc:
            if exc.code == "R2_GUARD_LOCK_HELD":
                return self.status.write("处理中", exc.code)
            return self.status.write("需处理", "R2_ZERO_CHARGE_GUARD_REQUIRED")
        except R2GuardError as exc:
            self.state.queue_incident(exc.code)
            return self._status_from_current(
                fallback_code=exc.code,
                backup_state="UNKNOWN",
            )
        status = self._status_from_current(
            fallback_code="R2_ZERO_CHARGE_GUARD_OK",
        )
        return {
            "ok": True,
            "code": "R2_ZERO_CHARGE_GUARD_OK",
            "human_status": status["human_status"],
        }

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

    @classmethod
    def _cashflow_observation_rejection_category(cls, error: ParseError) -> str:
        """Reduce a parser failure to one values-free public-safe category.

        The chart projection needs a concrete next repair target, but neither
        attachment metadata nor OCR text can cross the worker boundary.  Keep
        this mapping intentionally small and exhaustive: an unrecognised
        parser error is visible only as ``OTHER_REVIEW``.
        """

        code = cls._parse_failure_code(error)
        if code.startswith("CASHFLOW_OBSERVATION_HEADER") or code == "OCR_HEADER_MAPPING_MISSING":
            return "HEADER_LAYOUT"
        if code == "OCR_LOW_CONFIDENCE":
            return "OCR_CONFIDENCE"
        if code.startswith("CASHFLOW_OBSERVATION_TOTAL"):
            return "FOOTER_RECONCILIATION"
        if code.startswith("CASHFLOW_OBSERVATION_DATE"):
            return "DATE_FIELD"
        if code.startswith("CASHFLOW_OBSERVATION_AMOUNT") or code in {
            "CASHFLOW_OBSERVATION_ZERO_ROW",
            "CASHFLOW_OBSERVATION_ROWS_EMPTY",
        }:
            return "ROW_AMOUNT"
        if code.startswith("OCR_"):
            return "OCR_FORMAT"
        return "OTHER_REVIEW"

    @classmethod
    def _payment_request_rejection_category(cls, error: ParseError) -> str:
        """Reduce payment-request OCR failures to a values-free public label."""

        code = cls._parse_failure_code(error)
        if code.startswith("PAYMENT_REQUEST_TITLE"):
            return "TITLE_CONFIRMATION"
        if code.startswith("PAYMENT_REQUEST_DATE"):
            return "DATE_FIELD"
        if code.startswith("PAYMENT_REQUEST_GRAND_TOTAL_LABEL"):
            return "GRAND_TOTAL_LABEL"
        if code.startswith("PAYMENT_REQUEST_TOTAL"):
            return "GRAND_TOTAL"
        if code.startswith("PAYMENT_REQUEST_OCR") or code.startswith("PAYMENT_REQUEST_IMAGE"):
            return "OCR_FORMAT"
        return "OTHER_REVIEW"

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
                if attachment.family is None:
                    # A missing message title is never a financial family by
                    # itself.  A byte-proven structured attachment may still
                    # establish exactly one complete frozen fact schema; this
                    # is the same dual-schema rule already used for the
                    # explicit generic ``资金明细`` label and prevents native
                    # XLS/XLSX files from being stranded solely by an absent
                    # message title.  Unknown binary types remain capability
                    # evidence only, and OCR retains its separate calibration
                    # gate below.
                    if Path(attachment.filename).suffix.lower() in ALLOWED_SUFFIXES:
                        facts = parse_generic_structured_attachment(
                            filename=attachment.filename,
                            payload=attachment.payload,
                            source=self._source_ref(attachment),
                            mime=attachment.mime,
                        )
                    else:
                        if not (self.config.ocr_enabled and is_ocr_attachment(attachment.filename, payload=attachment.payload)):
                            raise ParseError("UNSUPPORTED_ATTACHMENT")
                        candidate = parse_ocr_attachment(
                            family="资金明细",
                            filename=attachment.filename,
                            payload=attachment.payload,
                            source=self._source_ref(attachment),
                            mime=attachment.mime,
                            min_confidence_bps=self.config.ocr_min_confidence_bps,
                        )
                        profile = self.state.observe_ocr_layout(
                            family=candidate.facts.family,
                            layout_fingerprint=candidate.layout_fingerprint,
                            parser_version=candidate.facts.parser_evidence.parser_version,
                            business_date=candidate.facts.business_date,
                        )
                        if not profile.ready_before:
                            raise ParseError("OCR_PROFILE_CALIBRATING")
                        facts = candidate.facts
                elif attachment.family == _GENERIC_DOCUMENT_FAMILY and Path(attachment.filename).suffix.lower() in ALLOWED_SUFFIXES:
                    facts = parse_generic_structured_attachment(
                        filename=attachment.filename,
                        payload=attachment.payload,
                        source=self._source_ref(attachment),
                        mime=attachment.mime,
                    )
                elif attachment.family == _GENERIC_DOCUMENT_FAMILY and self.config.ocr_enabled and is_ocr_attachment(attachment.filename, payload=attachment.payload):
                    candidate = parse_ocr_attachment(
                        family=_GENERIC_DOCUMENT_FAMILY,
                        filename=attachment.filename,
                        payload=attachment.payload,
                        source=self._source_ref(attachment),
                        mime=attachment.mime,
                        min_confidence_bps=self.config.ocr_min_confidence_bps,
                    )
                    profile = self.state.observe_ocr_layout(
                        family=candidate.facts.family,
                        layout_fingerprint=candidate.layout_fingerprint,
                        parser_version=candidate.facts.parser_evidence.parser_version,
                        business_date=candidate.facts.business_date,
                    )
                    if not profile.ready_before:
                        raise ParseError("OCR_PROFILE_CALIBRATING")
                    facts = candidate.facts
                elif Path(attachment.filename).suffix.lower() in ALLOWED_SUFFIXES:
                    facts = parse_attachment(
                        family=attachment.family,
                        filename=attachment.filename,
                        payload=attachment.payload,
                        source=self._source_ref(attachment),
                        mime=attachment.mime,
                    )
                elif self.config.ocr_enabled and is_ocr_attachment(attachment.filename, payload=attachment.payload):
                    candidate = parse_ocr_attachment(
                        family=attachment.family,
                        filename=attachment.filename,
                        payload=attachment.payload,
                        source=self._source_ref(attachment),
                        mime=attachment.mime,
                        min_confidence_bps=self.config.ocr_min_confidence_bps,
                    )
                    profile = self.state.observe_ocr_layout(
                        family=candidate.facts.family,
                        layout_fingerprint=candidate.layout_fingerprint,
                        parser_version=candidate.facts.parser_evidence.parser_version,
                        business_date=candidate.facts.business_date,
                    )
                    # The candidate which establishes a two-day profile is
                    # still calibration evidence, not a self-approved money
                    # fact.  A later readback of the already-known layout is
                    # required before the regular reconciliation path sees it.
                    if not profile.ready_before:
                        raise ParseError("OCR_PROFILE_CALIBRATING")
                    facts = candidate.facts
                else:
                    raise ParseError("UNSUPPORTED_ATTACHMENT")
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

    def _resolved_ambiguous_source_attachments(
        self,
        attachments: Iterable[DownloadedAttachment],
    ) -> tuple[DownloadedAttachment, ...]:
        """Resolve generic or title-less documents only after byte-proven schema checks.

        This is capability preflight, not monetary publication: each returned
        source still goes through the normal post-mirror parse and
        reconciliation path.  A generic ``资金明细`` label is not promoted
        merely because it was text-matched in a message; title-less reports
        retain the existing OCR-only route.  Any item that cannot establish
        exactly one fact schema remains raw evidence only, while a
        source-lineage failure still blocks the complete batch.
        """

        ambiguous = tuple(
            attachment
            for attachment in attachments
            if attachment.family is None or attachment.family == _GENERIC_DOCUMENT_FAMILY
        )
        if not ambiguous:
            return ()
        inspection = self._inspect_attachment_capabilities(ambiguous)
        integrity_failures = tuple(
            failure
            for failure in inspection.failures
            if self._parse_failure_code(failure) in _SOURCE_INTEGRITY_PARSE_CODES
        )
        if integrity_failures:
            raise integrity_failures[0]
        resolved_families: dict[str, str] = {}
        for item in inspection.parsed:
            source_version = item.facts.source_version
            family = item.facts.family
            if (
                source_version in resolved_families
                or family not in TRANSACTION_FAMILIES | {ACCOUNT_FAMILY}
            ):
                raise ParseError("UNCLASSIFIED_FAMILY_RESOLUTION_INVALID")
            resolved_families[source_version] = family
        return tuple(
            replace(attachment, family=resolved_families[attachment.sha256])
            for attachment in ambiguous
            if attachment.sha256 in resolved_families
        )

    @staticmethod
    def _cashflow_observation_candidates(
        attachments: Iterable[DownloadedAttachment],
        resolved_families: Mapping[str, str],
    ) -> tuple[DownloadedAttachment, ...]:
        """Admit screenshots only after their source family is deterministic.

        An explicitly classified ``资金流水明细`` or ``资金明细`` keeps its
        chart-only review path.  The latter is not promoted into formal
        account/transaction facts merely by this admission: the isolated
        cashflow parser still requires its own visible-header identity or
        fixed-table geometry, same-day two-direction and footer-total proof
        before any chart point exists.  A title-less
        attachment remains admissible only after the same raw-byte parser
        census has resolved it to a transaction family.  This preserves the
        strict formal-reconciliation boundary while allowing an actual
        receipt/payment screenshot to be evaluated by the purpose-built
        chart parser.
        """

        candidates: list[DownloadedAttachment] = []
        for attachment in attachments:
            resolved_family = resolved_families.get(attachment.sha256)
            if attachment.family in TRANSACTION_FAMILIES:
                candidates.append(attachment)
            elif attachment.family is None and resolved_family in TRANSACTION_FAMILIES:
                candidates.append(replace(attachment, family=resolved_family))
        return tuple(candidates)

    def _write_cashflow_observation(
        self,
        attachments: Iterable[DownloadedAttachment],
    ) -> dict[str, Any]:
        """Write a chart-only receipt/payment observation from read-back bytes.

        This projection is intentionally isolated from ``current.json``:
        screenshot receipts can prove daily inflow/outflow totals, but they do
        not carry the account snapshots required for available-balance
        reconciliation.  Any parse gap clears points rather than retaining a
        stale or partial cash-flow chart.
        """

        accumulator = _CashflowObservationAccumulator(self)
        for attachment in attachments:
            accumulator.add(attachment)
        return accumulator.write()

    def _write_payment_request_observation(
        self,
        attachments: Iterable[DownloadedAttachment],
    ) -> dict[str, Any]:
        """Write the independent pending-payment-request projection.

        The helper keeps the exact same raw-byte boundary as the archive audit
        while making the chart-only payment-request contract directly
        testable.  It never invokes the account/transaction publication path.
        """

        accumulator = _PaymentRequestObservationAccumulator(self)
        for attachment in attachments:
            accumulator.add(attachment)
        return accumulator.write()

    def raw_archive_audit(self) -> dict[str, Any]:
        """Audit acquired private raw bytes without reading DWS or publishing money.

        T04 needs a real cloud attachment capability receipt even when a
        bounded DWS history query cannot currently retrieve older pages.  The
        writer therefore re-opens only the acquired private-Git authority,
        validates every source envelope/occurrence/batch/object link, and
        passes those fresh bytes through the existing deterministic parser
        gate.  A parser result here is capability evidence only: it never
        updates D1/R2/OCI, a financial pointer, or source-discovery state.
        """

        try:
            self.config.validate(include_storage=False)
        except ConfigError:
            return self.status.write("需处理", "CONFIG_INVALID")
        try:
            with self._raw_archive_audit_process_lock():
                return self._raw_archive_audit_locked()
        except IngestionError as exc:
            if exc.code == "RAW_ARCHIVE_AUDIT_LOCK_HELD":
                return self.status.write("处理中", exc.code)
            # The precise private archive error remains in neither cron output
            # nor the shared status projection.  The recovery broker receives
            # only a fixed operational class, which remains an explicit
            # non-pass and cannot be promoted to a parser, source-pair, or
            # financial-publication receipt.
            self.state.queue_incident("RAW_ARCHIVE_AUDIT_NEEDS_REVIEW")
            status = self._status_from_current(fallback_code="RAW_ARCHIVE_AUDIT_NEEDS_REVIEW")
            self._write_flow_state(stage="RAW_ARCHIVE_AUDIT_NEEDS_REVIEW", status=status)
            return {
                "ok": False,
                "code": _RAW_ARCHIVE_AUDIT_FAILURE_PROJECTIONS.get(
                    exc.code,
                    "RAW_ARCHIVE_AUDIT_NEEDS_REVIEW",
                ),
            }

    def _raw_archive_audit_locked(self) -> dict[str, Any]:
        """Run one full raw-archive audit while its process lock is held."""

        writer = GitSparseWriter(self.config)
        accumulator = _RawArchiveAuditAccumulator(self)
        # The raw writer pins one private Git commit, validates the complete
        # metadata census, then reopens each bounded payload group from that
        # same commit.  The callback receives a byte-proven attachment only
        # while that small group is resident; it cannot accidentally retain
        # the historic image corpus in memory.
        audit = writer.audit_raw_archive(on_attachment=accumulator.consume)
        if accumulator.occurrence_count != audit.occurrence_count:
            raise IngestionError("GIT_READBACK_FAILED")

        # The chart-only projection has its own OCR/footer gate and remains
        # separate from the formal account-balance publication path.
        accumulator.cashflow.write()
        accumulator.payment_requests.write()
        if accumulator.integrity_failures:
            self.state.queue_incident("RAW_ARCHIVE_AUDIT_NEEDS_REVIEW")
            status = self._status_from_current(fallback_code="RAW_ARCHIVE_AUDIT_NEEDS_REVIEW")
            self._write_flow_state(stage="RAW_ARCHIVE_AUDIT_NEEDS_REVIEW", status=status)
            return {"ok": False, "code": "RAW_ARCHIVE_AUDIT_INTEGRITY_NEEDS_REVIEW"}

        # A capability receipt becomes visible only after this exact complete
        # private-Git census succeeds.  Retaining historic evidence is useful
        # for audit, but projecting it after its raw object has disappeared
        # would overstate the current source coverage.
        self.state.replace_capability_scope(
            parser_version=PARSER_VERSION,
            attachments=accumulator.scope,
        )

        for message_id_hash, index, attachment_sha256 in accumulator.inbox:
            occurrence_key = f"{message_id_hash}:{index}:{attachment_sha256}"
            self.state.note_inbox(
                occurrence_key,
                message_id_hash,
                attachment_sha256,
                "GIT_PERSISTED",
            )
            self.state.mark_inbox(occurrence_key, "ARCHIVED_CAPABILITY_RECORDED")
        code = "RAW_ARCHIVE_AUDIT_NEEDS_REVIEW" if accumulator.capability_needs_review else "RAW_ARCHIVE_AUDITED"
        status = self._status_from_current(fallback_code=code)
        self._write_flow_state(
            stage="RAW_ARCHIVE_AUDIT_NEEDS_REVIEW" if accumulator.capability_needs_review else "RAW_ARCHIVE_AUDITED",
            status=status,
        )
        return {
            "ok": True,
            "code": code,
            "capability_supported": accumulator.capability_supported,
            "capability_needs_review": accumulator.capability_needs_review,
        }

    def raw_coverage_repair(self, *, now: datetime | None = None) -> dict[str, Any]:
        """Repair only source occurrences absent from the private raw authority.

        A completed historical planner is not evidence that a later source
        replay still has every attachment occurrence in private Git.  This
        bounded maintenance operation compares the exact 360-day DWS ledger
        with the private raw occurrence identities, downloads only absences,
        persists them through the normal fresh sparse-readback writer, and
        rechecks coverage.  It never moves a funds publication pointer or
        calls D1/R2/OCI.
        """

        try:
            self.config.validate(include_storage=False)
        except ConfigError:
            return self.status.write("需处理", "CONFIG_INVALID")
        try:
            with self._raw_coverage_repair_process_lock():
                return self._raw_coverage_repair_locked(now=now)
        except IngestionError as exc:
            if exc.code == "RAW_COVERAGE_REPAIR_LOCK_HELD":
                return self.status.write("处理中", exc.code)
            if exc.code == "GIT_WRITER_LOCK_HELD":
                # A concurrent raw append is a live, bounded writer lease, not
                # a source, parser or reconciliation failure.  Preserve the
                # distinction so the public status does not ask for human
                # repair while the authorized writer is still making progress.
                return self.status.write("处理中", "RAW_COVERAGE_REPAIR_GIT_WRITER_LOCK_HELD")
            self.state.queue_incident("RAW_COVERAGE_REPAIR_NEEDS_REVIEW")
            status = self._status_from_current(fallback_code="RAW_COVERAGE_REPAIR_NEEDS_REVIEW")
            self._write_flow_state(stage="RAW_COVERAGE_REPAIR_NEEDS_REVIEW", status=status)
            return {"ok": False, "code": "RAW_COVERAGE_REPAIR_NEEDS_REVIEW"}

    def _raw_coverage_repair_locked(self, *, now: datetime | None) -> dict[str, Any]:
        """Run the repair under one non-reentrant process lock."""

        anchor = now or datetime.now(UTC)
        if anchor.tzinfo is None or anchor.utcoffset() is None:
            raise IngestionError("RAW_COVERAGE_REPAIR_NEEDS_REVIEW")
        anchor = anchor.astimezone(UTC)
        writer = GitSparseWriter(self.config)
        archived: set[tuple[str, int]] = set()

        metadata_audit = getattr(writer, "audit_raw_archive_metadata", None)
        audit_raw_identities = (
            metadata_audit
            if callable(metadata_audit)
            else writer.audit_raw_archive
        )
        try:
            audit_raw_identities(
                on_attachment=lambda attachment: archived.add((attachment.message_id_hash, attachment.index))
            )
        except IngestionError as exc:
            # A first-ever exact source archive has no raw tree to audit.  It
            # is safe to continue with an empty identity set; every source
            # occurrence will then pass through the ordinary writer/readback.
            if exc.code != "SOURCE_MISSING":
                raise

        client = self._dws_client()
        page = client.collect_group_history_v2(anchor - timedelta(days=_BACKFILL_WINDOW_DAYS), anchor)
        candidates = (*client.selected_messages(page), *client.quarantine_messages(page))
        source: dict[tuple[str, int], dict[str, Any]] = {}
        for message in candidates:
            message_id_hash = client.message_id_hash(message)
            attachment_count = client.attachment_count(message)
            for index in range(attachment_count):
                identity = (message_id_hash, index)
                if identity in source:
                    raise IngestionError("RAW_COVERAGE_REPAIR_NEEDS_REVIEW")
                source[identity] = message
        if len(source) > _RAW_COVERAGE_MAX_OCCURRENCES:
            raise IngestionError("RAW_COVERAGE_REPAIR_NEEDS_REVIEW")

        missing = [
            (message, index)
            for (message_id_hash, index), message in source.items()
            if (message_id_hash, index) not in archived
        ]
        recovered: tuple[DownloadedAttachment, ...] = ()
        capability_supported = 0
        capability_needs_review = 0
        download_failures = 0
        if missing:
            downloaded: list[DownloadedAttachment] = []
            for message, index in missing:
                # Media URLs can expire between a history listing and the
                # first resource request.  Retry the same immutable source
                # occurrence exactly once; do not broaden the query, guess a
                # replacement, or turn a failed download into a pass.
                for attempt in range(2):
                    try:
                        downloaded.append(client.download(message, index))
                    except IngestionError:
                        if attempt == 1:
                            download_failures += 1
                        continue
                    break
            if downloaded:
                commit = self._lease_call(
                    "git_writer_lock",
                    ttl_seconds=13 * 60,
                    code="GIT_WRITER_LOCK_HELD",
                    callback=lambda: writer.persist(downloaded),
                )
                recovered = commit.verified_attachments
                if len(recovered) != len(downloaded):
                    raise IngestionError("GIT_READBACK_FAILED")
                for attachment in recovered:
                    occurrence_key = f"{attachment.message_id_hash}:{attachment.index}:{attachment.sha256}"
                    self.state.note_inbox(
                        occurrence_key,
                        attachment.message_id_hash,
                        attachment.sha256,
                        "GIT_PERSISTED",
                    )
                inspection = self._inspect_attachment_capabilities(recovered)
                integrity_failures = tuple(
                    failure
                    for failure in inspection.failures
                    if self._parse_failure_code(failure) in _SOURCE_INTEGRITY_PARSE_CODES
                )
                if integrity_failures:
                    raise IngestionError("GIT_READBACK_FAILED")
                capability_supported = len(inspection.parsed)
                capability_needs_review = len(inspection.failures)
                for attachment in recovered:
                    occurrence_key = f"{attachment.message_id_hash}:{attachment.index}:{attachment.sha256}"
                    self.state.mark_inbox(occurrence_key, "ARCHIVED_CAPABILITY_RECORDED")

        verified: set[tuple[str, int]] = set()
        final_audit = audit_raw_identities(
            on_attachment=lambda attachment: verified.add((attachment.message_id_hash, attachment.index))
        )
        if (
            final_audit.occurrence_count != len(verified)
        ):
            raise IngestionError("RAW_COVERAGE_REPAIR_NEEDS_REVIEW")
        remaining = set(source) - verified
        if remaining:
            # A partial raw write changes the private branch, so an older
            # coverage receipt cannot safely authorize a later fact replay.
            self.state.put(_RAW_COVERAGE_RECEIPT_KEY, "")
            status = self._status_from_current(fallback_code="RAW_COVERAGE_REPAIR_INCOMPLETE")
            self._write_flow_state(stage="RAW_COVERAGE_REPAIR_INCOMPLETE", status=status)
            return {
                "ok": False,
                "code": "RAW_COVERAGE_REPAIR_INCOMPLETE",
                "source_occurrences": len(source),
                "recovered_occurrences": len(recovered),
                "remaining_occurrences": len(remaining),
                "download_failures": download_failures,
                "capability_supported": capability_supported,
                "capability_needs_review": capability_needs_review,
            }

        self._record_raw_coverage_receipt(
            raw_commit_sha=final_audit.commit_sha,
            source_occurrences=len(source),
            verified_occurrences=len(source),
            raw_archive_occurrences=final_audit.occurrence_count,
        )

        code = "RAW_COVERAGE_REPAIRED" if recovered else "RAW_COVERAGE_VERIFIED"
        status = self._status_from_current(fallback_code=code)
        self._write_flow_state(stage=code, status=status)
        return {
            "ok": True,
            "code": code,
            "source_occurrences": len(source),
            "recovered_occurrences": len(recovered),
            "capability_supported": capability_supported,
            "capability_needs_review": capability_needs_review,
        }

    def _record_raw_coverage_receipt(
        self,
        *,
        raw_commit_sha: str,
        source_occurrences: int,
        verified_occurrences: int,
        raw_archive_occurrences: int,
    ) -> None:
        """Persist only the bounded, values-free proof required before replay."""

        if (
            self._lower_hex(raw_commit_sha, 40) is None
            or isinstance(source_occurrences, bool)
            or isinstance(verified_occurrences, bool)
            or isinstance(raw_archive_occurrences, bool)
            or not isinstance(source_occurrences, int)
            or not isinstance(verified_occurrences, int)
            or not isinstance(raw_archive_occurrences, int)
            or source_occurrences <= 0
            or source_occurrences > _RAW_COVERAGE_MAX_OCCURRENCES
            or verified_occurrences != source_occurrences
            or raw_archive_occurrences < source_occurrences
            or raw_archive_occurrences > _RAW_COVERAGE_MAX_OCCURRENCES
        ):
            raise IngestionError("RAW_COVERAGE_REPAIR_NEEDS_REVIEW")
        self.state.put(
            _RAW_COVERAGE_RECEIPT_KEY,
            json.dumps(
                {
                    "schema_version": _RAW_COVERAGE_RECEIPT_SCHEMA,
                    "window_days": _BACKFILL_WINDOW_DAYS,
                    "source_occurrences": source_occurrences,
                    "verified_occurrences": verified_occurrences,
                    "raw_archive_occurrences": raw_archive_occurrences,
                    "raw_commit_sha": raw_commit_sha,
                },
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )

    def _raw_coverage_receipt(self) -> Mapping[str, Any] | None:
        """Return one structurally valid 360-day source-coverage receipt."""

        raw = self.state.get(_RAW_COVERAGE_RECEIPT_KEY)
        if raw is None:
            return None
        try:
            payload = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return None
        if not isinstance(payload, Mapping) or set(payload) != {
            "schema_version",
            "window_days",
            "source_occurrences",
            "verified_occurrences",
            "raw_archive_occurrences",
            "raw_commit_sha",
        }:
            return None
        source_occurrences = payload.get("source_occurrences")
        verified_occurrences = payload.get("verified_occurrences")
        raw_archive_occurrences = payload.get("raw_archive_occurrences")
        raw_commit_sha = self._lower_hex(payload.get("raw_commit_sha"), 40)
        if (
            payload.get("schema_version") != _RAW_COVERAGE_RECEIPT_SCHEMA
            or payload.get("window_days") != _BACKFILL_WINDOW_DAYS
            or isinstance(source_occurrences, bool)
            or isinstance(verified_occurrences, bool)
            or isinstance(raw_archive_occurrences, bool)
            or not isinstance(source_occurrences, int)
            or not isinstance(verified_occurrences, int)
            or not isinstance(raw_archive_occurrences, int)
            or source_occurrences <= 0
            or source_occurrences > _RAW_COVERAGE_MAX_OCCURRENCES
            or verified_occurrences != source_occurrences
            or raw_archive_occurrences < source_occurrences
            or raw_archive_occurrences > _RAW_COVERAGE_MAX_OCCURRENCES
            or raw_commit_sha is None
        ):
            return None
        return {
            "source_occurrences": source_occurrences,
            "verified_occurrences": verified_occurrences,
            "raw_archive_occurrences": raw_archive_occurrences,
            "raw_commit_sha": raw_commit_sha,
        }

    def raw_fact_replay(self, *, now: datetime | None = None) -> dict[str, Any]:
        """Publish only exact historical fact pairs from a coverage-proven raw snapshot."""

        try:
            self.config.validate(include_storage=True)
        except ConfigError:
            return self.status.write("需处理", "CONFIG_INVALID")
        try:
            with self._raw_fact_replay_process_lock():
                return self._raw_fact_replay_locked(now=now)
        except (IngestionError, ParseError, ReconciliationError, PublicationError, R2GuardError, ControlError) as exc:
            code = getattr(exc, "code", str(exc).split(":", 1)[0])
            if code == "RAW_FACT_REPLAY_LOCK_HELD":
                return self.status.write("处理中", code)
            if code == "GIT_WRITER_LOCK_HELD":
                # A fact replay can race a normal raw append.  The replay did
                # not establish a financial failure in that case; it simply
                # yields to the active single writer and remains retryable.
                return self.status.write("处理中", "RAW_FACT_REPLAY_GIT_WRITER_LOCK_HELD")
            status = self.status.write("需处理", str(code))
            self._write_flow_state(stage="RAW_FACT_REPLAY_NEEDS_REVIEW", status=status)
            return {"ok": False, "code": str(code)}

    def _raw_fact_replay_locked(self, *, now: datetime | None) -> dict[str, Any]:
        """Re-open the coverage-pinned raw archive and publish verified pairs only."""

        receipt = self._raw_coverage_receipt()
        if receipt is None:
            raise IngestionError("RAW_COVERAGE_RECEIPT_REQUIRED")
        anchor = now or datetime.now(UTC)
        if anchor.tzinfo is None or anchor.utcoffset() is None:
            raise IngestionError("RAW_FACT_REPLAY_NEEDS_REVIEW")
        anchor = anchor.astimezone(UTC)
        writer = GitSparseWriter(self.config)
        accumulator = _RawFactReplayAccumulator(self)
        # First re-open the complete source-gated raw metadata tree at one
        # immutable commit.  This verifies the 360-day authority without
        # downloading unrelated quarantine bytes into the formal fact lane.
        # Every declared account/flow candidate is then reopened below through
        # the normal byte/hash/batch path before parsing.
        audit = writer.audit_raw_archive_metadata(
            on_attachment=accumulator.index_persisted,
            commit_sha=str(receipt["raw_commit_sha"]),
        )
        if (
            audit.occurrence_count != accumulator.occurrence_count
            or audit.occurrence_count != receipt["raw_archive_occurrences"]
            or audit.commit_sha != receipt["raw_commit_sha"]
        ):
            raise IngestionError("RAW_COVERAGE_RECEIPT_STALE")
        # Keep each fresh sparse read bounded.  This is a parser workload cap,
        # not a source-selection cap: the complete metadata census above has
        # already bound every raw occurrence to the pinned source commit.
        for start in range(0, len(accumulator.declared_candidates), 25):
            candidates = accumulator.declared_candidates[start:start + 25]
            commit = self._lease_call(
                "git_writer_lock",
                ttl_seconds=13 * 60,
                code="GIT_WRITER_LOCK_HELD",
                callback=lambda candidates=candidates: writer.reopen_persisted(
                    candidates,
                    commit_sha=str(receipt["raw_commit_sha"]),
                ),
            )
            if commit.commit_sha != receipt["raw_commit_sha"]:
                raise IngestionError("RAW_COVERAGE_RECEIPT_STALE")
            for attachment in self._deduplicated_attachments(commit.verified_attachments):
                accumulator.consume(attachment)
        pairs, incomplete_days, ambiguous_days = accumulator.pairs()
        if not pairs:
            status = self.status.write("需处理", "RAW_FACT_REPLAY_NO_COMPLETE_PAIR")
            self._write_flow_state(stage="RAW_FACT_REPLAY_NO_COMPLETE_PAIR", status=status)
            return {
                "ok": False,
                "code": "RAW_FACT_REPLAY_NO_COMPLETE_PAIR",
                "source_occurrences": accumulator.occurrence_count,
                "parser_open_occurrences": accumulator.parsed_occurrences,
                "needs_review_occurrences": accumulator.needs_review_occurrences,
                "incomplete_days": incomplete_days,
                "ambiguous_days": ambiguous_days,
            }

        R2FreeTierGuard(self.config).require_fresh_receipt(now=anchor)
        coordinator = self._coordinator()
        published_days = 0
        for index, pair in enumerate(pairs):
            commit = self._lease_call(
                "git_writer_lock",
                ttl_seconds=13 * 60,
                code="GIT_WRITER_LOCK_HELD",
                callback=lambda pair=pair: writer.reopen_persisted(
                    (pair.accounts.persisted, pair.transactions.persisted),
                    commit_sha=str(receipt["raw_commit_sha"]),
                ),
            )
            attachments = self._deduplicated_attachments(commit.verified_attachments)
            if len(attachments) != 2:
                raise IngestionError("GIT_READBACK_FAILED")
            parsed = self._parse(attachments)
            account_facts, transaction_facts = self._latest_complete_pair(parsed)
            expected_versions = {
                pair.accounts.timed_facts.facts.source_version,
                pair.transactions.timed_facts.facts.source_version,
            }
            actual_versions = {
                account_facts.facts.source_version,
                transaction_facts.facts.source_version,
            }
            if (
                account_facts.facts.business_date != pair.business_day
                or transaction_facts.facts.business_date != pair.business_day
                or actual_versions != expected_versions
            ):
                raise IngestionError("GIT_READBACK_FAILED")
            report = reconcile(
                (account_facts.facts, transaction_facts.facts),
                previous_ending_by_account=self._prior_account_balances(pair.business_day),
            )
            balances = self._daily_balances(report)
            custom_line = ThresholdControl(self.config.control_dir).line(balances, report.business_date)
            r2_result = self._lease_call(
                "publisher_lock",
                ttl_seconds=13 * 60,
                code="PUBLISHER_LOCK_HELD",
                callback=lambda attachments=attachments, commit=commit: coordinator.r2.mirror(
                    attachments,
                    git_commit_sha=commit.commit_sha,
                ),
            )
            projection = self._lease_call(
                "publisher_lock",
                ttl_seconds=13 * 60,
                code="PUBLISHER_LOCK_HELD",
                callback=lambda report=report, commit=commit, attachments=attachments, balances=balances, account_facts=account_facts, transaction_facts=transaction_facts, custom_line=custom_line, r2_result=r2_result, index=index: coordinator.publish(
                    report=report,
                    git_commit=commit,
                    attachments=attachments,
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
                    advance_pointer=index == len(pairs) - 1,
                    extra_floating_lines=(custom_line,) if custom_line is not None else (),
                    pre_mirrored=r2_result,
                ),
            )
            self._record_history(report, str(projection.publication["publication_id"]))
            for attachment in attachments:
                occurrence_key = f"{attachment.message_id_hash}:{attachment.index}:{attachment.sha256}"
                self.state.mark_inbox(occurrence_key, "VALID_PUBLISHED")
            published_days += 1

        partial = bool(incomplete_days or ambiguous_days or accumulator.needs_review_occurrences)
        code = "RAW_FACT_REPLAY_PUBLISHED_NEEDS_REVIEW" if partial else "RAW_FACT_REPLAY_PUBLISHED"
        status = self._status_from_current(fallback_code=code)
        self._write_flow_state(
            stage=code,
            status=status,
            source_discovery_state="COMPLETE_PAIR_READY",
        )
        return {
            "ok": True,
            "code": code,
            "source_occurrences": accumulator.occurrence_count,
            "parser_open_occurrences": accumulator.parsed_occurrences,
            "needs_review_occurrences": accumulator.needs_review_occurrences,
            "published_days": published_days,
            "incomplete_days": incomplete_days,
            "ambiguous_days": ambiguous_days,
        }

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
            # A parsed real attachment is enough to distinguish a missing
            # source fact family from an empty history window.  Keep that
            # diagnostic values-free: no amount, message, filename, hash or
            # account identifier crosses the status boundary.
            has_accounts = any(groups.get("accounts") for groups in buckets.values())
            has_transactions = any(groups.get("transactions") for groups in buckets.values())
            if not has_accounts and has_transactions:
                raise ReconciliationError("ACCOUNT_SNAPSHOT_MISSING")
            if has_accounts and not has_transactions:
                raise ReconciliationError("TRANSACTION_FACT_MISSING")
            if has_accounts and has_transactions:
                raise ReconciliationError("SOURCE_FACT_DATE_MISMATCH")
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
            if self._lower_hex(key, 64) is None:
                raise ReconciliationError("PRIOR_BALANCE_KEY_INVALID")
            result[key] = self._journal_fen(value, "PRIOR_BALANCE_NOT_INTEGER_FEN")
        return result

    def _history_prior_balances(self, record: Mapping[str, Any]) -> Mapping[str, int]:
        """Return only a directly observed, identifiably VALID daily close."""

        if record.get("status") != "VALID" or self._lower_hex(record.get("publication_id"), 64) is None:
            raise ReconciliationError("PRIOR_HISTORY_NOT_VALID")
        direct_observation = self._journal_flag(record.get("direct_observation"), "PRIOR_HISTORY_INVALID")
        coverage_gap = self._journal_flag(record.get("coverage_gap"), "PRIOR_HISTORY_INVALID")
        carried_forward = self._journal_flag(record.get("carried_forward"), "PRIOR_HISTORY_INVALID")
        if not direct_observation or coverage_gap or carried_forward:
            raise ReconciliationError("PRIOR_HISTORY_NOT_VALID")
        values = record.get("account_ending_by_hash")
        if not isinstance(values, Mapping):
            raise ReconciliationError("PRIOR_HISTORY_INVALID")
        return self._prior_balance_mapping(values)

    def _current_prior_balances(
        self,
        current: Mapping[str, Any],
        business_date: date | None,
    ) -> Mapping[str, int]:
        publication = current.get("publication")
        if not isinstance(publication, Mapping):
            raise ReconciliationError("PRIOR_PUBLICATION_INVALID")
        if business_date is not None:
            try:
                current_business_date = date.fromisoformat(str(publication["business_date"]))
            except (KeyError, TypeError, ValueError) as exc:
                raise ReconciliationError("PRIOR_PUBLICATION_INVALID") from exc
            # Historical backfill must never borrow a newer (or older)
            # pointer just because it happens to have account aliases.  Only
            # the immediately preceding VALID date is a permissible fallback.
            if current_business_date != business_date - timedelta(days=1):
                return {}
        if self._lower_hex(publication.get("publication_id"), 64) is None:
            raise ReconciliationError("PRIOR_PUBLICATION_INVALID")
        if self._journal_fen(publication.get("reconciliation_difference_fen"), "PRIOR_PUBLICATION_INVALID") != 0:
            raise ReconciliationError("PRIOR_PUBLICATION_INVALID")
        summary = current.get("summary")
        if not isinstance(summary, Mapping):
            raise ReconciliationError("PRIOR_PUBLICATION_INVALID")
        values = summary.get("account_ending_by_hash")
        if not isinstance(values, Mapping):
            raise ReconciliationError("PRIOR_PUBLICATION_INVALID")
        return self._prior_balance_mapping(values)

    def _prior_account_balances(self, business_date: date | None = None) -> Mapping[str, int]:
        if business_date is not None:
            previous_day = (business_date - timedelta(days=1)).isoformat()
            record = self._history(strict=True).get("days", {}).get(previous_day)
            if isinstance(record, Mapping):
                return self._history_prior_balances(record)
        current = self._current(strict=True)
        if not current:
            return {}
        return self._current_prior_balances(current, business_date)

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

        def add_direct_balance(balance: DailyBalance) -> None:
            """Accept exact journal/pointer mirrors, never last-write-wins data."""

            key = balance.business_day.isoformat()
            prior = existing.get(key)
            if prior is not None and prior != balance:
                raise ReconciliationError("DAILY_BALANCE_MIRROR_CONFLICT")
            existing[key] = balance

        for business_day, row in self._history(strict=True).get("days", {}).items():
            try:
                if not isinstance(row, Mapping):
                    raise ReconciliationError("HISTORY_BALANCE_INVALID")
                day = date.fromisoformat(str(business_day))
                if day > report.business_date:
                    continue
                if row.get("status") != "VALID" or self._lower_hex(row.get("publication_id"), 64) is None:
                    raise ReconciliationError("HISTORY_BALANCE_NOT_VALID")
                ending = self._journal_fen(row["ending_available_fen"], "HISTORY_BALANCE_NOT_INTEGER_FEN")
                direct_observation = self._journal_flag(row.get("direct_observation"), "HISTORY_BALANCE_FLAG_INVALID")
                coverage_gap = self._journal_flag(row.get("coverage_gap", False), "HISTORY_BALANCE_FLAG_INVALID")
                carried_forward = self._journal_flag(row.get("carried_forward", False), "HISTORY_BALANCE_FLAG_INVALID")
                if not direct_observation or coverage_gap or carried_forward:
                    raise ReconciliationError("HISTORY_BALANCE_NOT_VALID")
                account_ending = self._prior_balance_mapping(row.get("account_ending_by_hash"))
                if not account_ending or sum(account_ending.values()) != ending:
                    raise ReconciliationError("HISTORY_BALANCE_TOTAL_MISMATCH")
                add_direct_balance(DailyBalance(
                    day,
                    ending,
                    direct_observation,
                    coverage_gap,
                    carried_forward,
                ))
            except ReconciliationError:
                raise
            except (KeyError, TypeError, ValueError) as exc:
                raise ReconciliationError("HISTORY_BALANCE_INVALID") from exc
        current = self._current(strict=True)
        if current:
            current_rows = current.get("daily_balances")
            if not isinstance(current_rows, list):
                raise ReconciliationError("CURRENT_BALANCE_INVALID")
            for row in current_rows:
                try:
                    if not isinstance(row, Mapping):
                        raise ReconciliationError("CURRENT_BALANCE_INVALID")
                    business_day = date.fromisoformat(str(row["business_date"]))
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
                    if coverage_gap or carried_forward:
                        raise ReconciliationError("CURRENT_BALANCE_INVALID")
                    add_direct_balance(DailyBalance(
                        business_day,
                        ending,
                        direct_observation,
                        coverage_gap,
                        carried_forward,
                    ))
                except ReconciliationError:
                    raise
                except (KeyError, TypeError, ValueError) as exc:
                    raise ReconciliationError("CURRENT_BALANCE_INVALID") from exc
        report_ending = self._journal_fen(report.total_ending_fen, "REPORT_BALANCE_NOT_INTEGER_FEN")
        add_direct_balance(DailyBalance(report.business_date, report_ending, True, False))
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
            identity = "\x1f".join((
                transaction.source.attachment_sha256,
                transaction.company,
                transaction.bank or "",
                transaction.account,
                transaction.transaction_id,
            ))
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
            storage_class="STANDARD",
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
        lease_profile: str = "live",
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
        formal_attachments: list[DownloadedAttachment] = []
        commits: list[GitCommit] = []
        # Keep the source diagnosis deliberately ordinal.  The production
        # status hand-off must explain which gate stopped without becoming a
        # second archive of messages, identities, or attachment metadata.
        history_nonempty = False
        target_document_seen = False
        target_attachment_seen = False
        source_discovery_state = "UNKNOWN"
        self.status.write("处理中", "POLLING")

        def persist_page(page) -> None:
            nonlocal history_nonempty, target_document_seen, target_attachment_seen, source_discovery_state
            if page.messages:
                history_nonempty = True
            selected = client.selected_messages(page)
            quarantined = client.quarantine_messages(page)
            if selected:
                target_document_seen = True
            selected_attachment_counts: list[tuple[dict[str, Any], int]] = []
            for message in selected:
                attachment_count = client.attachment_count(message)
                if attachment_count == 0:
                    source_discovery_state = "TARGET_ATTACHMENT_MISSING"
                    raise IngestionError("SOURCE_ATTACHMENT_MISSING")
                target_attachment_seen = True
                selected_attachment_counts.append((message, attachment_count))
            for message in quarantined:
                selected_attachment_counts.append((message, client.attachment_count(message)))

            # Raw batches bind the complete history page, not each message in
            # isolation.  Re-open the whole page only when every occurrence
            # has one durable raw receipt; otherwise retain the original
            # all-source download/write behavior so a partial synthetic batch
            # can never masquerade as the original evidence set.
            cached_attachments: list[PersistedRawAttachment] = []
            page_is_fully_reusable = bool(selected_attachment_counts)
            for message, attachment_count in selected_attachment_counts:
                message_id_hash = client.message_id_hash(message)
                for index in range(attachment_count):
                    attachment_sha256 = self.state.reusable_raw_attachment_sha(message_id_hash, index)
                    cached = (
                        client.reopen_candidate(message, index, attachment_sha256)
                        if attachment_sha256 is not None
                        else None
                    )
                    if cached is None:
                        page_is_fully_reusable = False
                        break
                    cached_attachments.append(cached)
                if not page_is_fully_reusable:
                    break
            if page_is_fully_reusable:
                commit = self._lease_call(
                    "git_writer_lock",
                    ttl_seconds=13 * 60,
                    code="GIT_WRITER_LOCK_HELD",
                    callback=lambda: writer.reopen_persisted(cached_attachments),
                )
                commits.append(commit)
                all_attachments.extend(commit.verified_attachments)
                formal_attachments.extend(
                    attachment for attachment in commit.verified_attachments
                    if attachment.family in _EXPLICIT_FACT_FAMILIES
                )
                return
            page_attachments = [
                client.download(message, index)
                for message, attachment_count in selected_attachment_counts
                for index in range(attachment_count)
            ]
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
                formal_attachments.extend(
                    attachment for attachment in commit.verified_attachments
                    if attachment.family in _EXPLICIT_FACT_FAMILIES
                )

        def empty_source_state() -> str:
            if not history_nonempty:
                return "HISTORY_EMPTY"
            if not target_document_seen:
                return "TARGET_DOCUMENT_NOT_FOUND"
            if not target_attachment_seen:
                return "TARGET_ATTACHMENT_MISSING"
            return "ATTACHMENT_ACQUIRED"

        try:
            pages = poller.poll(
                now=now,
                persist_page=persist_page,
                holder=holder,
                cursor_key=cursor_key,
                high_water_key=high_water_key,
                start_override=start_override,
                lease_profile=lease_profile,
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
                source_discovery_state = empty_source_state()
                raise IngestionError("SOURCE_MATCH_ZERO")
            verified_attachments = self._deduplicated_attachments(all_attachments)
            source_discovery_state = "ATTACHMENT_ACQUIRED"
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
            resolved_ambiguous = self._resolved_ambiguous_source_attachments(verified_attachments)
            candidate_attachments = self._deduplicated_attachments(
                (*formal_attachments, *resolved_ambiguous),
            )
            if not candidate_attachments:
                source_discovery_state = (
                    "GENERIC_DOCUMENT_UNRESOLVED"
                    if any(attachment.family == _GENERIC_DOCUMENT_FAMILY for attachment in verified_attachments)
                    else empty_source_state()
                )
                raise IngestionError("SOURCE_MATCH_ZERO")
            verified_attachments = candidate_attachments
            # The raw Git authority has been re-opened before this point.  R2
            # must mirror those exact bytes before parsing or reconciliation.
            R2FreeTierGuard(self.config).require_fresh_receipt(now=now)
            coordinator = self._coordinator()
            r2_result = self._lease_call(
                "publisher_lock",
                ttl_seconds=13 * 60,
                code="PUBLISHER_LOCK_HELD",
                callback=lambda: coordinator.r2.mirror(verified_attachments, git_commit_sha=commits[-1].commit_sha),
            )
            parsed = self._parse(verified_attachments)
            try:
                account_facts, transaction_facts = self._latest_complete_pair(parsed)
            except ReconciliationError as exc:
                code = str(exc).split(":", 1)[0]
                source_discovery_state = {
                    "SOURCE_MATCH_ZERO": "DOCUMENT_PAIR_MISSING",
                    "ACCOUNT_SNAPSHOT_MISSING": "ACCOUNT_SNAPSHOT_MISSING",
                    "TRANSACTION_FACT_MISSING": "TRANSACTION_FACT_MISSING",
                    "SOURCE_FACT_DATE_MISMATCH": "SOURCE_FACT_DATE_MISMATCH",
                }.get(code, source_discovery_state)
                raise
            source_discovery_state = "COMPLETE_PAIR_READY"
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
            if advance_pointer:
                self._write_flow_state(
                    stage=None,
                    source_discovery_state=source_discovery_state,
                )
            return {
                "ok": True,
                "pages": pages,
                "attachments": len(verified_attachments),
                "publication_id": projection.publication["publication_id"],
                "backup_state": projection.oci_backup_state,
            }
        except (IngestionError, ParseError, ReconciliationError, PublicationError, R2GuardError, ControlError) as exc:
            code = getattr(exc, "code", str(exc).split(":", 1)[0])
            lock_held = str(code).endswith("_LOCK_HELD")
            human_status = "处理中" if lock_held else "需处理"
            status = self.status.write(human_status, str(code))
            self._write_flow_state(
                stage=(
                    "POLLING" if lock_held
                    else "PARSER_NEEDS_REVIEW" if isinstance(exc, ParseError)
                    else "POLL_NEEDS_ATTENTION"
                ),
                status=status,
                # Bounded historical scans must not overwrite the current
                # live-source diagnosis merely because a past business day is
                # legitimately empty.
                source_discovery_state=source_discovery_state if advance_pointer else None,
            )
            return {"ok": False, "code": str(code)}

    def auth_probe(self) -> dict[str, Any]:
        try:
            self.config.validate(include_storage=False)
        except ConfigError:
            return self.status.write("需处理", "CONFIG_INVALID")
        client = self._dws_client()
        now = datetime.now(UTC)

        def probe_history_read() -> None:
            try:
                client.search(now - timedelta(minutes=1), now, None)
            except IngestionError as exc:
                # Keep the per-minute authorization signal aligned with the
                # scheduled collector.  A record-less legacy search response
                # is not an auth failure; only the exact-group, provider-owned
                # full-window reader can settle that protocol ambiguity.
                if exc.code != "DWS_PAGE_RECORDS_MISSING":
                    raise
                client.collect_group_history_v2(now - timedelta(minutes=1), now)

        try:
            self._lease_call(
                "auth_probe_lock",
                ttl_seconds=55,
                code="AUTH_PROBE_LOCK_HELD",
                callback=probe_history_read,
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

        try:
            with self._backfill_process_lock():
                return self._backfill_locked(now=now, max_days=max_days)
        except IngestionError as exc:
            if exc.code != "BACKFILL_LOCK_HELD":
                raise
            # The runner keeps this invocation's receipt in RUNNING only when
            # a real process still owns the flock.  Unlike the former durable
            # lease, a terminated/replaced worker cannot leave this state
            # behind after its process exits.
            return {"ok": False, "completed_days": [], "code": exc.code}

    def _backfill_locked(self, *, now: datetime | None, max_days: int) -> dict[str, Any]:
        """Run a bounded historical batch while ``_backfill_process_lock`` is held."""

        now = now or datetime.now(UTC)
        try:
            from zoneinfo import ZoneInfo
            local_today = now.astimezone(ZoneInfo("Asia/Shanghai")).date()
            local_zone = ZoneInfo("Asia/Shanghai")
        except Exception:  # zoneinfo is part of Python, but keep fail-closed
            return self.status.write("需处理", "TIMEZONE_UNAVAILABLE")
        first_required = local_today - timedelta(days=_BACKFILL_WINDOW_DAYS)
        raw_cursor = self.state.get("backfill_next_business_date")
        try:
            next_day = date.fromisoformat(raw_cursor) if raw_cursor else first_required
        except ValueError:
            return self.status.write("需处理", "BACKFILL_CURSOR_INVALID")
        completed: list[str] = []
        empty_days: list[str] = []
        needs_review_days: list[str] = []
        source_gap_days: list[str] = []
        needs_review_attachments = 0
        for _ in range(max(1, min(max_days, _BACKFILL_BATCH_MAX_DAYS))):
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
                lease_profile="backfill",
            )
            if not result.get("ok"):
                code = result.get("code", "BACKFILL_FAILED")
                if code not in _BACKFILL_CONTINUABLE_SOURCE_CODES:
                    return {"ok": False, "completed_days": completed, "code": code}
                # Preserve the missing attachment as an explicit review item
                # and incident, then advance only this bounded historical day.
                # No facts, balances, publication pointer or replacement
                # source are produced by this path.
                self.state.queue_incident(code)
                completed.append(next_day.isoformat())
                needs_review_days.append(next_day.isoformat())
                source_gap_days.append(next_day.isoformat())
                next_day += timedelta(days=1)
                self.state.put("backfill_next_business_date", next_day.isoformat())
                continue
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
        has_review = bool(needs_review_days)
        outcome_code = f"{base_code}_NEEDS_REVIEW" if has_review else base_code
        status = self._status_from_current(fallback_code=outcome_code)
        self._write_flow_state(
            stage="BACKFILL_COMPLETE_NEEDS_REVIEW" if next_day >= local_today and has_review else (
                "BACKFILLING_NEEDS_REVIEW" if has_review else base_code
            ),
            status=status,
        )
        return {
            "ok": True,
            "completed_days": completed,
            "empty_days": empty_days,
            "needs_review_days": needs_review_days,
            "source_gap_days": source_gap_days,
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
                        "处理中", "PUBLISHER_LOCK_HELD",
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

            # DF-024 calls for five *real working days*, not merely five
            # distinct calendar dates.  A valid weekend publication remains
            # visible as a verified pointer/D1 comparison, but must never
            # advance the deployment observer.  This deliberately uses the
            # portable Monday--Friday definition: no external holiday feed or
            # local calendar is allowed to become a hidden runtime dependency.
            if business_date.weekday() >= 5:
                return self._observer_status(
                    "已更新", "VALID_PUBLISHED",
                    stage="OBSERVER_WAITING_FOR_NEXT_BUSINESS_DATE",
                    observer_state="WAITING_FOR_NEXT_BUSINESS_DATE",
                    observer_result="NON_WORKING_DAY",
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
                    "处理中", "OBSERVER_LOCK_HELD",
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
            runtime = current.get("runtime") if isinstance(current.get("runtime"), Mapping) else {}
            private_publication_commit_sha = self._lower_hex(
                runtime.get("git_publication_commit_sha"),
                40,
            )
            if private_publication_commit_sha is None:
                raise PublicationError("PUBLICATION_INVALID")
            try:
                R2FreeTierGuard(self.config).require_fresh_receipt()
            except R2GuardError as exc:
                raise PublicationError(exc.code) from exc
            r2_store = S3CompatibleStore(
                endpoint_url=self.config.r2_endpoint_url,
                bucket=self.config.r2_bucket,
                access_key_id=self.config.r2_access_key_id,
                secret_access_key=self.config.r2_secret_access_key,
                region="auto",
                storage_class="STANDARD",
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
                git_publication_commit_sha=private_publication_commit_sha,
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
            if exc.code.startswith("R2_ZERO_CHARGE_GUARD_"):
                return self._status_from_current(fallback_code=exc.code, backup_state="UNKNOWN")
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

            def restore_under_publisher_lock():
                restored = RestoreCoordinator(
                    d1=D1Projection(self.config),
                    oci=OciColdBackup(oci_store),
                ).restore(publication_id)
                if (
                    self._lower_hex(getattr(restored, "git_publication_commit_sha", None), 40) is None
                    or self._lower_hex(getattr(restored, "oci_restore_manifest_sha", None), 64) is None
                ):
                    raise PublicationError("RESTORE_ARTIFACT_BINDING_INVALID")
                return restored

            restored = self._lease_call(
                "publisher_lock",
                ttl_seconds=13 * 60,
                code="PUBLISHER_LOCK_HELD",
                callback=restore_under_publisher_lock,
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
            "runtime": {
                "oci_backup_state": "OK",
                "git_publication_commit_sha": restored.git_publication_commit_sha,
                "oci_restore_manifest_sha": restored.oci_restore_manifest_sha,
                "restored_at": iso_now(),
            },
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
