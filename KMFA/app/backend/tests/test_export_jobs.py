"""S07/P7.3 durable export-job state-machine tests.

Every time transition advances a fixed clock directly.  No test sleeps,
polls a real observation window, or depends on wall-clock passage.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from app import app_state
from app.export_jobs import (
    EXPORT_ARTIFACT_TTL_SECONDS,
    EXPORT_JOB_LEASE_SECONDS,
    EXPORT_JOB_RETRY_DELAY_SECONDS,
    MAX_ACTIVE_COST_UNITS,
    MAX_ACTIVE_EXPORT_JOBS,
    MAX_EXPORT_ATTEMPTS,
    ExportJobCapacity,
    ExportJobConflict,
    ExportJobLeaseLost,
    ExportJobNotFound,
    ExportJobRepository,
    estimated_cost_units,
    export_jobs_enabled,
)

NOW = datetime(2026, 7, 26, 1, 2, 3, tzinfo=timezone.utc)
SOURCE_SHA256 = hashlib.sha256(b"synthetic-report-source").hexdigest()


@pytest.fixture
def repository(tmp_path):
    database = tmp_path / "state" / "kmfa_app_state.sqlite3"
    app_state.init(database)
    return ExportJobRepository(
        database,
        tmp_path / "state" / "export-artifacts",
    )


def create_job(
    repository: ExportJobRepository,
    *,
    key: str = "test-export-key-0001",
    report_no: int = 1,
    artifact_format: str = "html",
    units: int = 1,
    now: datetime = NOW,
):
    return repository.create(
        idempotency_key=key,
        report_no=report_no,
        artifact_format=artifact_format,
        source_fingerprint=SOURCE_SHA256,
        estimated_units=units,
        now=now,
    )


def complete_job(
    repository: ExportJobRepository,
    *,
    key: str = "test-export-key-0001",
    now: datetime = NOW,
):
    job, _ = create_job(repository, key=key, now=now)
    claim = repository.claim_next(now=now, job_id=job["job_id"])
    assert claim is not None
    payload = b"synthetic bounded export"
    artifact = repository.store_artifact(claim, payload)
    completed = repository.complete(
        claim,
        artifact=artifact,
        media_type="text/html; charset=utf-8",
        actual_units=2,
        report_grade="D",
        quality_grade="Q4",
        delivery_allowed=False,
        watermark_applied=True,
        export_record={
            "job_id": claim.job_id,
            "sha256": f"sha256:{artifact.sha256}",
        },
        audit_event={
            "event_id": "AUD-SYNTHETIC-EXPORT",
            "action_type": "export",
        },
        now=now,
    )
    return completed, artifact, payload


def test_flag_is_opt_in_and_rejects_ambiguous_values(monkeypatch):
    monkeypatch.delenv("KMFA_EXPORT_JOBS_ENABLED", raising=False)
    assert export_jobs_enabled() is False
    monkeypatch.setenv("KMFA_EXPORT_JOBS_ENABLED", "true")
    assert export_jobs_enabled() is True
    monkeypatch.setenv("KMFA_EXPORT_JOBS_ENABLED", "enabled")
    assert export_jobs_enabled() is False


def test_read_only_repository_does_not_create_database(tmp_path):
    database = tmp_path / "missing" / "state.sqlite3"
    repository = ExportJobRepository(
        database,
        tmp_path / "artifacts",
        initialize=False,
    )
    assert repository.metrics(now=NOW)["active"] == 0
    with pytest.raises(ExportJobNotFound):
        repository.get("export_aaaaaaaaaaaaaaaaaaaaaaaa")
    assert not database.exists()
    assert not database.parent.exists()


def test_same_idempotency_key_is_one_concurrent_business_result(repository):
    def submit():
        return create_job(repository)

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(lambda _: submit(), range(24)))

    assert len({row["job_id"] for row, _ in results}) == 1
    assert sum(int(created) for _, created in results) == 1
    assert repository.metrics(now=NOW)["states"]["queued"] == 1
    assert len(repository.events(results[0][0]["job_id"])) == 1

    with pytest.raises(ExportJobConflict, match="idempotency_key_conflict"):
        create_job(repository, artifact_format="pdf")


def test_explicit_queue_and_cost_budgets_are_bounded(repository):
    for index in range(MAX_ACTIVE_COST_UNITS):
        create_job(
            repository,
            key=f"budget-test-key-{index:04d}",
            units=1,
        )
        if index + 1 == MAX_ACTIVE_EXPORT_JOBS:
            break
    assert repository.metrics(now=NOW)["active"] == MAX_ACTIVE_EXPORT_JOBS
    with pytest.raises(ExportJobCapacity, match="export_job_capacity_reached"):
        create_job(repository, key="budget-test-key-overflow")

    other = ExportJobRepository(
        repository.db_path.parent / "cost.sqlite3",
        repository.artifacts_root.parent / "cost-artifacts",
    )
    for index in range(MAX_ACTIVE_COST_UNITS // 64):
        create_job(
            other,
            key=f"cost-test-key-{index:04d}",
            units=64,
        )
    with pytest.raises(ExportJobCapacity, match="export_cost_capacity_reached"):
        create_job(other, key="cost-test-key-overflow")


def test_running_limit_cancel_and_late_worker_commit(repository):
    jobs = [
        create_job(repository, key=f"running-key-{index:04d}")[0]
        for index in range(3)
    ]
    first = repository.claim_next(now=NOW, job_id=jobs[0]["job_id"])
    second = repository.claim_next(now=NOW, job_id=jobs[1]["job_id"])
    assert first is not None and second is not None
    assert repository.claim_next(now=NOW, job_id=jobs[2]["job_id"]) is None

    artifact = repository.store_artifact(first, b"late result")
    cancelled = repository.cancel(first.job_id, now=NOW)
    assert cancelled["state"] == "cancelled"
    assert not artifact.path.exists()
    with pytest.raises(ExportJobLeaseLost):
        repository.complete(
            first,
            artifact=artifact,
            media_type="text/html",
            actual_units=2,
            report_grade="D",
            quality_grade="Q4",
            delivery_allowed=False,
            watermark_applied=True,
            export_record={},
            audit_event={},
            now=NOW,
        )
    assert repository.cancel(first.job_id, now=NOW)["state"] == "cancelled"


def test_retry_timeout_and_attempt_exhaustion_use_fake_clock(repository):
    job, _ = create_job(repository)
    claim = repository.claim_next(now=NOW, job_id=job["job_id"])
    assert claim is not None
    retry = repository.fail(
        claim,
        error_code="export_renderer_unavailable",
        retryable=True,
        now=NOW,
    )
    assert retry["state"] == "retry"
    assert (
        repository.claim_next(
            now=NOW + timedelta(seconds=EXPORT_JOB_RETRY_DELAY_SECONDS - 1),
            job_id=job["job_id"],
        )
        is None
    )

    retry_at = NOW + timedelta(seconds=EXPORT_JOB_RETRY_DELAY_SECONDS)
    claim = repository.claim_next(now=retry_at, job_id=job["job_id"])
    assert claim is not None and claim.attempt_count == 2
    orphan = repository.store_artifact(claim, b"crashed worker output")

    lease_boundary = retry_at + timedelta(seconds=EXPORT_JOB_LEASE_SECONDS)
    recovered = repository.claim_next(
        now=lease_boundary,
        job_id=job["job_id"],
    )
    assert recovered is not None
    assert recovered.attempt_count == MAX_EXPORT_ATTEMPTS
    assert not orphan.path.exists()
    failed = repository.fail(
        recovered,
        error_code="export_renderer_unavailable",
        retryable=True,
        now=lease_boundary,
    )
    assert failed["state"] == "failed"
    assert repository.claim_next(
        now=lease_boundary + timedelta(days=1),
        job_id=job["job_id"],
    ) is None
    assert [event["event_kind"] for event in repository.events(job["job_id"])] == [
        "created",
        "claimed",
        "retry_scheduled",
        "claimed",
        "lease_recovered",
        "claimed",
        "failed",
    ]


def test_success_is_atomic_verifiable_and_contains_no_raw_key(repository):
    completed, artifact, payload = complete_job(repository)
    assert completed["state"] == "succeeded"
    path, row = repository.artifact_path(completed["job_id"], now=NOW)
    assert path.read_bytes() == payload
    assert row["artifact_sha256"] == hashlib.sha256(payload).hexdigest()

    export_rows = app_state.read(repository.db_path, "export_records")
    audit_rows = app_state.read(repository.db_path, "audit_events")
    assert export_rows[0]["job_id"] == completed["job_id"]
    assert audit_rows[0]["action_type"] == "export"

    payload_view = repository.payload(completed["job_id"], now=NOW)
    assert payload_view["state"] == "succeeded"
    assert payload_view["artifact"]["sha256"] == (
        f"sha256:{artifact.sha256}"
    )
    assert payload_view["cost"] == {
        "unit": "bounded-render-unit-v1",
        "estimated": 1,
        "actual": 2,
    }

    database_bytes = repository.db_path.read_bytes()
    assert b"test-export-key-0001" not in database_bytes
    assert SOURCE_SHA256.encode() in database_bytes


def test_missing_evidence_table_rolls_back_success_atomically(tmp_path):
    repository = ExportJobRepository(
        tmp_path / "state.sqlite3",
        tmp_path / "artifacts",
    )
    job, _ = create_job(repository)
    claim = repository.claim_next(now=NOW, job_id=job["job_id"])
    assert claim is not None
    artifact = repository.store_artifact(claim, b"atomic fixture")
    with pytest.raises(sqlite3.OperationalError, match="export_records"):
        repository.complete(
            claim,
            artifact=artifact,
            media_type="text/html",
            actual_units=2,
            report_grade="D",
            quality_grade="Q4",
            delivery_allowed=False,
            watermark_applied=True,
            export_record={"job_id": claim.job_id},
            audit_event={"action_type": "export"},
            now=NOW,
        )
    assert repository.get(claim.job_id)["state"] == "running"
    assert [
        event["event_kind"] for event in repository.events(claim.job_id)
    ] == ["created", "claimed"]
    repository.remove_artifact(artifact)


def test_artifact_expiry_projection_and_sweep_are_deterministic(repository):
    completed, artifact, _ = complete_job(repository)
    expiry = NOW + timedelta(seconds=EXPORT_ARTIFACT_TTL_SECONDS)
    assert repository.payload(completed["job_id"], now=expiry)["state"] == "expired"
    with pytest.raises(ExportJobConflict, match="export_artifact_unavailable"):
        repository.artifact_path(completed["job_id"], now=expiry)

    assert repository.get(completed["job_id"])["state"] == "succeeded"
    assert repository.sweep_expired(now=expiry) == 1
    assert repository.get(completed["job_id"])["state"] == "expired"
    assert repository.sweep_expired(now=expiry + timedelta(days=1)) == 0
    assert not artifact.path.exists()


def test_event_ledger_is_database_enforced_append_only(repository):
    job, _ = create_job(repository)
    connection = sqlite3.connect(repository.db_path)
    try:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE export_job_events SET event_kind = 'tampered'"
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("DELETE FROM export_job_events")
    finally:
        connection.close()


def test_cost_estimator_rejects_unbounded_source():
    assert estimated_cost_units(
        source_bytes=1,
        artifact_format="html",
    ) == 1
    assert estimated_cost_units(
        source_bytes=65_537,
        artifact_format="pdf",
    ) == 8
    with pytest.raises(ExportJobCapacity, match="export_source_bytes_exceeded"):
        estimated_cost_units(
            source_bytes=2 * 1024 * 1024 + 1,
            artifact_format="html",
        )


def test_schema_and_events_contain_only_bounded_metadata(repository):
    job, _ = create_job(repository)
    payload = repository.payload(job["job_id"], now=NOW)
    encoded = json.dumps(payload, sort_keys=True)
    assert "synthetic-report-source" not in encoded
    assert "test-export-key-0001" not in encoded
    assert payload["events"][0]["cost_units"] == 1
