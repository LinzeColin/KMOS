#!/usr/bin/env python3
"""S07/P7.3 exact-image export-job Oracle.

Only a deterministic synthetic report is mounted over the image report tree.
Business time is advanced directly inside one-shot workers; no acceptance
assertion depends on sleep, soak, an observation window, or a full test suite.
The only bounded HTTP wait is process-readiness synchronization.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

from file_security_flow import HttpResult, _run, _wait_http

CONTAINER_RE = re.compile(r"^kmfa-p73-[a-z0-9-]{1,32}$")
IMAGE_RE = re.compile(r"^[A-Za-z0-9._:/@-]{1,300}$")
PRIVATE_SOURCE_MARKERS = (
    "recovery_code",
    "workspace_secret",
    "cf-access-jwt",
    "KMFA_S3_SECRET_ACCESS_KEY",
)


class ExportApi:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResult:
        encoded = (
            json.dumps(body, sort_keys=True).encode()
            if body is not None
            else None
        )
        request = urllib.request.Request(
            f"{self.base_url}{quote(path, safe='/?=&%:._-')}",
            data=encoded,
            method=method,
            headers={
                "Accept": "application/json",
                **(
                    {"Content-Type": "application/json"}
                    if encoded is not None
                    else {}
                ),
                **(headers or {}),
            },
        )
        try:
            response = urllib.request.urlopen(request, timeout=30)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return HttpResult(
                status=response.status,
                headers={
                    key.lower(): value
                    for key, value in response.headers.items()
                },
                set_cookies=(),
                body=response.read(),
            )

    def create(
        self,
        *,
        key: str,
        report_no: int = 1,
        artifact_format: str = "html",
    ) -> HttpResult:
        return self.request(
            "POST",
            "/api/exports/jobs",
            body={
                "report_no": report_no,
                "format": artifact_format,
            },
            headers={"Idempotency-Key": key},
        )


@dataclass
class Runtime:
    image: str
    state_dir: Path
    fixture_dir: Path
    container: str
    port: int

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def stop(self) -> None:
        _run("docker", "rm", "-f", self.container, check=False)

    def start(self, *, enabled: bool) -> None:
        self.stop()
        self.state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.state_dir.chmod(0o700)
        _run(
            "docker",
            "run",
            "--detach",
            "--name",
            self.container,
            "--publish",
            f"127.0.0.1:{self.port}:8000",
            "--env",
            "KMFA_PRIVATE_OPS_REQUIRE_ACCESS=0",
            "--env",
            (
                "KMFA_EXPORT_JOBS_ENABLED=1"
                if enabled
                else "KMFA_EXPORT_JOBS_ENABLED=0"
            ),
            "--mount",
            (
                f"type=bind,src={self.state_dir.resolve()},"
                "dst=/var/lib/kmfa/state"
            ),
            "--mount",
            (
                f"type=bind,src={self.fixture_dir.resolve()},"
                "dst=/opt/kmfa/KMOS/KMFA/stage_artifacts,readonly"
            ),
            self.image,
        )
        _wait_http(f"{self.base_url}/healthz")

    def worker_once(
        self,
        *,
        expect_failure: bool = False,
    ) -> dict[str, Any]:
        result = _run(
            "docker",
            "exec",
            "--env",
            "KMFA_EXPORT_JOBS_ENABLED=1",
            self.container,
            "python3",
            "-m",
            "app.export_worker",
            "--once",
            "--limit",
            "2",
            check=not expect_failure,
        )
        if expect_failure:
            assert result.returncode == 1, result.stderr
        return json.loads(result.stdout)

    def python(self, source: str, *, enabled: bool = True) -> dict[str, Any]:
        result = _run(
            "docker",
            "exec",
            "--env",
            (
                "KMFA_EXPORT_JOBS_ENABLED=1"
                if enabled
                else "KMFA_EXPORT_JOBS_ENABLED=0"
            ),
            self.container,
            "python3",
            "-c",
            source,
        )
        return json.loads(result.stdout)


def _fixture(root: Path) -> Path:
    if root.exists():
        shutil.rmtree(root)
    report = root / "DT5_DATA0019_report_no1"
    human = report / "human"
    machine = report / "machine"
    human.mkdir(parents=True)
    machine.mkdir()
    (human / "report.md").write_text(
        "# Synthetic fixture report\n\n"
        "This bounded report contains fixture-only content.\n"
        "Amount fixture: 0.00. No user, employee, finance, or recovery data.\n",
        encoding="utf-8",
    )
    (machine / "dispositions.json").write_text(
        json.dumps(
            {
                "dispositions": [
                    {
                        "item": "fixture-row",
                        "status": "closed",
                        "delta_cents": 0,
                        "finding": "synthetic-only",
                    }
                ]
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return root


def _semantic_state(state_dir: Path) -> dict[str, Any]:
    database = state_dir / "kmfa_app_state.sqlite3"
    tables: dict[str, list[list[Any]]] = {}
    if database.is_file():
        connection = sqlite3.connect(
            f"file:{database}?mode=ro",
            uri=True,
        )
        try:
            connection.execute("PRAGMA query_only=ON")
            names = [
                str(row[0])
                for row in connection.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                    """
                )
            ]
            for name in names:
                tables[name] = [
                    list(row)
                    for row in connection.execute(
                        f'SELECT * FROM "{name}" ORDER BY rowid'
                    )
                ]
        finally:
            connection.close()
    artifact_root = state_dir / "export-artifacts"
    artifacts = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(artifact_root.glob("*"))
        if path.is_file()
    }
    return {"tables": tables, "artifacts": artifacts}


def _db_counts(state_dir: Path) -> dict[str, int]:
    connection = sqlite3.connect(
        state_dir / "kmfa_app_state.sqlite3"
    )
    try:
        return {
            table: int(
                connection.execute(
                    f'SELECT COUNT(*) FROM "{table}"'
                ).fetchone()[0]
            )
            for table in (
                "export_jobs",
                "export_job_events",
                "export_records",
                "audit_events",
            )
        }
    finally:
        connection.close()


def _job_ref(job_id: str) -> str:
    return hashlib.sha256(job_id.encode()).hexdigest()[:16]


def _retry_oracle(runtime: Runtime) -> dict[str, Any]:
    source = """
import json
from datetime import timedelta
from app.export_jobs import utc_now
from app.export_worker import InjectedExportFailure, run_once
def fault(stage, claim):
    if stage == "before_render":
        raise InjectedExportFailure("export_renderer_unavailable", True)
base = utc_now()
first = run_once(limit=1, now=base, fault_hook=fault)
second = run_once(limit=1, now=base + timedelta(seconds=5))
print(json.dumps({
    "first": {k:first[k] for k in ("claimed","retry","failed","succeeded")},
    "second": {k:second[k] for k in ("claimed","retry","failed","succeeded")},
}, sort_keys=True))
"""
    return runtime.python(source)


def _timeout_oracle(runtime: Runtime, job_id: str) -> dict[str, Any]:
    source = f"""
import json
from datetime import timedelta
from app import main
from app.export_jobs import ExportJobRepository, utc_now
from app.export_worker import run_once
base = utc_now()
repository = ExportJobRepository(
    main.APP_DB_PATH,
    main._export_artifacts_root(),
)
claim = repository.claim_next(now=base, job_id={job_id!r})
result = run_once(limit=1, now=base + timedelta(seconds=60))
payload = repository.payload({job_id!r}, now=base + timedelta(seconds=60))
print(json.dumps({{
    "claimed_initially": claim is not None,
    "succeeded": result["succeeded"],
    "attempt_count": payload["attempt_count"],
    "lease_recovered": any(
        event["event_kind"] == "lease_recovered"
        for event in payload["events"]
    ),
}}, sort_keys=True))
"""
    return runtime.python(source)


def _expire_oracle(runtime: Runtime, job_id: str) -> dict[str, Any]:
    source = f"""
import json
from datetime import timedelta
from app import main
from app.export_jobs import (
    EXPORT_ARTIFACT_TTL_SECONDS,
    ExportJobRepository,
    utc_now,
)
repository = ExportJobRepository(
    main.APP_DB_PATH,
    main._export_artifacts_root(),
)
future = utc_now() + timedelta(seconds=EXPORT_ARTIFACT_TTL_SECONDS + 1)
count = repository.sweep_expired(now=future)
row = repository.get({job_id!r})
print(json.dumps({{"expired_count":count,"state":row["state"]}}, sort_keys=True))
"""
    return runtime.python(source)


def _browser_oracle(
    runtime: Runtime,
    out_dir: Path,
) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise AssertionError("Playwright is required without --skip-browser") from error

    errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(accept_downloads=True)
        page.on(
            "console",
            lambda message: (
                errors.append(message.text)
                if message.type == "error"
                else None
            ),
        )
        page.goto(f"{runtime.base_url}/ops/app", wait_until="networkidle")
        page.get_by_role("tab", name="报告下载").click()
        row = page.get_by_role("row").filter(
            has_text="Synthetic fixture report"
        )
        row.wait_for()
        with page.expect_response(
            lambda response: (
                response.url.endswith("/api/exports/jobs")
                and response.request.method == "POST"
            )
        ) as creation:
            row.get_by_role("button", name="创建作业").first.click()
        assert creation.value.status == 202
        worker = runtime.worker_once()
        assert worker["succeeded"] == 1
        with page.expect_response(
            lambda response: (
                "/api/exports/jobs/" in response.url
                and not response.url.endswith("/artifact")
                and response.request.method == "GET"
            )
        ):
            row.get_by_role("button", name="刷新状态").click()
        row.get_by_text("可下载", exact=True).wait_for()
        with page.expect_download() as download_info:
            row.get_by_role("link", name="下载").click()
        download = download_info.value
        download_path = download.path()
        assert download_path is not None
        payload = Path(download_path).read_bytes()
        assert payload.startswith(b"<!doctype html")
        screenshot = out_dir / "export-job-ui.png"
        page.screenshot(path=str(screenshot), full_page=True)
        browser.close()
    assert not errors, errors
    return {
        "created": True,
        "worker_succeeded": True,
        "download_sha256": hashlib.sha256(payload).hexdigest(),
        "console_errors": 0,
        "screenshot_sha256": hashlib.sha256(
            screenshot.read_bytes()
        ).hexdigest(),
    }


def run_flow(arguments: argparse.Namespace) -> dict[str, Any]:
    state_dir = Path(arguments.state_dir).resolve()
    out_dir = Path(arguments.out_dir).resolve()
    fixture_dir = out_dir.parent / f".{arguments.container_name}-fixture"
    out_dir.mkdir(parents=True, exist_ok=True)
    _fixture(fixture_dir)
    runtime = Runtime(
        image=arguments.image,
        state_dir=state_dir,
        fixture_dir=fixture_dir,
        container=arguments.container_name,
        port=arguments.port,
    )
    api = ExportApi(runtime.base_url)
    trace: list[dict[str, Any]] = []

    try:
        runtime.start(enabled=True)
        baseline_before = _semantic_state(state_dir)
        legacy = api.request(
            "GET",
            "/api/报告中心/导出?报告=1&格式=pdf",
        )
        legacy_head = api.request(
            "HEAD",
            "/api/报告中心/导出?报告=1&格式=pdf",
        )
        assert legacy.status == legacy_head.status == 405
        assert _semantic_state(state_dir) == baseline_before
        trace.append(
            {
                "case": "legacy_get_head",
                "status": [legacy.status, legacy_head.status],
                "business_state_delta": 0,
            }
        )

        idempotency_key = "p73-exact-image-idempotency-0001"
        with ThreadPoolExecutor(max_workers=12) as pool:
            responses = list(
                pool.map(
                    lambda _: api.create(key=idempotency_key),
                    range(24),
                )
            )
        assert {response.status for response in responses} == {200, 202}
        assert sum(response.status == 202 for response in responses) == 1
        job_ids = {response.json()["job_id"] for response in responses}
        assert len(job_ids) == 1
        first_job = job_ids.pop()
        worker = runtime.worker_once()
        assert worker["claimed"] == worker["succeeded"] == 1
        first_status = api.request(
            "GET",
            f"/api/exports/jobs/{first_job}",
        )
        first_artifact = api.request(
            "GET",
            f"/api/exports/jobs/{first_job}/artifact",
        )
        assert first_status.status == first_artifact.status == 200
        artifact_sha256 = hashlib.sha256(
            first_artifact.body
        ).hexdigest()
        assert first_status.json()["artifact"]["sha256"] == (
            f"sha256:{artifact_sha256}"
        )
        assert first_artifact.headers["x-kmfa-sha256"] == (
            f"sha256:{artifact_sha256}"
        )
        assert first_artifact.headers["x-kmfa-watermark"] == "applied"
        assert first_artifact.headers["content-disposition"].startswith(
            "attachment;"
        )
        trace.append(
            {
                "case": "concurrent_idempotency",
                "submissions": len(responses),
                "created": 1,
                "business_results": 1,
                "job_ref": _job_ref(first_job),
            }
        )

        replay_before = _semantic_state(state_dir)
        probes = [
            ("GET", f"/api/exports/jobs/{first_job}", 200),
            ("HEAD", f"/api/exports/jobs/{first_job}", 200),
            ("GET", f"/api/exports/jobs/{first_job}/artifact", 200),
            ("HEAD", f"/api/exports/jobs/{first_job}/artifact", 200),
            ("GET", "/api/exports/jobs/metrics", 200),
            ("HEAD", "/api/exports/jobs/metrics", 200),
            ("GET", "/api/报告中心/导出?报告=1", 405),
            ("HEAD", "/api/报告中心/导出?报告=1", 405),
        ]

        def probe(item: tuple[str, str, int]) -> tuple[int, int]:
            method, path, expected = item
            return api.request(method, path).status, expected

        with ThreadPoolExecutor(max_workers=8) as pool:
            probe_results = list(pool.map(probe, probes * 3))
        assert all(
            actual == expected
            for actual, expected in probe_results
        )
        assert _semantic_state(state_dir) == replay_before
        trace.append(
            {
                "case": "get_head_replay",
                "requests": len(probe_results),
                "business_state_delta": 0,
                "unauthorized_renderer_invocations": 0,
            }
        )

        cancelled = api.create(
            key="p73-cancelled-job-key-0001",
        ).json()
        cancellation = api.request(
            "DELETE",
            f"/api/exports/jobs/{cancelled['job_id']}",
        )
        assert cancellation.status == 200
        assert cancellation.json()["state"] == "cancelled"
        assert runtime.worker_once()["claimed"] == 0

        retry = api.create(
            key="p73-retry-job-key-0001",
            artifact_format="csv",
        ).json()
        retry_result = _retry_oracle(runtime)
        assert retry_result["first"]["retry"] == 1
        assert retry_result["second"]["succeeded"] == 1
        retry_status = api.request(
            "GET",
            f"/api/exports/jobs/{retry['job_id']}",
        )
        assert retry_status.json()["attempt_count"] == 2

        timeout = api.create(
            key="p73-timeout-job-key-0001",
            artifact_format="pdf",
        ).json()
        timeout_result = _timeout_oracle(
            runtime,
            timeout["job_id"],
        )
        assert timeout_result == {
            "attempt_count": 2,
            "claimed_initially": True,
            "lease_recovered": True,
            "succeeded": 1,
        }

        source_changed = api.create(
            key="p73-source-change-key-0001",
        ).json()
        report_path = (
            fixture_dir
            / "DT5_DATA0019_report_no1"
            / "human"
            / "report.md"
        )
        original_report = report_path.read_text(encoding="utf-8")
        report_path.write_text(
            original_report + "\nSynthetic source revision.\n",
            encoding="utf-8",
        )
        changed_worker = runtime.worker_once(expect_failure=True)
        assert changed_worker["failed"] == 1
        changed_status = api.request(
            "GET",
            f"/api/exports/jobs/{source_changed['job_id']}",
        )
        assert changed_status.json()["error_code"] == "export_source_changed"
        report_path.write_text(original_report, encoding="utf-8")

        counts_before_restart = _db_counts(state_dir)
        runtime.start(enabled=True)
        assert api.request(
            "GET",
            f"/api/exports/jobs/{first_job}",
        ).json()["state"] == "succeeded"
        assert api.request(
            "GET",
            f"/api/exports/jobs/{first_job}/artifact",
        ).body == first_artifact.body
        assert _db_counts(state_dir) == counts_before_restart

        runtime.start(enabled=False)
        blocked = api.create(key="p73-rollback-new-key-0001")
        assert blocked.status == 503
        assert api.request(
            "GET",
            f"/api/exports/jobs/{first_job}",
        ).status == 200
        assert api.request(
            "GET",
            f"/api/exports/jobs/{first_job}/artifact",
        ).body == first_artifact.body
        disabled_worker = runtime.python(
            """
import json
from app.export_worker import run_once
print(json.dumps(run_once(limit=1), sort_keys=True))
""",
            enabled=False,
        )
        assert disabled_worker["enabled"] is False
        runtime.start(enabled=True)
        assert api.request(
            "GET",
            f"/api/exports/jobs/{first_job}/artifact",
        ).body == first_artifact.body

        browser = (
            {"skipped": True}
            if arguments.skip_browser
            else _browser_oracle(runtime, out_dir)
        )

        expiry = _expire_oracle(runtime, retry["job_id"])
        assert expiry["state"] == "expired"
        assert expiry["expired_count"] >= 1
        assert api.request(
            "GET",
            f"/api/exports/jobs/{retry['job_id']}/artifact",
        ).status == 410

        logs = _run(
            "docker",
            "logs",
            runtime.container,
            check=False,
        ).stdout
        assert idempotency_key not in logs
        assert "bounded report contains fixture-only content" not in logs
        assert not any(
            marker.lower() in logs.lower()
            for marker in PRIVATE_SOURCE_MARKERS
        )

        summary = {
            "contract": "S07-P7.3/AC-DL-003/AC-DL-004",
            "fixture": "synthetic-only",
            "legacy_side_effect_get": {
                "status": 405,
                "business_state_delta": 0,
            },
            "idempotency": {
                "concurrent_submissions": len(responses),
                "created_jobs": 1,
                "business_results": 1,
            },
            "get_head": {
                "inventory_probes": len(probe_results),
                "business_state_delta": 0,
                "unauthorized_long_tasks": 0,
            },
            "lifecycle": {
                "cancelled": True,
                "retry_succeeded": True,
                "timeout_recovered": True,
                "source_change_failed_closed": True,
                "artifact_expired": True,
            },
            "budgets": first_status.json()["cost"],
            "artifact": {
                "sha256": artifact_sha256,
                "verified": True,
                "attachment": True,
                "watermark_applied": True,
            },
            "restart": {
                "state_preserved": True,
                "artifact_preserved": True,
            },
            "rollback": {
                "new_create_blocked": True,
                "worker_disabled": True,
                "status_preserved": True,
                "artifact_preserved": True,
                "re_enable_preserved": True,
            },
            "browser": browser,
            "privacy": {
                "raw_idempotency_key_in_logs": 0,
                "private_source_markers_in_logs": 0,
                "report_body_in_logs": 0,
            },
            "real_time_acceptance_waits": 0,
            "soak_or_observation_gate": False,
        }
        summary_path = out_dir / "summary.json"
        trace_path = out_dir / "http-trace.json"
        summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        trace_path.write_text(
            json.dumps(trace, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        evidence_text = summary_path.read_text() + trace_path.read_text()
        assert idempotency_key not in evidence_text
        assert first_job not in evidence_text
        return summary
    finally:
        runtime.stop()
        shutil.rmtree(fixture_dir, ignore_errors=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--container-name",
        default="kmfa-p73-e2e",
    )
    parser.add_argument("--port", type=int, default=18112)
    parser.add_argument("--skip-browser", action="store_true")
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    if IMAGE_RE.fullmatch(arguments.image) is None:
        raise SystemExit("invalid image")
    if CONTAINER_RE.fullmatch(arguments.container_name) is None:
        raise SystemExit("invalid container name")
    if arguments.port < 1024 or arguments.port > 65535:
        raise SystemExit("invalid port")
    summary = run_flow(arguments)
    print(
        json.dumps(
            {
                "status": "PASS",
                "contract": summary["contract"],
                "business_results": summary["idempotency"][
                    "business_results"
                ],
                "get_head_state_delta": summary["get_head"][
                    "business_state_delta"
                ],
                "real_time_acceptance_waits": 0,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
