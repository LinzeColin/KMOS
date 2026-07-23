#!/usr/bin/env python3
"""Final-image S04/P4.4 normal/attack traffic Oracle.

All identities and files are synthetic. Recovery codes, browser/session/device
cookies, challenge tokens and workspace identifiers remain memory-only and are
scanned out of state/log/evidence surfaces before this script writes result
JSON. The owned state directory and container are never reused or deleted.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import re
import sqlite3
import subprocess
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

CONTAINER_RE = re.compile(r"^kmfa-p44-[a-z0-9-]+$")
CAPABILITY_RE = re.compile(rb"kmfa-(?:r1|a1)-[A-Za-z0-9_-]{20,128}")
BASE_PATH = "/public-api/walking-skeleton/v1"
NORMAL_ACTORS = 20
NORMAL_REQUESTS_PER_ACTOR = 5
UPLOAD_FIXTURE = (
    b"synthetic-p44-flood-fixture|" * ((256 * 1024 // 28) + 1)
)[: 256 * 1024]
SLOW_UPLOAD_BYTES = 512 * 1024
SLOW_CHUNK_BYTES = 32 * 1024


def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=check,
        text=True,
        capture_output=True,
    )


def _container_exists(name: str) -> bool:
    return (
        _run(
            "docker",
            "container",
            "inspect",
            name,
            check=False,
        ).returncode
        == 0
    )


def _wait_ready(base_url: str) -> None:
    deadline = time.monotonic() + 60
    last_error = "not attempted"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/healthz", timeout=2) as response:
                if response.status == 200:
                    return
        except Exception as error:  # noqa: BLE001 - diagnostic is local only.
            last_error = type(error).__name__
        time.sleep(0.5)
    raise AssertionError(f"container did not become ready: {last_error}")


class ContainerLifecycle:
    def __init__(
        self,
        *,
        name: str,
        image: str,
        state_dir: Path,
        port: int,
    ) -> None:
        self.name = name
        self.image = image
        self.state_dir = state_dir
        self.port = port
        self.base_url = f"http://localhost:{port}"
        self.owned = False

    def start(self) -> None:
        assert not self.owned
        assert not _container_exists(self.name)
        user_args: tuple[str, ...] = ()
        if hasattr(os, "getuid") and hasattr(os, "getgid"):
            user_args = ("--user", f"{os.getuid()}:{os.getgid()}")
        result = _run(
            "docker",
            "run",
            "-d",
            "--name",
            self.name,
            "-p",
            f"127.0.0.1:{self.port}:8000",
            "-e",
            "KMFA_WALKING_SKELETON_ENABLED=1",
            "-e",
            "KMFA_ABUSE_POLICY_MODE=enforced",
            "-e",
            "KMFA_PUBLIC_INDEXING_ENABLED=0",
            "-e",
            "KMFA_PRIVATE_OPS_REQUIRE_ACCESS=1",
            "-v",
            f"{self.state_dir}:/var/lib/kmfa/state",
            *user_args,
            self.image,
        )
        assert result.stdout.strip()
        self.owned = True
        try:
            _wait_ready(self.base_url)
        except Exception:
            raise AssertionError(self.logs()) from None

    def logs(self) -> str:
        if not self.owned:
            return ""
        result = _run("docker", "logs", self.name, check=False)
        return result.stdout + result.stderr

    def stats(self) -> dict[str, Any]:
        result = _run(
            "docker",
            "stats",
            "--no-stream",
            "--format",
            "{{json .}}",
            self.name,
        )
        payload = json.loads(result.stdout)
        return {
            key: payload.get(key)
            for key in ("CPUPerc", "MemUsage", "MemPerc", "NetIO", "BlockIO", "PIDs")
        }

    def policy_probe(self) -> dict[str, Any]:
        result = _run(
            "docker",
            "exec",
            "-e",
            "PYTHONPATH=/opt/kmfa/KMOS/KMFA/app/backend",
            self.name,
            "python3",
            "/opt/kmfa/KMOS/KMFA/app/e2e/abuse_policy_probe.py",
        )
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        assert lines
        return json.loads(lines[-1])

    def remove(self) -> None:
        if not self.owned:
            return
        _run("docker", "rm", "-f", self.name)
        self.owned = False


@dataclass
class HttpResult:
    status: int
    headers: dict[str, str]
    body: bytes
    elapsed_ms: float

    def json(self) -> dict[str, Any]:
        return json.loads(self.body)


class Actor:
    def __init__(self, base_url: str, ip: str) -> None:
        self.base_url = base_url
        self.ip = ip
        self.cookies: dict[str, str] = {}

    def cookie_header(self) -> str:
        return "; ".join(
            f"{name}={value}" for name, value in sorted(self.cookies.items())
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResult:
        request_headers = {
            "Accept": "application/json",
            "Origin": self.base_url,
            "CF-Connecting-IP": self.ip,
            **(headers or {}),
        }
        cookie = self.cookie_header()
        if cookie:
            request_headers["Cookie"] = cookie
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers=request_headers,
            method=method,
        )
        started = time.monotonic()
        try:
            response = urllib.request.urlopen(request, timeout=30)
        except urllib.error.HTTPError as error:
            response = error
        response_body = response.read()
        elapsed_ms = (time.monotonic() - started) * 1000
        for header in response.headers.get_all("Set-Cookie", []):
            parsed = SimpleCookie()
            parsed.load(header)
            for name, morsel in parsed.items():
                if morsel.value:
                    self.cookies[name] = morsel.value
                else:
                    self.cookies.pop(name, None)
        response_headers = {
            name.lower(): value for name, value in response.headers.items()
        }
        return HttpResult(
            status=int(response.status),
            headers=response_headers,
            body=response_body,
            elapsed_ms=elapsed_ms,
        )

    def json_request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any],
        *,
        headers: dict[str, str] | None = None,
    ) -> HttpResult:
        return self.request(
            method,
            path,
            body=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            headers={"Content-Type": "application/json", **(headers or {})},
        )


def _percentile(values: list[float], fraction: float) -> float:
    assert values
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return round(ordered[index], 2)


def _solve(challenge: dict[str, Any]) -> tuple[str, int]:
    assert challenge["algorithm"] == "sha256-leading-zero-bits"
    token = str(challenge["token"])
    difficulty = int(challenge["difficulty_bits"])
    for nonce in range(2**32):
        proof = f"{token}:{nonce}"
        digest = hashlib.sha256(proof.encode("ascii")).digest()
        zero_bits = 0
        for byte in digest:
            if byte == 0:
                zero_bits += 8
                continue
            zero_bits += 8 - byte.bit_length()
            break
        if zero_bits >= difficulty:
            return proof, nonce + 1
    raise AssertionError("challenge solver exhausted")


def _create_workspace(
    actor: Actor,
    name: str,
    sensitive_values: list[str],
) -> tuple[str, HttpResult]:
    response = actor.json_request(
        "POST",
        f"{BASE_PATH}/workspaces",
        {"project_name": name},
    )
    assert response.status == 201, response.body
    payload = response.json()
    workspace_id = str(payload["workspace"]["workspace_id"])
    sensitive_values.append(str(payload["recovery_code"]))
    sensitive_values.extend(actor.cookies.values())
    return workspace_id, response


def _normal_fixture(
    base_url: str,
    sensitive_values: list[str],
) -> dict[str, Any]:
    statuses: list[int] = []
    latencies: list[float] = []
    for index in range(NORMAL_ACTORS):
        actor = Actor(base_url, f"198.18.0.{index + 1}")
        root = actor.request("GET", "/")
        status = actor.request("GET", f"{BASE_PATH}/status")
        workspace_id, created = _create_workspace(
            actor,
            f"normal-synthetic-{index}",
            sensitive_values,
        )
        read = actor.request("GET", f"{BASE_PATH}/workspaces/{workspace_id}")
        saved = actor.json_request(
            "PATCH",
            f"{BASE_PATH}/workspaces/{workspace_id}",
            {"progress": index},
        )
        batch = (root, status, created, read, saved)
        statuses.extend(item.status for item in batch)
        latencies.extend(item.elapsed_ms for item in batch)
        assert [item.status for item in batch] == [200, 200, 201, 200, 200]
        assert status.headers["x-kmfa-abuse-decision"] == "public-browse-exempt"

    false_positives = sum(status in {403, 429} for status in statuses)
    request_count = len(statuses)
    assert request_count == NORMAL_ACTORS * NORMAL_REQUESTS_PER_ACTOR
    assert false_positives == 0
    assert false_positives / request_count < 0.01
    assert _percentile(latencies, 0.95) < 1500
    return {
        "actors": NORMAL_ACTORS,
        "requests": request_count,
        "false_positives": false_positives,
        "false_positive_percent": 0,
        "latency_ms": {
            "p50": _percentile(latencies, 0.50),
            "p95": _percentile(latencies, 0.95),
            "max": round(max(latencies), 2),
        },
        "status": "PASS",
    }


def _brute_and_challenge(
    base_url: str,
    sensitive_values: list[str],
) -> dict[str, Any]:
    actor = Actor(base_url, "198.51.100.81")
    actor.request("GET", f"{BASE_PATH}/status")
    invalid_code = "kmfa-r1-" + ("R" * 43)
    sensitive_values.append(invalid_code)
    attempts = [
        actor.json_request(
            "POST",
            f"{BASE_PATH}/recoveries",
            {"recovery_code": invalid_code},
        )
        for _ in range(7)
    ]
    assert [result.status for result in attempts[:6]] == [404] * 6
    challenged = attempts[6]
    assert challenged.status == 429
    assert challenged.json()["detail"] == "risk_challenge_required"
    proof, solver_iterations = _solve(challenged.json()["challenge"])
    sensitive_values.append(proof)
    passed_to_business = actor.json_request(
        "POST",
        f"{BASE_PATH}/recoveries",
        {"recovery_code": invalid_code},
        headers={"X-KMFA-Challenge-Proof": proof},
    )
    replay = actor.json_request(
        "POST",
        f"{BASE_PATH}/recoveries",
        {"recovery_code": invalid_code},
        headers={"X-KMFA-Challenge-Proof": proof},
    )
    cross_actor = Actor(base_url, "203.0.113.201").json_request(
        "POST",
        f"{BASE_PATH}/recoveries",
        {"recovery_code": invalid_code},
        headers={"X-KMFA-Challenge-Proof": proof},
    )
    assert passed_to_business.status == 404
    assert passed_to_business.headers["x-kmfa-abuse-decision"] == "challenge-passed"
    assert replay.status == 403
    assert replay.json()["detail"] == "risk_challenge_replayed"
    assert cross_actor.status == 403
    assert cross_actor.json()["detail"] == "risk_challenge_invalid"
    authorization_successes = sum(
        200 <= result.status < 300
        for result in (passed_to_business, replay, cross_actor)
    )
    assert authorization_successes == 0
    return {
        "brute_attempts": len(attempts),
        "underlying_not_found_before_challenge": 6,
        "challenge_status": challenged.status,
        "challenge_solver_iterations": solver_iterations,
        "challenge_pass_reaches_uniform_not_found": True,
        "replay_status": replay.status,
        "cross_actor_status": cross_actor.status,
        "authorization_successes": authorization_successes,
        "bypasses": 0,
        "status": "PASS",
    }


def _browser_challenge(
    base_url: str,
    sensitive_values: list[str],
) -> dict[str, Any]:
    response_statuses: list[int] = []
    console_messages: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(locale="zh-CN")
        page = context.new_page()

        def capture_response(response) -> None:
            if (
                response.request.method == "POST"
                and response.url.endswith(f"{BASE_PATH}/workspaces")
            ):
                response_statuses.append(response.status)

        page.on("response", capture_response)
        page.on("console", lambda message: console_messages.append(message.text))
        page.goto(base_url, wait_until="networkidle", timeout=30_000)
        page.locator('[data-walking-skeleton-state="ready"]').wait_for()
        challenge_started = 0.0
        challenge_elapsed_ms = 0.0
        for index in range(7):
            if index:
                page.get_by_role("button", name="创建工作区", exact=True).click()
            page.locator("#walking-project-create").fill(
                f"browser-challenge-{index}"
            )
            if index == 6:
                challenge_started = time.monotonic()
            page.get_by_role(
                "button",
                name="创建并生成恢复码",
                exact=True,
            ).click()
            page.locator('[data-workspace-ready="true"]').wait_for(
                timeout=30_000
            )
            if index == 6:
                challenge_elapsed_ms = (
                    time.monotonic() - challenge_started
                ) * 1000
            recovery_code = page.locator(
                '[data-recovery-code-value="true"]'
            ).inner_text()
            sensitive_values.append(recovery_code)
            if index < 6:
                page.get_by_role(
                    "button",
                    name="撤销并清除本页会话",
                    exact=True,
                ).click()
                page.get_by_role(
                    "button",
                    name="创建工作区",
                    exact=True,
                ).wait_for()
        cookies = context.cookies()
        sensitive_values.extend(
            str(cookie["value"]) for cookie in cookies if cookie.get("value")
        )
        assert page.locator('[data-workspace-ready="true"]').count() == 1
        assert page.locator('[data-walking-message="error"]').count() == 0
        context.close()
        browser.close()

    assert response_statuses.count(201) == 7
    assert response_statuses.count(429) == 1
    console_raw_hits = sum(
        value in message
        for message in console_messages
        for value in sensitive_values
        if value
    )
    assert console_raw_hits == 0
    return {
        "workspace_creates": 7,
        "challenge_responses": 1,
        "successful_responses": 7,
        "automatic_retry_completed": True,
        "challenge_elapsed_ms": round(challenge_elapsed_ms, 2),
        "account_prompted": False,
        "console_sensitive_hits": 0,
        "status": "PASS",
    }


def _upload_export_flood(
    base_url: str,
    sensitive_values: list[str],
) -> dict[str, Any]:
    actor = Actor(base_url, "198.51.100.91")
    actor.request("GET", f"{BASE_PATH}/status")
    workspace_id, _ = _create_workspace(
        actor,
        "upload-export-flood",
        sensitive_values,
    )
    upload_headers = {
        "Content-Type": "application/octet-stream",
        "X-KMFA-Filename": "synthetic-flood.bin",
    }
    uploads = [
        actor.request(
            "PUT",
            f"{BASE_PATH}/workspaces/{workspace_id}/artifact",
            body=UPLOAD_FIXTURE if index == 0 else b"must-not-replace",
            headers=upload_headers,
        )
        for index in range(7)
    ]
    assert uploads[0].status == 200
    assert [result.status for result in uploads[1:6]] == [409] * 5
    assert uploads[6].status == 429
    assert uploads[6].json()["detail"] == "risk_challenge_required"

    downloads = [
        actor.request(
            "POST",
            f"{BASE_PATH}/workspaces/{workspace_id}/artifact/download",
        )
        for _ in range(7)
    ]
    assert [result.status for result in downloads[:6]] == [200] * 6
    assert all(result.body == UPLOAD_FIXTURE for result in downloads[:6])
    assert downloads[6].status == 429
    assert downloads[6].json()["detail"] == "risk_challenge_required"
    root = actor.request("GET", "/")
    status = actor.request("GET", f"{BASE_PATH}/status")
    assert root.status == status.status == 200
    return {
        "upload_attempts": len(uploads),
        "objects_created": 1,
        "duplicate_business_rejections": 5,
        "upload_challenges": 1,
        "export_attempts": len(downloads),
        "exports_served_before_challenge": 6,
        "export_bytes_served": len(UPLOAD_FIXTURE) * 6,
        "export_challenges": 1,
        "public_root_after_flood": root.status,
        "public_status_after_flood": status.status,
        "status": "PASS",
    }


def _slow_upload(
    *,
    port: int,
    actor: Actor,
    workspace_id: str,
    index: int,
    barrier: threading.Barrier,
) -> tuple[int, int, str]:
    connection = http.client.HTTPConnection("localhost", port, timeout=30)
    path = f"{BASE_PATH}/workspaces/{workspace_id}/artifact"
    connection.putrequest("PUT", path)
    headers = {
        "Origin": actor.base_url,
        "CF-Connecting-IP": actor.ip,
        "Cookie": actor.cookie_header(),
        "Content-Type": "application/octet-stream",
        "Content-Length": str(SLOW_UPLOAD_BYTES),
        "X-KMFA-Filename": f"slow-{index}.bin",
    }
    for name, value in headers.items():
        connection.putheader(name, value)
    connection.endheaders()
    barrier.wait(timeout=10)
    # Give the server time to admit two leases and reject the rest before any
    # admitted handler can complete its body.
    time.sleep(0.2)
    sent = 0
    chunk = bytes([index + 1]) * SLOW_CHUNK_BYTES
    try:
        while sent < SLOW_UPLOAD_BYTES:
            connection.send(chunk)
            sent += len(chunk)
            time.sleep(0.02)
    except (BrokenPipeError, ConnectionResetError):
        pass
    response = connection.getresponse()
    status = response.status
    reason = response.getheader("X-KMFA-Abuse-Reason", "")
    response.read()
    connection.close()
    return index, status, reason


def _concurrency_flood(
    *,
    base_url: str,
    port: int,
    control_db: Path,
    sensitive_values: list[str],
) -> dict[str, Any]:
    actors: list[Actor] = []
    workspaces: list[str] = []
    for index in range(6):
        actor = Actor(base_url, f"203.0.113.{index + 10}")
        actor.request("GET", f"{BASE_PATH}/status")
        workspace_id, _ = _create_workspace(
            actor,
            f"concurrency-{index}",
            sensitive_values,
        )
        actors.append(actor)
        workspaces.append(workspace_id)

    # The preceding upload-flood scenario intentionally consumed seven slots
    # from the same 10-second global upload bucket. Start the concurrency curve
    # in a fresh policy window so a fast Linux runner cannot turn the intended
    # concurrency denials/recovery into a legitimate global-rate denial.
    window_seconds = 10
    window_now = time.time()
    next_window = ((int(window_now) // window_seconds) + 1) * window_seconds
    window_alignment_seconds = max(0.05, next_window - window_now + 0.05)
    time.sleep(window_alignment_seconds)

    barrier = threading.Barrier(len(actors) + 1)
    with ThreadPoolExecutor(max_workers=len(actors)) as pool:
        futures = [
            pool.submit(
                _slow_upload,
                port=port,
                actor=actors[index],
                workspace_id=workspaces[index],
                index=index,
                barrier=barrier,
            )
            for index in range(len(actors))
        ]
        barrier.wait(timeout=10)
        # All six attack connections are open. Two server-side upload leases
        # remain occupied while this independent actor exercises the public
        # root and a normal identity mutation.
        time.sleep(0.25)
        normal_actor = Actor(base_url, "192.0.2.240")
        root_during_attack = normal_actor.request("GET", "/")
        _, normal_create = _create_workspace(
            normal_actor,
            "normal-during-upload-attack",
            sensitive_values,
        )
        results = [future.result() for future in futures]
    assert root_during_attack.status == 200
    assert normal_create.status == 201
    assert root_during_attack.elapsed_ms < 1000
    assert normal_create.elapsed_ms < 1000
    statuses = {index: status for index, status, _ in results}
    reasons = {index: reason for index, _, reason in results}
    admitted = [index for index, status in statuses.items() if status == 200]
    blocked = [index for index, status in statuses.items() if status == 429]
    assert len(admitted) == 2, statuses
    assert len(blocked) == 4, statuses
    assert {reasons[index] for index in blocked} == {"concurrency"}, reasons

    # A successful recovery assertion requires the persistent lease invariant,
    # not merely completed client futures. Observe that invariant directly
    # instead of hiding it behind an arbitrary sleep.
    lease_release_started = time.monotonic()
    lease_release_deadline = lease_release_started + 5
    active_leases = -1
    while time.monotonic() < lease_release_deadline:
        with sqlite3.connect(control_db) as connection:
            active_leases = int(
                connection.execute(
                    "SELECT COUNT(*) FROM concurrency_leases"
                ).fetchone()[0]
            )
        if active_leases == 0:
            break
        time.sleep(0.02)
    assert active_leases == 0, {
        "active_leases": active_leases,
        "parallel_statuses": statuses,
    }
    lease_release_wait_ms = (time.monotonic() - lease_release_started) * 1000

    recovery_index = blocked[0]
    recovered = actors[recovery_index].request(
        "PUT",
        f"{BASE_PATH}/workspaces/{workspaces[recovery_index]}/artifact",
        body=b"post-concurrency-recovery",
        headers={
            "Content-Type": "application/octet-stream",
            "X-KMFA-Filename": "recovered.bin",
        },
    )
    assert recovered.status == 200, {
        "status": recovered.status,
        "body": recovered.body.decode("utf-8", errors="replace")[:500],
        "lease_release_wait_ms": lease_release_wait_ms,
    }
    root = actors[recovery_index].request("GET", "/")
    assert root.status == 200
    return {
        "parallel_uploads": len(actors),
        "concurrency_budget": 2,
        "fresh_rate_window_wait_ms": round(
            window_alignment_seconds * 1000,
            2,
        ),
        "admitted": len(admitted),
        "capacity_blocked": len(blocked),
        "capacity_block_reason": "concurrency",
        "public_root_during_attack": root_during_attack.status,
        "public_root_during_attack_latency_ms": round(
            root_during_attack.elapsed_ms,
            2,
        ),
        "normal_workspace_during_attack": normal_create.status,
        "normal_workspace_during_attack_latency_ms": round(
            normal_create.elapsed_ms,
            2,
        ),
        "active_leases_before_recovery": active_leases,
        "lease_release_wait_ms": round(lease_release_wait_ms, 2),
        "recovered_after_leases_released": recovered.status,
        "public_root_during_recovery": root.status,
        "status": "PASS",
    }


def _state_metrics(
    state_dir: Path,
    sensitive_values: list[str],
) -> dict[str, Any]:
    root = state_dir / "walking-skeleton"
    business_db = root / "walking_skeleton.sqlite3"
    abuse_db = root / "abuse-control" / "abuse_control.sqlite3"
    assert business_db.is_file() and abuse_db.is_file()
    with sqlite3.connect(business_db) as connection:
        business = {
            "workspaces": connection.execute(
                "SELECT COUNT(*) FROM workspaces"
            ).fetchone()[0],
            "active_sessions": connection.execute(
                "SELECT COUNT(*) FROM access_tokens"
            ).fetchone()[0],
            "artifacts": connection.execute(
                "SELECT COUNT(*) FROM artifacts"
            ).fetchone()[0],
            "artifact_bytes": connection.execute(
                "SELECT COALESCE(SUM(size_bytes), 0) FROM artifacts"
            ).fetchone()[0],
            "audit_events": connection.execute(
                "SELECT COUNT(*) FROM audit_events"
            ).fetchone()[0],
        }
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    with sqlite3.connect(abuse_db) as connection:
        control_counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "rate_counters",
                "concurrency_leases",
                "challenge_uses",
                "decision_metrics",
                "decision_windows",
                "capacity_alerts",
            )
        }
        decisions = [
            {
                "operation": row[0],
                "decision": row[1],
                "reason": row[2],
                "count": row[3],
            }
            for row in connection.execute(
                """
                SELECT operation, decision, reason, count
                FROM decision_metrics
                ORDER BY operation, decision, reason
                """
            )
        ]
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    assert control_counts["concurrency_leases"] == 0
    assert control_counts["rate_counters"] <= 2048
    files = [path for path in root.rglob("*") if path.is_file()]
    persisted = b"".join(path.read_bytes() for path in files)
    raw_value_hits = sum(
        value.encode("utf-8") in persisted
        for value in sensitive_values
        if value
    )
    capability_hits = len(CAPABILITY_RE.findall(persisted))
    assert raw_value_hits == 0
    assert capability_hits == 0
    return {
        "business": business,
        "control_rows": control_counts,
        "decision_metrics": decisions,
        "state_files": len(files),
        "state_bytes": sum(path.stat().st_size for path in files),
        "raw_sensitive_value_hits": raw_value_hits,
        "capability_pattern_hits": capability_hits,
        "resource_growth_bounded": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--container-name", default="kmfa-p44-e2e")
    parser.add_argument("--port", type=int, default=18105)
    args = parser.parse_args()
    assert CONTAINER_RE.fullmatch(args.container_name)
    args.state_dir = args.state_dir.resolve()
    args.out_dir = args.out_dir.resolve()
    args.state_dir.mkdir(parents=True, exist_ok=True)
    assert not any(args.state_dir.iterdir())
    args.out_dir.mkdir(parents=True, exist_ok=True)
    assert not any(args.out_dir.iterdir())
    assert not _container_exists(args.container_name)
    image_id = _run(
        "docker",
        "image",
        "inspect",
        "--format",
        "{{.Id}}",
        args.image,
    ).stdout.strip()
    assert image_id.startswith("sha256:")

    lifecycle = ContainerLifecycle(
        name=args.container_name,
        image=args.image,
        state_dir=args.state_dir,
        port=args.port,
    )
    sensitive_values: list[str] = []
    log_text = ""
    lifecycle.start()
    try:
        normal = _normal_fixture(lifecycle.base_url, sensitive_values)
        brute = _brute_and_challenge(lifecycle.base_url, sensitive_values)
        browser_challenge = _browser_challenge(
            lifecycle.base_url,
            sensitive_values,
        )
        floods = _upload_export_flood(lifecycle.base_url, sensitive_values)
        concurrency = _concurrency_flood(
            base_url=lifecycle.base_url,
            port=args.port,
            control_db=(
                args.state_dir
                / "walking-skeleton"
                / "abuse-control"
                / "abuse_control.sqlite3"
            ),
            sensitive_values=sensitive_values,
        )
        distributed = lifecycle.policy_probe()
        runtime_stats = lifecycle.stats()
        post_attack = Actor(lifecycle.base_url, "192.0.2.250")
        root_started = time.monotonic()
        root = post_attack.request("GET", "/")
        root_elapsed = (time.monotonic() - root_started) * 1000
        status = post_attack.request("GET", f"{BASE_PATH}/status")
        assert root.status == status.status == 200
        assert root_elapsed < 1000
        log_text = lifecycle.logs()
    finally:
        lifecycle.remove()

    log_capability_hits = len(CAPABILITY_RE.findall(log_text.encode("utf-8")))
    raw_log_hits = sum(
        value in log_text for value in sensitive_values if value
    )
    assert log_capability_hits == 0
    assert raw_log_hits == 0
    capacity_alert_lines = sum(
        "KMFA_ABUSE_CAPACITY_ALERT" in line for line in log_text.splitlines()
    )
    state = _state_metrics(args.state_dir, sensitive_values)
    # One flood object, two concurrent admissions and one post-release recovery.
    assert state["business"]["artifacts"] == 4
    assert state["business"]["artifact_bytes"] == (
        len(UPLOAD_FIXTURE) + (2 * SLOW_UPLOAD_BYTES) + len(b"post-concurrency-recovery")
    )
    assert brute["bypasses"] == 0
    assert distributed["blocked_after_bound"] == 1
    assert distributed["recovered_next_window"] is True

    result = {
        "contract": "S04/P4.4 AC-WS-004 TEST-WS-004",
        "image_id": image_id,
        "synthetic_only": True,
        "policy_version": "p44-v1",
        "normal_fixture": normal,
        "attack_curves": {
            "brute_recovery_and_challenge": brute,
            "browser_automatic_challenge": browser_challenge,
            "upload_export_flood": floods,
            "concurrency_flood": concurrency,
            "distributed_low_speed": distributed,
        },
        "post_attack_public_browse": {
            "root_status": root.status,
            "status_endpoint": status.status,
            "root_latency_ms": round(root_elapsed, 2),
            "available": True,
        },
        "resource_metrics": {
            "runtime": runtime_stats,
            "state": state,
            "capacity_alert_log_lines": capacity_alert_lines,
        },
        "security": {
            "account_required": False,
            "attack_bypasses": 0,
            "raw_sensitive_state_hits": 0,
            "raw_sensitive_log_hits": raw_log_hits,
            "capability_state_hits": 0,
            "capability_log_hits": log_capability_hits,
            "challenge_tokens_persisted": False,
        },
        "status": "PASS",
    }
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    assert not CAPABILITY_RE.search(serialized.encode("utf-8"))
    (args.out_dir / "result.json").write_text(serialized, encoding="utf-8")
    print(
        json.dumps(
            {
                "contract": result["contract"],
                "normal_requests": normal["requests"],
                "false_positives": normal["false_positives"],
                "attack_bypasses": 0,
                "concurrency_blocked": concurrency["capacity_blocked"],
                "distributed_bound": distributed["global_sustained_limit"],
                "post_attack_root_status": root.status,
                "status": "PASS",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
