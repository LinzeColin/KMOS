"""Projection, mirrors, cold backup, publication pointer and restore oracle."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Protocol

from .config import DailyFundsConfig
from .contracts import (
    DailyBalance,
    FloatingLine,
    HARD_THRESHOLD_FEN,
    SOFT_THRESHOLD_FEN,
    effective_risk,
    floating_month_lines,
)
from .ingestion import DownloadedAttachment, GitCommit
from .reconcile import ReconciliationReport
from .state import StatusWriter, atomic_json_write, iso_now

UTC = timezone.utc


class PublicationError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _canonical_bytes(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _jsonable_lines(lines: Iterable[FloatingLine]) -> list[dict[str, Any]]:
    return [
        {
            "name": line.name,
            "threshold_fen": line.threshold_fen,
            "start": line.start.isoformat(),
            "end": line.end.isoformat(),
            "days": line.days,
            "direct_observations": line.direct_observations,
            "covered_days": line.covered_days,
            "carried_forward_days": line.carried_forward_days,
            "coverage": str(line.coverage),
            "active": line.active,
            "reason": line.reason,
        }
        for line in lines
    ]


class D1Projection:
    """Small Cloudflare D1 REST client; no raw attachment bytes enter D1."""

    def __init__(self, config: DailyFundsConfig):
        self.config = config
        self.url = (
            f"https://api.cloudflare.com/client/v4/accounts/{config.cf_account_id}"
            f"/d1/database/{config.d1_database_id}/query"
        )

    def _query(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        decoded = self._request({"sql": sql, "params": params or []})
        result = decoded.get("result")
        if isinstance(result, list) and result:
            first = result[0]
            if isinstance(first, Mapping) and isinstance(first.get("results"), list):
                return [dict(row) for row in first["results"] if isinstance(row, Mapping)]
        return []

    def _request(self, payload: object) -> Mapping[str, Any]:
        body = _canonical_bytes(payload)
        request = urllib.request.Request(
            self.url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.config.cf_api_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                decoded = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            raise PublicationError("D1_FAILED") from exc
        if not isinstance(decoded, Mapping) or decoded.get("success") is not True:
            raise PublicationError("D1_FAILED")
        # Cloudflare wraps a multi-statement request in a successful outer API
        # response even when an individual statement reports failure.  A
        # publication may not treat that partial result as a D1 transaction.
        result = decoded.get("result")
        if not isinstance(result, list) or any(
            not isinstance(item, Mapping) or item.get("success") is not True
            for item in result
        ):
            raise PublicationError("D1_FAILED")
        return decoded

    def _batch(self, statements: Iterable[tuple[str, list[Any]]]) -> None:
        # Cloudflare D1 executes a query batch as one transaction.  If a D1
        # endpoint rejects the batch shape, the method fails closed before the
        # public pointer is touched; it never degrades to partial row writes.
        statements_payload = [{"sql": sql, "params": params} for sql, params in statements]
        if not statements_payload:
            return
        # Cloudflare's REST API accepts ``{batch:[...]}``, not a bare JSON
        # array.  Keep this explicitly shaped and tested because a rejected
        # batch must fail before any publication pointer can move.
        self._request({"batch": statements_payload})

    def ensure_schema(self) -> None:
        statements = (
            """CREATE TABLE IF NOT EXISTS daily_funds_publications (
                publication_id TEXT PRIMARY KEY, business_date TEXT NOT NULL,
                status TEXT NOT NULL, reconciliation_difference_fen INTEGER NOT NULL,
                git_commit_sha TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS daily_funds_daily_balances (
                publication_id TEXT NOT NULL, business_date TEXT NOT NULL, scope TEXT NOT NULL,
                ending_available_fen INTEGER NOT NULL, direct_observation INTEGER NOT NULL,
                coverage_gap INTEGER NOT NULL, carried_forward INTEGER NOT NULL,
                PRIMARY KEY (publication_id, business_date, scope)
            )""",
            """CREATE TABLE IF NOT EXISTS daily_funds_transactions (
                publication_id TEXT NOT NULL, transaction_key_hash TEXT NOT NULL,
                business_date TEXT NOT NULL, inflow_fen INTEGER NOT NULL, outflow_fen INTEGER NOT NULL,
                adjustment_fen INTEGER NOT NULL, internal_transfer INTEGER NOT NULL,
                source_version TEXT NOT NULL, message_id_hash TEXT NOT NULL,
                PRIMARY KEY (publication_id, transaction_key_hash)
            )""",
            """CREATE TABLE IF NOT EXISTS daily_funds_account_snapshots (
                publication_id TEXT NOT NULL, account_key_hash TEXT NOT NULL,
                business_date TEXT NOT NULL, company_id TEXT NOT NULL,
                bank_id TEXT NOT NULL, account_alias TEXT NOT NULL,
                opening_available_fen INTEGER, ending_available_fen INTEGER NOT NULL,
                source_version TEXT NOT NULL, message_id_hash TEXT NOT NULL,
                PRIMARY KEY (publication_id, account_key_hash)
            )""",
        )
        for statement in statements:
            self._query(statement)

    def project(
        self,
        publication: Mapping[str, Any],
        daily_balances: Iterable[DailyBalance],
        transaction_rows: Iterable[Mapping[str, Any]],
        account_rows: Iterable[Mapping[str, Any]],
    ) -> None:
        self.ensure_schema()
        publication_id = str(publication["publication_id"])
        statements: list[tuple[str, list[Any]]] = [
            ("DELETE FROM daily_funds_daily_balances WHERE publication_id=?", [publication_id]),
            ("DELETE FROM daily_funds_transactions WHERE publication_id=?", [publication_id]),
            ("DELETE FROM daily_funds_account_snapshots WHERE publication_id=?", [publication_id]),
            (
                """INSERT OR REPLACE INTO daily_funds_publications
                (publication_id,business_date,status,reconciliation_difference_fen,git_commit_sha,payload_json,created_at)
                VALUES(?,?,?,?,?,?,?)""",
                [
                    publication_id,
                    publication["business_date"],
                    publication["status"],
                    publication["reconciliation_difference_fen"],
                    publication["git_commit_sha"],
                    _canonical_bytes(publication).decode("utf-8"),
                    publication["created_at"],
                ],
            ),
        ]
        for balance in daily_balances:
            statements.append((
                """INSERT INTO daily_funds_daily_balances
                (publication_id,business_date,scope,ending_available_fen,direct_observation,coverage_gap,carried_forward)
                VALUES(?,?,?,?,?,?,?)""",
                [
                    publication_id,
                    balance.business_day.isoformat(),
                    "global",
                    balance.ending_available_fen,
                    int(balance.direct_observation),
                    int(balance.coverage_gap),
                    int(balance.carried_forward),
                ],
            ))
        for row in transaction_rows:
            statements.append((
                """INSERT INTO daily_funds_transactions
                (publication_id,transaction_key_hash,business_date,inflow_fen,outflow_fen,adjustment_fen,internal_transfer,source_version,message_id_hash)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                [
                    publication_id,
                    row["transaction_key_hash"],
                    row["business_date"],
                    row["inflow_fen"],
                    row["outflow_fen"],
                    row["adjustment_fen"],
                    int(bool(row["internal_transfer"])),
                    row["source_version"],
                    row["message_id_hash"],
                ],
            ))
        for row in account_rows:
            statements.append((
                """INSERT INTO daily_funds_account_snapshots
                (publication_id,account_key_hash,business_date,company_id,bank_id,account_alias,
                 opening_available_fen,ending_available_fen,source_version,message_id_hash)
                VALUES(?,?,?,?,?,?,?,?,?,?)""",
                [
                    publication_id,
                    row["account_key_hash"],
                    row["business_date"],
                    row["company_id"],
                    row["bank_id"],
                    row["account_alias"],
                    row.get("opening_available_fen"),
                    row["ending_available_fen"],
                    row["source_version"],
                    row["message_id_hash"],
                ],
            ))
        self._batch(statements)

    def oracle(self, publication_id: str) -> Mapping[str, Any]:
        rows = self._query(
            "SELECT publication_id,reconciliation_difference_fen,status,payload_json FROM daily_funds_publications WHERE publication_id=?",
            [publication_id],
        )
        if len(rows) != 1:
            raise PublicationError("D1_ORACLE_MISSING")
        row = rows[0]
        if row.get("status") != "VALID" or row.get("reconciliation_difference_fen") != 0:
            raise PublicationError("D1_ORACLE_RECONCILIATION_FAILED")
        try:
            publication = json.loads(str(row["payload_json"]))
            business_date = str(publication["business_date"])
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise PublicationError("D1_ORACLE_PUBLICATION_INVALID") from exc
        if not isinstance(publication, Mapping) or publication.get("publication_id") != publication_id:
            raise PublicationError("D1_ORACLE_PUBLICATION_INVALID")
        # Receipt success says D1 accepted the batch, not that every critical
        # projection row is queryable or coherent.  This read-back Oracle
        # proves both fact families arrived and that their account total equals
        # the daily-balance read model that will feed the owner UI.
        checks = self._query(
            """SELECT
                 (SELECT COUNT(*) FROM daily_funds_account_snapshots
                   WHERE publication_id=? AND business_date=?) AS account_count,
                 (SELECT COUNT(*) FROM daily_funds_transactions
                   WHERE publication_id=? AND business_date=?) AS transaction_count,
                 (SELECT COALESCE(SUM(ending_available_fen),0) FROM daily_funds_account_snapshots
                   WHERE publication_id=? AND business_date=?) AS account_ending_fen,
                 (SELECT COUNT(*) FROM daily_funds_daily_balances
                   WHERE publication_id=? AND business_date=? AND scope='global') AS balance_count,
                 (SELECT ending_available_fen FROM daily_funds_daily_balances
                   WHERE publication_id=? AND business_date=? AND scope='global') AS balance_ending_fen""",
            [publication_id, business_date, publication_id, business_date, publication_id, business_date,
             publication_id, business_date, publication_id, business_date],
        )
        if len(checks) != 1:
            raise PublicationError("D1_ORACLE_PROJECTION_MISSING")
        check = checks[0]
        try:
            account_count = int(check["account_count"])
            transaction_count = int(check["transaction_count"])
            balance_count = int(check["balance_count"])
            account_ending = int(check["account_ending_fen"])
            balance_ending = int(check["balance_ending_fen"])
        except (KeyError, TypeError, ValueError) as exc:
            raise PublicationError("D1_ORACLE_PROJECTION_MISSING") from exc
        if account_count < 1 or transaction_count < 1 or balance_count != 1:
            raise PublicationError("D1_ORACLE_PROJECTION_MISSING")
        if account_ending != balance_ending:
            raise PublicationError("D1_ORACLE_RECONCILIATION_FAILED")
        return row

    def export(self, publication_id: str) -> bytes:
        row = self.oracle(publication_id)
        balances = self._query(
            "SELECT business_date,scope,ending_available_fen,direct_observation,coverage_gap,carried_forward FROM daily_funds_daily_balances WHERE publication_id=? ORDER BY business_date",
            [publication_id],
        )
        transactions = self._query(
            "SELECT transaction_key_hash,business_date,inflow_fen,outflow_fen,adjustment_fen,internal_transfer,source_version,message_id_hash FROM daily_funds_transactions WHERE publication_id=? ORDER BY transaction_key_hash",
            [publication_id],
        )
        accounts = self._query(
            "SELECT account_key_hash,business_date,company_id,bank_id,account_alias,opening_available_fen,ending_available_fen,source_version,message_id_hash FROM daily_funds_account_snapshots WHERE publication_id=? ORDER BY account_key_hash",
            [publication_id],
        )
        return _canonical_bytes({"publication": row, "daily_balances": balances, "transactions": transactions, "account_snapshots": accounts})


class ObjectStore(Protocol):
    def put_bytes(self, key: str, payload: bytes, *, metadata: Mapping[str, str] | None = None) -> None: ...
    def get_bytes(self, key: str) -> bytes: ...


class S3CompatibleStore:
    """Used for both Cloudflare R2 and OCI Object Storage endpoints."""

    def __init__(self, *, endpoint_url: str, bucket: str, access_key_id: str, secret_access_key: str, region: str):
        try:
            import boto3  # type: ignore[import-not-found]
            from botocore.config import Config  # type: ignore[import-not-found]
        except ImportError as exc:
            raise PublicationError("OBJECT_STORE_RUNTIME_DEPENDENCY_MISSING") from exc
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
            config=Config(s3={"addressing_style": "path"}),
        )

    def put_bytes(self, key: str, payload: bytes, *, metadata: Mapping[str, str] | None = None) -> None:
        try:
            self.client.put_object(Bucket=self.bucket, Key=key, Body=payload, Metadata=dict(metadata or {}))
            head = self.client.head_object(Bucket=self.bucket, Key=key)
        except Exception as exc:
            raise PublicationError("OBJECT_STORE_FAILED") from exc
        if int(head.get("ContentLength", -1)) != len(payload):
            raise PublicationError("OBJECT_STORE_READBACK_FAILED")
        expected_sha = str((metadata or {}).get("sha256") or "")
        actual_sha = str((head.get("Metadata") or {}).get("sha256") or "")
        if expected_sha and actual_sha != expected_sha:
            raise PublicationError("OBJECT_STORE_READBACK_FAILED")

    def get_bytes(self, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except Exception as exc:
            raise PublicationError("OBJECT_STORE_FAILED") from exc


class R2Mirror:
    def __init__(self, store: ObjectStore):
        self.store = store

    def mirror(self, attachments: Iterable[DownloadedAttachment], *, git_commit_sha: str) -> tuple[str, bytes]:
        rows: list[dict[str, Any]] = []
        for attachment in attachments:
            key = f"daily-funds/sha256/{attachment.sha256}"
            self.store.put_bytes(key, attachment.payload, metadata={"sha256": attachment.sha256})
            rows.append({"key": key, "sha256": attachment.sha256, "size_bytes": len(attachment.payload)})
        manifest = {
            "schema_version": "kmfa.daily_funds.r2_manifest.v1",
            "git_commit_sha": git_commit_sha,
            "objects": sorted(rows, key=lambda row: str(row["sha256"])),
            "created_at": iso_now(),
        }
        payload = _canonical_bytes(manifest)
        manifest_sha = sha256(payload).hexdigest()
        self.store.put_bytes(f"daily-funds/manifests/{manifest_sha}.json", payload, metadata={"sha256": manifest_sha})
        return manifest_sha, payload


class OciColdBackup:
    def __init__(self, store: ObjectStore):
        self.store = store

    def backup(
        self,
        *,
        publication_id: str,
        publication_sha256: str,
        git_bundle: bytes,
        d1_export: bytes,
        r2_inventory: bytes,
    ) -> str:
        artifacts = {
            "git_bundle": git_bundle,
            "d1_export": d1_export,
            "r2_inventory": r2_inventory,
        }
        inventory = {
            name: {"key": f"daily-funds/{publication_id}/{name}", "sha256": sha256(payload).hexdigest(), "size_bytes": len(payload)}
            for name, payload in artifacts.items()
        }
        manifest = {
            "schema_version": "kmfa.daily_funds.oci_restore_manifest.v1",
            "publication_id": publication_id,
            "publication_sha256": publication_sha256,
            "artifacts": inventory,
            "created_at": iso_now(),
        }
        manifest_payload = _canonical_bytes(manifest)
        inventory["restore_manifest"] = {
            "key": f"daily-funds/{publication_id}/restore_manifest.json",
            "sha256": sha256(manifest_payload).hexdigest(),
            "size_bytes": len(manifest_payload),
        }
        for name, payload in artifacts.items():
            self.store.put_bytes(inventory[name]["key"], payload, metadata={"sha256": inventory[name]["sha256"]})
        self.store.put_bytes(inventory["restore_manifest"]["key"], manifest_payload, metadata={"sha256": inventory["restore_manifest"]["sha256"]})
        return inventory["restore_manifest"]["sha256"]

    def restore_artifacts(self, publication_id: str) -> tuple[Mapping[str, Any], Mapping[str, bytes]]:
        """Fetch and hash-verify the immutable OCI restore set.

        This method does not mutate D1 or the UI pointer.  Callers can run it
        in an empty environment, then make the pointer swap only after the D1
        rebuild Oracle succeeds.
        """

        key = f"daily-funds/{publication_id}/restore_manifest.json"
        try:
            manifest_payload = self.store.get_bytes(key)
            manifest = json.loads(manifest_payload.decode("utf-8"))
        except (PublicationError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PublicationError("RESTORE_MANIFEST_UNAVAILABLE") from exc
        if not isinstance(manifest, Mapping) or manifest.get("publication_id") != publication_id:
            raise PublicationError("RESTORE_MANIFEST_INVALID")
        if not isinstance(manifest.get("publication_sha256"), str) or len(str(manifest["publication_sha256"])) != 64:
            raise PublicationError("RESTORE_MANIFEST_INVALID")
        inventory = manifest.get("artifacts")
        if not isinstance(inventory, Mapping):
            raise PublicationError("RESTORE_MANIFEST_INVALID")
        recovered: dict[str, bytes] = {}
        for name in ("git_bundle", "d1_export", "r2_inventory"):
            descriptor = inventory.get(name)
            if not isinstance(descriptor, Mapping):
                raise PublicationError("RESTORE_MANIFEST_INVALID")
            object_key = descriptor.get("key")
            expected_sha = descriptor.get("sha256")
            expected_size = descriptor.get("size_bytes")
            if not isinstance(object_key, str) or not isinstance(expected_sha, str) or not isinstance(expected_size, int):
                raise PublicationError("RESTORE_MANIFEST_INVALID")
            try:
                payload = self.store.get_bytes(object_key)
            except PublicationError as exc:
                raise PublicationError("RESTORE_ARTIFACT_UNAVAILABLE") from exc
            if len(payload) != expected_size or sha256(payload).hexdigest() != expected_sha:
                raise PublicationError("RESTORE_ARTIFACT_HASH_MISMATCH")
            recovered[name] = payload
        return manifest, recovered


@dataclass(frozen=True)
class PublishedProjection:
    publication: Mapping[str, Any]
    snapshot: Mapping[str, Any]
    oci_backup_state: str


class PublicationCoordinator:
    """Implements the no-premature-pointer publication protocol."""

    def __init__(
        self,
        *,
        publication_dir: str | Path,
        status: StatusWriter,
        d1: D1Projection,
        r2: R2Mirror,
        oci: OciColdBackup,
    ):
        self.publication_dir = Path(publication_dir)
        self.status = status
        self.d1 = d1
        self.r2 = r2
        self.oci = oci
        self.current_path = self.publication_dir / "current.json"

    def _make_publication(
        self,
        *,
        report: ReconciliationReport,
        git_commit: GitCommit,
        r2_manifest_sha: str,
        floating_lines: tuple[FloatingLine, ...],
    ) -> dict[str, Any]:
        if not report.valid:
            raise PublicationError("RECONCILIATION_FAILED")
        if len(report.source_versions) < 2:
            raise PublicationError("SOURCE_VERSION_PAIR_MISSING")
        active_lines = [line.threshold_fen for line in floating_lines if line.active and line.threshold_fen is not None]
        risk, dynamic = effective_risk(report.total_ending_fen, active_lines)
        created_at = iso_now()
        identity = "|".join((report.business_date.isoformat(), git_commit.commit_sha, *report.source_versions, r2_manifest_sha))
        publication_id = sha256(identity.encode("utf-8")).hexdigest()
        return {
            "publication_id": publication_id,
            "business_date": report.business_date.isoformat(),
            "status": "VALID",
            "source_versions": [{"source_version": version} for version in report.source_versions],
            "reconciliation_difference_fen": report.difference_fen,
            "threshold_snapshot": {
                "currency": "CNY",
                "fixed": {"hard_fen": HARD_THRESHOLD_FEN, "soft_fen": SOFT_THRESHOLD_FEN},
                "floating": _jsonable_lines(floating_lines),
                "fixed_risk": risk if risk in {"正常", "关注", "高风险"} else "正常",
                "dynamic_flag": dynamic,
            },
            "created_at": created_at,
            "git_commit_sha": git_commit.commit_sha,
            "d1_projection_version": "kmfa.daily_funds.d1.v1",
            "r2_manifest_sha256": r2_manifest_sha,
            "oci_backup_state": "PENDING",
        }

    def publish(
        self,
        *,
        report: ReconciliationReport,
        git_commit: GitCommit,
        attachments: Iterable[DownloadedAttachment],
        daily_balances: Iterable[DailyBalance],
        transaction_rows: Iterable[Mapping[str, Any]],
        account_rows: Iterable[Mapping[str, Any]] = (),
        private_publication_sink: Callable[[Mapping[str, Any]], str] | None = None,
        git_bundle_sink: Callable[[], bytes] | None = None,
        advance_pointer: bool = True,
        extra_floating_lines: Iterable[FloatingLine] = (),
        pre_mirrored: tuple[str, bytes] | None = None,
    ) -> PublishedProjection:
        balances = tuple(daily_balances)
        transactions = tuple(transaction_rows)
        accounts = tuple(account_rows)
        if not report.valid:
            raise PublicationError("RECONCILIATION_FAILED")
        # R2 must be complete before parsing/reconciliation can produce a user
        # visible pointer; a controlled OCI lag is the sole asynchronous stage.
        if pre_mirrored is None:
            try:
                r2_sha, r2_inventory = self.r2.mirror(attachments, git_commit_sha=git_commit.commit_sha)
            except PublicationError as exc:
                raise PublicationError("R2_FAILED") from exc
        else:
            r2_sha, r2_inventory = pre_mirrored
        as_of = report.business_date + timedelta(days=1)
        floating_lines = (*floating_month_lines(as_of, balances), *tuple(extra_floating_lines))
        publication = self._make_publication(
            report=report,
            git_commit=git_commit,
            r2_manifest_sha=r2_sha,
            floating_lines=floating_lines,
        )
        try:
            self.d1.project(publication, balances, transactions, accounts)
            self.d1.oracle(str(publication["publication_id"]))
        except PublicationError as exc:
            raise PublicationError("D1_FAILED") from exc
        if private_publication_sink is not None:
            try:
                private_publication_sink(publication)
            except Exception as exc:
                raise PublicationError("GIT_WRITE_FAILED") from exc
        offsite_bundle = git_commit.bundle_bytes
        if git_bundle_sink is not None:
            try:
                offsite_bundle = git_bundle_sink()
            except Exception as exc:
                raise PublicationError("GIT_WRITE_FAILED") from exc
        if not offsite_bundle:
            raise PublicationError("GIT_BUNDLE_EMPTY")
        active_lines = [line.threshold_fen for line in floating_lines if line.active and line.threshold_fen is not None]
        risk, dynamic = effective_risk(report.total_ending_fen, active_lines)
        snapshot: dict[str, Any] = {
            "schema_version": "kmfa.daily_funds.current_projection.v1",
            "publication": publication,
            "summary": {
                "total_available_fen": report.total_ending_fen,
                "risk_label": risk,
                "dynamic_flag": dynamic,
                "by_company_ending_fen": report.by_company_ending_fen,
                "by_bank_ending_fen": report.by_bank_ending_fen,
                "account_ending_by_hash": {
                    row.account_key_hash: row.ending_fen for row in report.account_reports
                },
            },
            "daily_balances": [
                {
                    "business_date": item.business_day.isoformat(),
                    "ending_available_fen": item.ending_available_fen,
                    "direct_observation": item.direct_observation,
                    "coverage_gap": item.coverage_gap,
                    "carried_forward": item.carried_forward,
                }
                for item in balances
            ],
            "transactions": [dict(row) for row in transactions],
        }
        # This is the only pointer swap.  Historical backfill validates and
        # projects its own publication but is not allowed to replace a newer
        # live day in the UI.
        if advance_pointer:
            atomic_json_write(self.current_path, snapshot)
            self.status.write(
                "已更新",
                "VALID_PUBLISHED",
                effective_business_date=report.business_date.isoformat(),
                last_verified_at=publication["created_at"],
                publication_id=str(publication["publication_id"]),
                backup_state="PENDING",
            )
        oci_state = "OK"
        try:
            d1_export = self.d1.export(str(publication["publication_id"]))
            self.oci.backup(
                publication_id=str(publication["publication_id"]),
                publication_sha256=sha256(_canonical_bytes(publication)).hexdigest(),
                git_bundle=offsite_bundle,
                d1_export=d1_export,
                r2_inventory=r2_inventory,
            )
        except PublicationError:
            # F-011: OCI lag cannot destroy a valid live publication; it is
            # visible and retried by the independent cold-backup schedule.
            oci_state = "LAG"
        # ``publication`` is immutable and is written byte-identically to D1,
        # private Git and the pointer.  OCI state is operational status, not a
        # late mutation of the canonical publication record.
        snapshot["runtime"] = {"oci_backup_state": oci_state}
        if advance_pointer:
            atomic_json_write(self.current_path, snapshot)
            self.status.write(
                "已更新",
                "VALID_PUBLISHED",
                effective_business_date=report.business_date.isoformat(),
                last_verified_at=publication["created_at"],
                publication_id=str(publication["publication_id"]),
                backup_state=oci_state,
            )
        return PublishedProjection(snapshot["publication"], snapshot, oci_state)


class RestoreOracle:
    """Verify a rebuilt projection before a caller exposes it to KMFA."""

    @staticmethod
    def verify(*, restored_publication: Mapping[str, Any], expected_publication_sha: str, expected_difference_fen: int = 0) -> None:
        actual_sha = sha256(_canonical_bytes(restored_publication)).hexdigest()
        if actual_sha != expected_publication_sha:
            raise PublicationError("RESTORE_HASH_MISMATCH")
        if restored_publication.get("reconciliation_difference_fen") != expected_difference_fen:
            raise PublicationError("RESTORE_RECONCILIATION_FAILED")
        if restored_publication.get("status") != "VALID":
            raise PublicationError("RESTORE_PUBLICATION_INVALID")

    @staticmethod
    def verify_git_bundle(bundle: bytes, *, expected_commit_sha: str) -> None:
        """Prove that the OCI Git artifact is a usable complete bundle.

        A hash only proves that the bytes OCI returned are the bytes it stored.
        Recovery also needs to know that Git can import those bytes and that the
        raw-source commit cited by the canonical publication is actually in the
        bundle.  Do this in a throw-away bare repository, so no local checkout
        or existing Git state can make a bad bundle appear valid.
        """

        if len(expected_commit_sha) != 40 or any(char not in "0123456789abcdef" for char in expected_commit_sha):
            raise PublicationError("RESTORE_GIT_BUNDLE_INVALID")
        if not bundle:
            raise PublicationError("RESTORE_GIT_BUNDLE_INVALID")
        try:
            with tempfile.TemporaryDirectory(prefix="daily-funds-restore-git-") as temp:
                root = Path(temp)
                bundle_path = root / "private-db.bundle"
                bare_repo = root / "verify.git"
                bundle_path.write_bytes(bundle)
                commands = (
                    (["git", "init", "--bare", "--quiet", str(bare_repo)], None),
                    (["git", "bundle", "verify", str(bundle_path)], bare_repo),
                    (["git", "bundle", "unbundle", str(bundle_path)], bare_repo),
                    (["git", "cat-file", "-e", f"{expected_commit_sha}^{{commit}}"], bare_repo),
                )
                for command, cwd in commands:
                    result = subprocess.run(
                        command,
                        cwd=str(cwd) if cwd is not None else None,
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=60,
                    )
                    if result.returncode != 0:
                        raise PublicationError("RESTORE_GIT_BUNDLE_INVALID")
        except (OSError, subprocess.TimeoutExpired):
            raise PublicationError("RESTORE_GIT_BUNDLE_INVALID") from None

    @staticmethod
    def decode_d1_export(
        payload: bytes,
        *,
        publication_id: str,
        expected_publication_sha: str,
    ) -> tuple[Mapping[str, Any], tuple[DailyBalance, ...], tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
        """Validate the OCI D1 export and return only rebuild-safe records."""

        try:
            decoded = json.loads(payload.decode("utf-8"))
            row = decoded["publication"]
            publication = json.loads(row["payload_json"])
            raw_balances = decoded["daily_balances"]
            raw_transactions = decoded["transactions"]
            raw_accounts = decoded["account_snapshots"]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise PublicationError("RESTORE_D1_EXPORT_INVALID") from exc
        if not isinstance(publication, Mapping) or str(publication.get("publication_id")) != publication_id:
            raise PublicationError("RESTORE_D1_EXPORT_INVALID")
        RestoreOracle.verify(restored_publication=publication, expected_publication_sha=expected_publication_sha)
        if not isinstance(raw_balances, list) or not isinstance(raw_transactions, list) or not isinstance(raw_accounts, list):
            raise PublicationError("RESTORE_D1_EXPORT_INVALID")
        balances: list[DailyBalance] = []
        transactions: list[dict[str, Any]] = []
        accounts: list[dict[str, Any]] = []
        try:
            for row in raw_balances:
                if not isinstance(row, Mapping):
                    raise TypeError
                balances.append(DailyBalance(
                    date.fromisoformat(str(row["business_date"])),
                    int(row["ending_available_fen"]),
                    bool(row["direct_observation"]),
                    bool(row["coverage_gap"]),
                    bool(row.get("carried_forward")),
                ))
            for row in raw_transactions:
                if not isinstance(row, Mapping):
                    raise TypeError
                transactions.append({
                    "transaction_key_hash": str(row["transaction_key_hash"]),
                    "business_date": str(row["business_date"]),
                    "inflow_fen": int(row["inflow_fen"]),
                    "outflow_fen": int(row["outflow_fen"]),
                    "adjustment_fen": int(row["adjustment_fen"]),
                    "internal_transfer": bool(row["internal_transfer"]),
                    "source_version": str(row["source_version"]),
                    "message_id_hash": str(row["message_id_hash"]),
                })
            for row in raw_accounts:
                if not isinstance(row, Mapping):
                    raise TypeError
                accounts.append({
                    "account_key_hash": str(row["account_key_hash"]),
                    "business_date": str(row["business_date"]),
                    "company_id": str(row["company_id"]),
                    "bank_id": str(row["bank_id"]),
                    "account_alias": str(row["account_alias"]),
                    "opening_available_fen": None if row.get("opening_available_fen") is None else int(row["opening_available_fen"]),
                    "ending_available_fen": int(row["ending_available_fen"]),
                    "source_version": str(row["source_version"]),
                    "message_id_hash": str(row["message_id_hash"]),
                })
        except (KeyError, TypeError, ValueError) as exc:
            raise PublicationError("RESTORE_D1_EXPORT_INVALID") from exc
        return publication, tuple(balances), tuple(transactions), tuple(accounts)


@dataclass(frozen=True)
class RestoredProjection:
    publication: Mapping[str, Any]
    daily_balances: tuple[DailyBalance, ...]
    transaction_rows: tuple[dict[str, Any], ...]
    account_rows: tuple[dict[str, Any], ...]


class RestoreCoordinator:
    """Rebuild D1 from OCI's verified copy without trusting local runtime state."""

    def __init__(self, *, d1: D1Projection, oci: OciColdBackup):
        self.d1 = d1
        self.oci = oci

    def restore(self, publication_id: str) -> RestoredProjection:
        manifest, artifacts = self.oci.restore_artifacts(publication_id)
        publication, balances, transactions, accounts = RestoreOracle.decode_d1_export(
            artifacts["d1_export"],
            publication_id=publication_id,
            expected_publication_sha=str(manifest["publication_sha256"]),
        )
        expected_r2 = str(publication.get("r2_manifest_sha256") or "")
        if sha256(artifacts["r2_inventory"]).hexdigest() != expected_r2:
            raise PublicationError("RESTORE_R2_INVENTORY_MISMATCH")
        RestoreOracle.verify_git_bundle(
            artifacts["git_bundle"],
            expected_commit_sha=str(publication.get("git_commit_sha") or ""),
        )
        self.d1.project(publication, balances, transactions, accounts)
        self.d1.oracle(publication_id)
        return RestoredProjection(publication, balances, transactions, accounts)
