"""S07/P7.3 command API and GET/HEAD replay-safety acceptance tests."""

from __future__ import annotations

import hashlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app import main as main_module
from app.export_jobs import (
    EXPORT_ARTIFACT_TTL_SECONDS,
    EXPORT_JOB_LEASE_SECONDS,
    EXPORT_JOB_RETRY_DELAY_SECONDS,
    ExportJobRepository,
)
from app.export_worker import InjectedExportFailure, run_once

client = TestClient(main_module.app)
START = datetime(2026, 7, 26, 4, 5, 6, tzinfo=timezone.utc)


@dataclass
class FakeClock:
    value: datetime

    def now(self) -> datetime:
        return self.value

    def advance(self, seconds: int) -> None:
        self.value += timedelta(seconds=seconds)


@pytest.fixture
def export_runtime(monkeypatch, tmp_path):
    state = tmp_path / "state"
    clock = FakeClock(START)
    render_count = {"value": 0}

    def snapshot(report_no: int, artifact_format: str):
        if report_no == 404:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="synthetic_missing")
        material = f"synthetic:{report_no}:{artifact_format}".encode()
        return {
            "report_no": report_no,
            "format": artifact_format,
            "title": f"Synthetic report {report_no}",
            "header": {
                "报告等级": "D",
                "质量等级": "Q4",
                "delivery状态": "未解锁（NO_GO）",
                "delivery_allowed": False,
            },
            "watermark": "D 级 ｜ synthetic ｜ delivery_allowed=false",
            "body": "synthetic report body",
            "dispositions": {
                "dispositions": [
                    {
                        "item": "fixture",
                        "status": "closed",
                        "delta_cents": 0,
                        "finding": "synthetic",
                    }
                ]
            },
            "source_bytes": len(material),
            "source_fingerprint": hashlib.sha256(material).hexdigest(),
        }

    def render(snapshot_payload):
        render_count["value"] += 1
        artifact_format = snapshot_payload["format"]
        mark = snapshot_payload["watermark"].encode()
        if artifact_format == "html":
            return b"<!doctype html>" + mark, "text/html; charset=utf-8"
        if artifact_format == "csv":
            return b"\xef\xbb\xbf" + mark, "text/csv; charset=utf-8"
        return b"%PDF-1.4\n" + mark + b"\n%%EOF", "application/pdf"

    monkeypatch.delenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", raising=False)
    monkeypatch.setenv("KMFA_EXPORT_JOBS_ENABLED", "1")
    monkeypatch.setattr(main_module, "APP_STATE_DIR", state)
    monkeypatch.setattr(
        main_module,
        "APP_DB_PATH",
        state / "kmfa_app_state.sqlite3",
    )
    monkeypatch.setattr(main_module, "utc_now", clock.now)
    monkeypatch.setattr(
        main_module,
        "_report_export_snapshot",
        snapshot,
    )
    monkeypatch.setattr(
        main_module,
        "_render_report_export",
        render,
    )
    return {
        "clock": clock,
        "state": state,
        "render_count": render_count,
        "snapshot": snapshot,
    }


def create_job(
    *,
    key: str,
    report_no: int = 1,
    artifact_format: str = "html",
):
    return client.post(
        "/api/exports/jobs",
        headers={"Idempotency-Key": key},
        json={"report_no": report_no, "format": artifact_format},
    )


def semantic_state(state_root: Path):
    database = state_root / "kmfa_app_state.sqlite3"
    tables = {}
    if database.is_file():
        connection = sqlite3.connect(
            f"file:{database}?mode=ro",
            uri=True,
        )
        try:
            connection.execute("PRAGMA query_only=ON")
            names = [
                row[0]
                for row in connection.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                    """
                )
            ]
            for name in names:
                tables[name] = connection.execute(
                    f'SELECT * FROM "{name}" ORDER BY rowid'
                ).fetchall()
        finally:
            connection.close()
    artifacts = {}
    root = state_root / "export-artifacts"
    if root.is_dir():
        artifacts = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.iterdir())
            if path.is_file()
        }
    return {"tables": tables, "artifacts": artifacts}


def test_get_head_inventory_is_replay_safe_and_never_renders(
    export_runtime,
):
    created = create_job(key="inventory-export-key-0001")
    assert created.status_code == 202
    job_id = created.json()["job_id"]
    before = semantic_state(export_runtime["state"])
    before_renders = export_runtime["render_count"]["value"]

    inventory = {
        (route.path, method)
        for route in main_module.app.routes
        if isinstance(route, APIRoute)
        for method in route.methods
        if method in {"GET", "HEAD"}
    }
    assert (
        "/api/报告中心/导出",
        "GET",
    ) in inventory
    assert (
        "/api/报告中心/导出",
        "HEAD",
    ) in inventory
    assert (
        "/api/exports/jobs/{job_id}",
        "GET",
    ) in inventory
    assert (
        "/api/exports/jobs/{job_id}/artifact",
        "HEAD",
    ) in inventory
    assert (
        "/api/exports/jobs",
        "GET",
    ) not in inventory

    probes = [
        ("GET", "/api/报告中心/导出?报告=1&格式=pdf", 405),
        ("HEAD", "/api/报告中心/导出?报告=1&格式=pdf", 405),
        ("GET", f"/api/exports/jobs/{job_id}", 200),
        ("HEAD", f"/api/exports/jobs/{job_id}", 200),
        ("GET", "/api/exports/jobs/metrics", 200),
        ("HEAD", "/api/exports/jobs/metrics", 200),
        ("GET", f"/api/exports/jobs/{job_id}/artifact", 409),
        ("HEAD", f"/api/exports/jobs/{job_id}/artifact", 409),
    ]

    def probe(item):
        method, path, expected = item
        response = client.request(method, path)
        return response.status_code, expected

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(probe, probes * 4))
    assert all(actual == expected for actual, expected in results)
    assert semantic_state(export_runtime["state"]) == before
    assert export_runtime["render_count"]["value"] == before_renders == 0


def test_openapi_exposes_command_status_artifact_cancel_and_deprecation(
    export_runtime,
):
    schema = client.get("/ops/openapi.json").json()
    paths = schema["paths"]
    assert set(paths["/api/exports/jobs"]) == {"post"}
    assert {"get", "head", "delete"} <= set(
        paths["/api/exports/jobs/{job_id}"]
    )
    assert {"get", "head"} <= set(
        paths["/api/exports/jobs/{job_id}/artifact"]
    )
    assert {"get", "head"} <= set(
        paths["/api/exports/jobs/metrics"]
    )
    assert paths["/api/报告中心/导出"]["get"]["deprecated"] is True
    required_headers = paths["/api/exports/jobs"]["post"]["parameters"]
    assert any(
        item["in"] == "header"
        and item["name"] == "Idempotency-Key"
        for item in required_headers
    )


def test_concurrent_idempotency_status_artifact_hash_and_cost_metrics(
    export_runtime,
):
    key = "concurrent-export-key-0001"
    with ThreadPoolExecutor(max_workers=12) as pool:
        responses = list(
            pool.map(lambda _: create_job(key=key), range(24))
        )
    assert {response.status_code for response in responses} == {200, 202}
    assert sum(response.status_code == 202 for response in responses) == 1
    job_ids = {response.json()["job_id"] for response in responses}
    assert len(job_ids) == 1
    job_id = job_ids.pop()

    worker = run_once(limit=2, now=export_runtime["clock"].now())
    assert worker["claimed"] == 1
    assert worker["succeeded"] == 1
    status = client.get(f"/api/exports/jobs/{job_id}")
    assert status.status_code == 200
    payload = status.json()
    assert payload["state"] == "succeeded"
    assert [event["event_kind"] for event in payload["events"]] == [
        "created",
        "claimed",
        "succeeded",
    ]
    assert payload["cost"]["estimated"] >= 1
    assert payload["cost"]["actual"] >= payload["cost"]["estimated"]

    artifact = client.get(f"/api/exports/jobs/{job_id}/artifact")
    assert artifact.status_code == 200
    assert artifact.content.startswith(b"<!doctype html>")
    digest = "sha256:" + hashlib.sha256(artifact.content).hexdigest()
    assert artifact.headers["x-kmfa-sha256"] == digest
    assert payload["artifact"]["sha256"] == digest
    assert artifact.headers["x-kmfa-report-grade"] == "D"
    assert artifact.headers["x-kmfa-quality-grade"] == "Q4"
    assert artifact.headers["x-kmfa-delivery-allowed"] == "false"
    assert artifact.headers["x-kmfa-watermark"] == "applied"
    assert "attachment" in artifact.headers["content-disposition"]
    assert client.head(
        f"/api/exports/jobs/{job_id}/artifact"
    ).content == b""

    replay = create_job(key=key)
    assert replay.status_code == 200
    assert replay.headers["idempotency-replayed"] == "true"
    assert replay.json()["job_id"] == job_id
    assert create_job(
        key=key,
        artifact_format="pdf",
    ).status_code == 409

    metrics = client.get("/api/exports/jobs/metrics").json()
    assert metrics["states"]["succeeded"] == 1
    assert metrics["active"] == 0
    assert metrics["cost"]["actual_total"] == payload["cost"]["actual"]
    assert key.encode() not in (
        export_runtime["state"] / "kmfa_app_state.sqlite3"
    ).read_bytes()


def test_cancel_retry_timeout_failure_and_expiry_with_fake_clock(
    export_runtime,
):
    clock = export_runtime["clock"]

    cancelled = create_job(key="cancelled-export-key-0001").json()
    response = client.delete(
        f"/api/exports/jobs/{cancelled['job_id']}"
    )
    assert response.status_code == 200
    assert response.json()["state"] == "cancelled"
    assert run_once(limit=2, now=clock.now())["claimed"] == 0

    retry_job = create_job(key="retryable-export-key-0001").json()

    def transient(stage, _claim):
        if stage == "before_render":
            raise InjectedExportFailure(
                "export_renderer_unavailable",
                True,
            )

    first = run_once(limit=1, now=clock.now(), fault_hook=transient)
    assert first["retry"] == 1
    assert client.get(
        f"/api/exports/jobs/{retry_job['job_id']}"
    ).json()["state"] == "retry"
    clock.advance(EXPORT_JOB_RETRY_DELAY_SECONDS)
    assert run_once(limit=1, now=clock.now())["succeeded"] == 1

    timeout_job = create_job(key="timeout-export-key-0001").json()
    repository = ExportJobRepository(
        main_module.APP_DB_PATH,
        main_module._export_artifacts_root(),
    )
    claim = repository.claim_next(
        now=clock.now(),
        job_id=timeout_job["job_id"],
    )
    assert claim is not None
    clock.advance(EXPORT_JOB_LEASE_SECONDS)
    assert run_once(limit=1, now=clock.now())["succeeded"] == 1
    timeout_status = client.get(
        f"/api/exports/jobs/{timeout_job['job_id']}"
    ).json()
    assert timeout_status["attempt_count"] == 2
    assert "lease_recovered" in {
        event["event_kind"] for event in timeout_status["events"]
    }

    failed_job = create_job(key="failed-export-key-0001").json()
    for attempt in range(3):
        result = run_once(
            limit=1,
            now=clock.now(),
            fault_hook=transient,
        )
        if attempt < 2:
            assert result["retry"] == 1
            clock.advance(EXPORT_JOB_RETRY_DELAY_SECONDS)
        else:
            assert result["failed"] == 1
    assert client.get(
        f"/api/exports/jobs/{failed_job['job_id']}"
    ).json()["state"] == "failed"

    clock.advance(EXPORT_ARTIFACT_TTL_SECONDS)
    expired_status = client.get(
        f"/api/exports/jobs/{retry_job['job_id']}"
    )
    assert expired_status.json()["state"] == "expired"
    assert client.get(
        f"/api/exports/jobs/{retry_job['job_id']}/artifact"
    ).status_code == 410
    swept = run_once(limit=1, now=clock.now())
    assert swept["expired"] >= 1


def test_flag_rollback_preserves_status_and_artifact(
    export_runtime,
    monkeypatch,
):
    clock = export_runtime["clock"]
    job = create_job(key="rollback-export-key-0001").json()
    assert run_once(limit=1, now=clock.now())["succeeded"] == 1
    artifact_url = f"/api/exports/jobs/{job['job_id']}/artifact"
    expected = client.get(artifact_url).content

    monkeypatch.setenv("KMFA_EXPORT_JOBS_ENABLED", "0")
    assert create_job(key="rollback-new-key-0001").status_code == 503
    assert client.get(
        f"/api/exports/jobs/{job['job_id']}"
    ).json()["state"] == "succeeded"
    assert client.get(artifact_url).content == expected
    assert run_once(limit=1, now=clock.now())["enabled"] is False

    monkeypatch.setenv("KMFA_EXPORT_JOBS_ENABLED", "1")
    assert client.get(artifact_url).content == expected
    assert create_job(key="rollback-new-key-0001").status_code == 202


def test_source_change_and_artifact_integrity_fail_closed(
    export_runtime,
    monkeypatch,
):
    clock = export_runtime["clock"]
    changed = create_job(key="changed-source-key-0001").json()
    original_snapshot = export_runtime["snapshot"]

    def changed_snapshot(report_no, artifact_format):
        payload = original_snapshot(report_no, artifact_format)
        payload["source_fingerprint"] = hashlib.sha256(
            b"changed"
        ).hexdigest()
        return payload

    monkeypatch.setattr(
        main_module,
        "_report_export_snapshot",
        changed_snapshot,
    )
    result = run_once(limit=1, now=clock.now())
    assert result["failed"] == 1
    assert client.get(
        f"/api/exports/jobs/{changed['job_id']}"
    ).json()["error_code"] == "export_source_changed"

    monkeypatch.setattr(
        main_module,
        "_report_export_snapshot",
        original_snapshot,
    )
    complete = create_job(key="integrity-export-key-0001").json()
    assert run_once(limit=1, now=clock.now())["succeeded"] == 1
    repository = ExportJobRepository(
        main_module.APP_DB_PATH,
        main_module._export_artifacts_root(),
        initialize=False,
    )
    path, _ = repository.artifact_path(
        complete["job_id"],
        now=clock.now(),
    )
    path.write_bytes(b"tampered")
    assert client.get(
        f"/api/exports/jobs/{complete['job_id']}/artifact"
    ).status_code == 503


def test_request_validation_and_legacy_deprecation_are_explicit(
    export_runtime,
):
    assert client.post(
        "/api/exports/jobs",
        json={"report_no": 1, "format": "html"},
    ).status_code == 400
    assert create_job(
        key="missing-report-key-0001",
        report_no=404,
    ).status_code == 404
    assert client.post(
        "/api/exports/jobs",
        headers={"Idempotency-Key": "invalid"},
        json={"report_no": 1, "format": "html"},
    ).status_code == 400
    assert client.post(
        "/api/exports/jobs",
        headers={"Idempotency-Key": "extra-field-key-0001"},
        json={
            "report_no": 1,
            "format": "html",
            "watermark": False,
        },
    ).status_code == 422

    legacy = client.get(
        "/api/报告中心/导出?报告=1&格式=pdf&watermark=false"
    )
    assert legacy.status_code == 405
    assert legacy.json()["detail"] == "side_effect_get_retired"
    assert legacy.headers["deprecation"] == "true"
    assert legacy.headers["allow"] == "POST"
    assert export_runtime["render_count"]["value"] == 0
