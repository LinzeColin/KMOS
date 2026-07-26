#!/usr/bin/env python3
"""S06/P6.2 exact-image quarantine/scanner acceptance Oracle.

Only synthetic bytes are used. Recovery/session capabilities stay in memory
and are never written to the evidence directory.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import secrets
import subprocess
import time
import urllib.error
import urllib.request
import zipfile
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

API_PREFIX = "/public-api/walking-skeleton/v1"
PREFIX_RE = re.compile(r"^kmfa-p62-[a-z0-9-]{1,32}$")
ACCESS_RE = re.compile(r"^kmfa-a1-[A-Za-z0-9_-]{43}$")
RECOVERY_RE = re.compile(r"^kmfa-r1-[A-Za-z0-9_-]{43}$")
SECRET_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")
SCANNER_BACKLOG_CASES = 8


@dataclass(frozen=True)
class HttpResult:
    status: int
    headers: dict[str, str]
    set_cookies: tuple[str, ...]
    body: bytes

    def json(self) -> dict[str, Any]:
        return json.loads(self.body)


def _run(
    *arguments: str,
    check: bool = True,
    sensitive_values: Sequence[str] = (),
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(arguments),
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        detail = result.stdout + result.stderr
        for value in sensitive_values:
            detail = detail.replace(value, "[REDACTED]")
        raise AssertionError(f"owned Docker command failed: {detail[-4000:]}")
    return result


def _exists(kind: str, name: str) -> bool:
    command = {
        "container": ("docker", "inspect", name),
        "network": ("docker", "network", "inspect", name),
    }[kind]
    return _run(*command, check=False).returncode == 0


def _wait_http(url: str, timeout: float = 90) -> None:
    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError) as exc:
            last_error = str(exc)
        time.sleep(0.25)
    raise AssertionError(f"HTTP readiness timeout: {last_error}")


def _zip(entries: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(
        output,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for name, payload in entries.items():
            archive.writestr(name, payload)
    return output.getvalue()


def _eicar() -> bytes:
    return (
        b"X5O!P%@AP[4"
        + bytes((92,))
        + b"PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    )


class Api:
    def __init__(self, base_url: str, capabilities: list[str]) -> None:
        self.base_url = base_url
        self.capabilities = capabilities
        self.sequence = 0

    def _actor(self) -> dict[str, str]:
        self.sequence += 1
        digest = hashlib.sha256(
            f"p62-actor-{self.sequence}".encode()
        ).hexdigest()
        return {
            "CF-Connecting-IP": f"198.51.100.{10 + self.sequence % 200}",
            "Cookie": f"__Host-kmfa_device=kmfa-d1-{digest[:22]}",
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 30,
    ) -> HttpResult:
        request = urllib.request.Request(
            f"{self.base_url}{API_PREFIX}{path}",
            data=body,
            method=method,
            headers={
                "Accept": "application/json",
                "Origin": self.base_url,
                **(headers or {}),
            },
        )
        try:
            response = urllib.request.urlopen(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            return HttpResult(
                status=response.status,
                headers={
                    key.lower(): value
                    for key, value in response.headers.items()
                },
                set_cookies=tuple(
                    response.headers.get_all("Set-Cookie") or ()
                ),
                body=response.read(),
            )

    def create(self, label: str) -> tuple[str, str, dict[str, str]]:
        actor = self._actor()
        result = self.request(
            "POST",
            "/workspaces",
            body=json.dumps({"project_name": label}).encode(),
            headers={**actor, "Content-Type": "application/json"},
        )
        assert result.status == 201, result.body
        payload = result.json()
        workspace_id = str(payload["workspace"]["workspace_id"])
        recovery_code = str(payload["recovery_code"])
        assert RECOVERY_RE.fullmatch(recovery_code)
        match = re.search(
            r"__Secure-kmfa_session=([^;\s]+)",
            "\n".join(result.set_cookies),
        )
        assert match and ACCESS_RE.fullmatch(match.group(1))
        token = match.group(1)
        self.capabilities.extend((recovery_code, token))
        return workspace_id, token, actor

    @staticmethod
    def auth(token: str, actor: dict[str, str]) -> dict[str, str]:
        return {
            **actor,
            "Authorization": f"Bearer {token}",
        }

    def upload(
        self,
        workspace_id: str,
        token: str,
        actor: dict[str, str],
        *,
        name: str,
        media_type: str,
        payload: bytes,
    ) -> HttpResult:
        return self.request(
            "PUT",
            f"/workspaces/{workspace_id}/artifact",
            body=payload,
            headers={
                **self.auth(token, actor),
                "Content-Type": media_type,
                "X-KMFA-Filename": quote(name, safe=""),
                "Idempotency-Key": (
                    f"p62-final-image-upload-{self.sequence:06d}"
                ),
            },
        )

    def workspace(
        self,
        workspace_id: str,
        token: str,
        actor: dict[str, str],
    ) -> HttpResult:
        return self.request(
            "GET",
            f"/workspaces/{workspace_id}",
            headers=self.auth(token, actor),
        )

    def download(
        self,
        workspace_id: str,
        token: str,
        actor: dict[str, str],
    ) -> HttpResult:
        return self.request(
            "POST",
            f"/workspaces/{workspace_id}/artifact/download",
            headers=self.auth(token, actor),
        )


class Resources:
    def __init__(
        self,
        *,
        prefix: str,
        image: str,
        state_dir: Path,
        port: int,
        shared_secret: str,
    ) -> None:
        self.prefix = prefix
        self.image = image
        self.state_dir = state_dir
        self.port = port
        self.shared_secret = shared_secret
        self.network = f"{prefix}-net"
        self.app_network = f"{prefix}-app-net"
        self.scanner = f"{prefix}-scanner"
        self.app = f"{prefix}-app"
        self.worker_sequence = 0
        self.base_url = f"http://localhost:{port}"
        self.owned_network = False
        self.owned_app_network = False
        self.owned_scanner = False
        self.owned_app = False
        self.worker_logs: list[str] = []

    @property
    def user_args(self) -> tuple[str, ...]:
        if hasattr(os, "getuid") and hasattr(os, "getgid"):
            return ("--user", f"{os.getuid()}:{os.getgid()}")
        return ()

    def create_network(self) -> None:
        assert not _exists("network", self.network)
        assert not _exists("network", self.app_network)
        _run("docker", "network", "create", "--internal", self.network)
        self.owned_network = True
        _run("docker", "network", "create", self.app_network)
        self.owned_app_network = True

    def start_scanner(self) -> None:
        assert not _exists("container", self.scanner)
        result = _run(
            "docker",
            "run",
            "-d",
            "--name",
            self.scanner,
            "--network",
            self.network,
            "--network-alias",
            "file-security-scanner",
            "--user",
            "65532:65532",
            "--read-only",
            "--tmpfs",
            (
                "/tmp:rw,noexec,nosuid,nodev,size=80m,"
                "mode=0700,uid=65532,gid=65532"
            ),
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "64",
            "--memory",
            "256m",
            "-e",
            f"KMFA_FILE_SCANNER_SHARED_SECRET={self.shared_secret}",
            self.image,
            "uvicorn",
            "app.file_security_scanner_service:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8090",
            "--no-access-log",
            "--workers",
            "1",
            sensitive_values=(self.shared_secret,),
        )
        assert result.stdout.strip()
        self.owned_scanner = True
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            ready = _run(
                "docker",
                "exec",
                self.scanner,
                "python3",
                "-c",
                (
                    "import urllib.request;"
                    "urllib.request.urlopen("
                    "'http://127.0.0.1:8090/healthz',timeout=2)"
                ),
                check=False,
            )
            if ready.returncode == 0:
                return
            time.sleep(0.25)
        raise AssertionError("scanner readiness timeout")

    def remove_scanner(self) -> None:
        if self.owned_scanner:
            _run("docker", "rm", "-f", self.scanner)
            self.owned_scanner = False

    def start_app(
        self,
        *,
        security_enabled: bool,
        derivation_enabled: bool = False,
    ) -> None:
        assert not _exists("container", self.app)
        result = _run(
            "docker",
            "run",
            "-d",
            "--name",
            self.app,
            "--network",
            self.app_network,
            "-p",
            f"127.0.0.1:{self.port}:8000",
            "-e",
            "KMFA_WALKING_SKELETON_ENABLED=1",
            "-e",
            "KMFA_PUBLIC_INDEXING_ENABLED=0",
            "-e",
            "KMFA_ABUSE_POLICY_MODE=enforced",
            "-e",
            f"KMFA_FILE_SECURITY_ENABLED={1 if security_enabled else 0}",
            "-e",
            (
                "KMFA_ARTIFACT_DERIVATION_ENABLED="
                f"{1 if derivation_enabled else 0}"
            ),
            "-e",
            (
                "KMFA_FILE_SCANNER_URL="
                "http://file-security-scanner:8090/scan"
            ),
            "-e",
            f"KMFA_FILE_SCANNER_SHARED_SECRET={self.shared_secret}",
            "-e",
            "KMFA_FILE_SCANNER_TIMEOUT_SECONDS=1",
            "-e",
            "KMFA_FILE_SCAN_LEASE_SECONDS=5",
            "-e",
            "KMFA_FILE_SCAN_RETRY_DELAY_SECONDS=0",
            "-e",
            "KMFA_FILE_SCAN_MAX_ATTEMPTS=3",
            "-v",
            f"{self.state_dir}:/var/lib/kmfa/state",
            *self.user_args,
            self.image,
            sensitive_values=(self.shared_secret,),
        )
        assert result.stdout.strip()
        self.owned_app = True
        _run(
            "docker",
            "network",
            "connect",
            self.network,
            self.app,
        )
        try:
            _wait_http(f"{self.base_url}/healthz")
            status = urllib.request.urlopen(
                f"{self.base_url}{API_PREFIX}/status",
                timeout=5,
            )
            with status:
                assert status.status == 200
        except (AssertionError, OSError, urllib.error.URLError):
            logs = self.logs()
            raise AssertionError(f"app readiness failed: {logs[-4000:]}")

    def remove_app(self) -> None:
        if self.owned_app:
            _run("docker", "rm", "-f", self.app)
            self.owned_app = False

    def restart_app(self) -> None:
        assert self.owned_app
        _run("docker", "restart", self.app)
        _wait_http(f"{self.base_url}/healthz")

    def run_worker(self, *, derivation_enabled: bool = False) -> str:
        self.worker_sequence += 1
        name = f"{self.prefix}-worker-{self.worker_sequence}"
        assert not _exists("container", name)
        result = _run(
            "docker",
            "run",
            "--rm",
            "--name",
            name,
            "--network",
            self.network,
            "-e",
            "KMFA_FILE_SECURITY_ENABLED=1",
            "-e",
            (
                "KMFA_ARTIFACT_DERIVATION_ENABLED="
                f"{1 if derivation_enabled else 0}"
            ),
            "-e",
            (
                "KMFA_FILE_SCANNER_URL="
                "http://file-security-scanner:8090/scan"
            ),
            "-e",
            f"KMFA_FILE_SCANNER_SHARED_SECRET={self.shared_secret}",
            "-e",
            "KMFA_FILE_SCANNER_TIMEOUT_SECONDS=1",
            "-e",
            "KMFA_FILE_SCAN_LEASE_SECONDS=5",
            "-e",
            "KMFA_FILE_SCAN_RETRY_DELAY_SECONDS=0",
            "-e",
            "KMFA_FILE_SCAN_MAX_ATTEMPTS=3",
            "-v",
            f"{self.state_dir}:/var/lib/kmfa/state",
            *self.user_args,
            self.image,
            "python3",
            "-m",
            "app.file_security_worker",
            "--once",
            sensitive_values=(self.shared_secret,),
        )
        self.worker_logs.append(result.stdout + result.stderr)
        return result.stdout

    def scanner_isolation(self) -> dict[str, Any]:
        inspected = json.loads(
            _run("docker", "inspect", self.scanner).stdout
        )[0]
        environment = inspected["Config"].get("Env") or []
        kmfa_names = {
            entry.split("=", 1)[0]
            for entry in environment
            if entry.startswith("KMFA_")
        }
        networks = set(
            (inspected["NetworkSettings"].get("Networks") or {}).keys()
        )
        host = inspected["HostConfig"]
        assert kmfa_names == {"KMFA_FILE_SCANNER_SHARED_SECRET"}
        assert not any(
            token in name
            for name in kmfa_names
            for token in (
                "DATABASE",
                "S3",
                "OBJECT",
                "LIFECYCLE",
                "STATE_DIR",
            )
        )
        assert inspected["Config"]["User"] == "65532:65532"
        assert host["ReadonlyRootfs"] is True
        assert set(host.get("CapDrop") or ()) == {"ALL"}
        assert any(
            option.startswith("no-new-privileges")
            for option in (host.get("SecurityOpt") or ())
        )
        assert not inspected.get("Mounts")
        assert networks == {self.network}
        assert not (host.get("PortBindings") or {})
        network = json.loads(
            _run("docker", "network", "inspect", self.network).stdout
        )[0]
        assert network["Internal"] is True
        return {
            "non_root": True,
            "read_only_root": True,
            "capabilities_dropped": True,
            "no_new_privileges": True,
            "database_environment": False,
            "object_environment": False,
            "state_mounts": 0,
            "host_ports": 0,
            "private_network_only": True,
            "memory_limit_bytes": int(host["Memory"]),
            "pids_limit": int(host["PidsLimit"]),
        }

    def database_summary(self) -> dict[str, Any]:
        command = (
            "import json,sqlite3;"
            "c=sqlite3.connect('/var/lib/kmfa/state/walking-skeleton/"
            "walking_skeleton.sqlite3');"
            "print(json.dumps({"
            "'assessments':dict(c.execute("
            "\"SELECT state,COUNT(*) FROM artifact_security_assessments "
            "GROUP BY state\").fetchall()),"
            "'events':c.execute("
            "\"SELECT COUNT(*) FROM artifact_security_events\").fetchone()[0],"
            "'isolated':c.execute("
            "\"SELECT COUNT(*) FROM object_quarantine "
            "WHERE state='isolated'\").fetchone()[0]"
            "},sort_keys=True));c.close()"
        )
        return json.loads(
            _run(
                "docker",
                "exec",
                self.app,
                "python3",
                "-c",
                command,
            ).stdout
        )

    def logs(self) -> str:
        chunks = []
        for name, owned in (
            (self.app, self.owned_app),
            (self.scanner, self.owned_scanner),
        ):
            if owned:
                result = _run("docker", "logs", name, check=False)
                chunks.append(result.stdout + result.stderr)
        chunks.extend(self.worker_logs)
        return "\n".join(chunks)

    def cleanup(self) -> None:
        self.remove_app()
        self.remove_scanner()
        for index in range(1, self.worker_sequence + 1):
            name = f"{self.prefix}-worker-{index}"
            if _exists("container", name):
                _run("docker", "rm", "-f", name)
        if self.owned_network:
            _run("docker", "network", "rm", self.network)
            self.owned_network = False
        if self.owned_app_network:
            _run("docker", "network", "rm", self.app_network)
            self.owned_app_network = False


def _run_case(
    api: Api,
    *,
    label: str,
    name: str,
    media_type: str,
    payload: bytes,
    expected_state: str,
    expected_reason: str | None = None,
    verify_download: bool = True,
) -> tuple[str, str, dict[str, str], str]:
    workspace_id, token, actor = api.create(label)
    uploaded = api.upload(
        workspace_id,
        token,
        actor,
        name=name,
        media_type=media_type,
        payload=payload,
    )
    assert uploaded.status == 200, uploaded.body
    artifact = uploaded.json()["artifact"]
    security = artifact["security"]
    assert security["state"] == expected_state, security
    if expected_reason is not None:
        assert security["reason_code"] == expected_reason
    assert security["preview_allowed"] is False
    assert security["processing_allowed"] is False
    if expected_state == "rejected":
        assert artifact["download_allowed"] is False
        if verify_download:
            downloaded = api.download(workspace_id, token, actor)
            assert downloaded.status == 409
            assert (
                downloaded.json()["detail"]
                == "artifact_security_rejected"
            )
    else:
        assert artifact["download_allowed"] is True
        if verify_download:
            downloaded = api.download(workspace_id, token, actor)
            assert downloaded.status == 200, downloaded.body
            assert (
                hashlib.sha256(downloaded.body).hexdigest()
                == hashlib.sha256(payload).hexdigest()
            )
            assert (
                downloaded.headers["x-kmfa-artifact-security"]
                == expected_state
            )
    return (
        workspace_id,
        token,
        actor,
        hashlib.sha256(payload).hexdigest(),
    )


def _scanner_backlog_oracle(
    api: Api,
    resources: Resources,
) -> dict[str, Any]:
    resources.remove_scanner()
    records: list[tuple[str, str, dict[str, str], str]] = []
    for index in range(SCANNER_BACKLOG_CASES):
        payload = f"P6.4 scanner backlog fixture {index}\n".encode()
        workspace_id, token, actor = api.create(
            f"P6.4 scanner backlog {index}"
        )
        uploaded = api.upload(
            workspace_id,
            token,
            actor,
            name=f"backlog-{index}.txt",
            media_type="text/plain",
            payload=payload,
        )
        assert uploaded.status == 200, uploaded.body
        security = uploaded.json()["artifact"]["security"]
        assert security["state"] == "scanner_error"
        assert security["preview_allowed"] is False
        assert security["processing_allowed"] is False
        assert uploaded.json()["artifact"]["download_allowed"] is True
        records.append(
            (
                workspace_id,
                token,
                actor,
                hashlib.sha256(payload).hexdigest(),
            )
        )

    queued = resources.database_summary()["assessments"]
    assert queued.get("scanner_error") == SCANNER_BACKLOG_CASES, queued
    resources.start_scanner()
    for _ in range(SCANNER_BACKLOG_CASES):
        output = resources.run_worker()
        payloads = [
            json.loads(line)
            for line in output.splitlines()
            if line.strip().startswith("{")
        ]
        assert len(payloads) == 1
        assert payloads[0]["kind"] == "security_scan"
        assert payloads[0]["state"] == "clean"

    drained = resources.database_summary()["assessments"]
    assert drained.get("scanner_error", 0) == 0, drained
    for workspace_id, token, actor, _ in records:
        refreshed = api.workspace(workspace_id, token, actor)
        assert refreshed.status == 200
        security = refreshed.json()["artifact"]["security"]
        assert security["state"] == "clean"
        assert security["preview_allowed"] is False
    return {
        "queued": SCANNER_BACKLOG_CASES,
        "initial_state": "scanner_error",
        "queued_attachment_only": SCANNER_BACKLOG_CASES,
        "attachment_download_hash_checks": 0,
        "preview_or_processing_exposures": 0,
        "workers": SCANNER_BACKLOG_CASES,
        "drained": SCANNER_BACKLOG_CASES,
        "remaining_retryable": 0,
        "real_time_window_wait_used": False,
        "wall_clock_gate_used": False,
        "thresholds": {
            "remaining_retryable_max": 0,
            "preview_or_processing_exposures_max": 0,
        },
        "status": "PASS",
    }


def _browser_oracle(base_url: str) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(base_url, wait_until="networkidle")
        page.locator(
            "[data-walking-skeleton-state='ready']"
        ).wait_for(timeout=15_000)
        page.locator("#walking-project-create").fill(
            "P6.2 browser synthetic"
        )
        page.locator("[data-walking-create] button[type=submit]").click()
        page.locator("[data-workspace-ready='true']").wait_for(
            timeout=15_000
        )
        page.locator("#walking-file").set_input_files(
            {
                "name": "browser-legal.txt",
                "mimeType": "text/plain",
                "buffer": b"P6.2 browser legal fixture\n",
            }
        )
        page.locator(
            "[data-walking-upload] button[type=submit]"
        ).click()
        artifact = page.locator(
            "[data-walking-artifact][data-security-state='clean']"
        )
        artifact.wait_for(timeout=15_000)
        download = artifact.locator("[data-walking-download='true']")
        assert download.is_enabled()
        assert "有界检查通过" in artifact.inner_text()
        assert page.locator("[data-walking-message='error']").count() == 0
        browser.close()
    return {
        "root_workspace_ready": True,
        "upload_control_used": True,
        "security_state_visible": "clean",
        "download_enabled": True,
        "preview_control_present": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--prefix", default="kmfa-p62-e2e")
    parser.add_argument("--port", type=int, default=18107)
    parser.add_argument("--skip-browser", action="store_true")
    arguments = parser.parse_args()

    assert PREFIX_RE.fullmatch(arguments.prefix)
    arguments.state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    assert not any(arguments.state_dir.iterdir()), (
        "state-dir must be initially empty"
    )
    arguments.out_dir.mkdir(parents=True, exist_ok=True)
    assert not any(arguments.out_dir.iterdir()), (
        "out-dir must be initially empty"
    )
    image_id = _run(
        "docker",
        "image",
        "inspect",
        "--format",
        "{{.Id}}",
        arguments.image,
    ).stdout.strip()
    assert image_id.startswith("sha256:")

    shared_secret = secrets.token_urlsafe(32)
    assert SECRET_RE.fullmatch(shared_secret)
    resources = Resources(
        prefix=arguments.prefix,
        image=arguments.image,
        state_dir=arguments.state_dir.resolve(),
        port=arguments.port,
        shared_secret=shared_secret,
    )
    capabilities: list[str] = []
    state_counts: Counter[str] = Counter()
    preserved: list[tuple[str, str, dict[str, str], str]] = []
    try:
        resources.create_network()
        resources.start_scanner()
        isolation = resources.scanner_isolation()
        resources.start_app(security_enabled=True)
        api = Api(resources.base_url, capabilities)
        contract = api.request("GET", "/status")
        assert contract.status == 200
        security_contract = contract.json()["file_security"]
        assert security_contract["enabled"] is True
        assert security_contract["timeout_is_clean"] is False
        assert security_contract["preview_allowed"] is False

        direct_traversal_workspace, traversal_token, traversal_actor = (
            api.create("P6.2 direct traversal")
        )
        direct_traversal = api.upload(
            direct_traversal_workspace,
            traversal_token,
            traversal_actor,
            name="../outside.txt",
            media_type="text/plain",
            payload=b"must not be accepted",
        )
        assert direct_traversal.status == 422
        assert direct_traversal.json()["detail"] == "invalid_filename"

        attack_cases = (
            (
                "EICAR",
                "canary.txt",
                "text/plain",
                _eicar(),
                "security_malware_eicar",
            ),
            (
                "archive traversal",
                "traversal.zip",
                "application/zip",
                _zip({"../outside.txt": b"escape"}),
                "security_archive_path_traversal",
            ),
            (
                "archive bomb",
                "bomb.zip",
                "application/zip",
                _zip({"large.txt": b"A" * (2 * 1024 * 1024)}),
                "security_archive_bomb",
            ),
            (
                "malformed media",
                "broken.png",
                "image/png",
                b"\x89PNG\r\n\x1a\nbroken",
                "security_media_malformed",
            ),
        )
        for label, name, media_type, payload, reason in attack_cases:
            record = _run_case(
                api,
                label=f"P6.2 {label}",
                name=name,
                media_type=media_type,
                payload=payload,
                expected_state="rejected",
                expected_reason=reason,
            )
            state_counts["rejected"] += 1
            preserved.append(record)

        attachment_cases = (
            (
                "MIME spoof",
                "photo.png",
                "image/png",
                b"MZ" + (b"\x00" * 64),
            ),
            (
                "double extension",
                "invoice.exe.txt",
                "text/plain",
                b"misleading extension fixture",
            ),
            (
                "macro",
                "macro.docx",
                (
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                ),
                _zip(
                    {
                        "[Content_Types].xml": b"<Types/>",
                        "word/vbaProject.bin": b"macro",
                    }
                ),
            ),
            (
                "unknown",
                "unknown.bin",
                "application/octet-stream",
                b"\x00\x01\x02\x03",
            ),
        )
        for label, name, media_type, payload in attachment_cases:
            _run_case(
                api,
                label=f"P6.2 {label}",
                name=name,
                media_type=media_type,
                payload=payload,
                expected_state="attachment_only",
            )
            state_counts["attachment_only"] += 1

        for index in range(12):
            record = _run_case(
                api,
                label=f"P6.2 legal {index}",
                name=f"legal-{index}.txt",
                media_type="text/plain",
                payload=f"legal final-image fixture {index}\n".encode(),
                expected_state="clean",
                expected_reason="security_scan_clean",
                verify_download=index == 0,
            )
            state_counts["clean"] += 1
            if index == 0:
                preserved.append(record)

        resources.remove_scanner()
        unavailable_payload = b"P6.2 unavailable scanner attachment\n"
        unavailable_workspace, unavailable_token, unavailable_actor = (
            api.create("P6.2 scanner unavailable")
        )
        unavailable = api.upload(
            unavailable_workspace,
            unavailable_token,
            unavailable_actor,
            name="unavailable.txt",
            media_type="text/plain",
            payload=unavailable_payload,
        )
        assert unavailable.status == 200
        assert (
            unavailable.json()["artifact"]["security"]["state"]
            == "scanner_error"
        )
        assert api.download(
            unavailable_workspace,
            unavailable_token,
            unavailable_actor,
        ).body == unavailable_payload
        state_counts["scanner_error"] += 1
        resources.start_scanner()
        resources.run_worker()
        assert (
            api.workspace(
                unavailable_workspace,
                unavailable_token,
                unavailable_actor,
            ).json()["artifact"]["security"]["state"]
            == "clean"
        )
        backlog = _scanner_backlog_oracle(api, resources)
        state_counts["scanner_error"] += SCANNER_BACKLOG_CASES

        browser = (
            {"skipped": True}
            if arguments.skip_browser
            else _browser_oracle(resources.base_url)
        )

        resources.restart_app()
        for workspace_id, token, actor, expected_hash in (
            preserved[0],
            preserved[-1],
        ):
            refreshed = api.workspace(workspace_id, token, actor)
            assert refreshed.status == 200
            state = refreshed.json()["artifact"]["security"]["state"]
            downloaded = api.download(workspace_id, token, actor)
            if state == "rejected":
                assert downloaded.status == 409
            else:
                assert hashlib.sha256(downloaded.body).hexdigest() == expected_hash

        resources.remove_app()
        resources.start_app(security_enabled=False)
        rollback_api = Api(resources.base_url, capabilities)
        rollback_contract = rollback_api.request("GET", "/status").json()
        assert rollback_contract["file_security"]["enabled"] is False
        rejected_record = preserved[0]
        assert (
            rollback_api.download(
                rejected_record[0],
                rejected_record[1],
                rejected_record[2],
            ).status
            == 409
        )
        safe_record = preserved[-1]
        safe_download = rollback_api.download(
            safe_record[0],
            safe_record[1],
            safe_record[2],
        )
        assert safe_download.status == 200
        assert hashlib.sha256(safe_download.body).hexdigest() == safe_record[3]
        rollback_workspace, rollback_token, rollback_actor = (
            rollback_api.create("P6.2 flag rollback")
        )
        rollback_upload = rollback_api.upload(
            rollback_workspace,
            rollback_token,
            rollback_actor,
            name="rollback.bin",
            media_type="application/octet-stream",
            payload=b"rollback attachment",
        )
        assert rollback_upload.status == 200
        assert (
            rollback_upload.json()["artifact"]["security"]["state"]
            == "unscanned_attachment_only"
        )

        database = resources.database_summary()
        combined_logs = resources.logs()
        assert shared_secret not in combined_logs
        assert not any(value in combined_logs for value in capabilities)
        assert not ACCESS_RE.search(combined_logs)
        assert not RECOVERY_RE.search(combined_logs)

        summary = {
            "status": "PASS",
            "image_id": image_id,
            "malicious_or_malformed_escape_count": 0,
            "direct_traversal_rejected": True,
            "attack_rejected": len(attack_cases),
            "attachment_only_risk_cases": len(attachment_cases),
            "legal_final_image_fixtures": 12,
            "legal_false_rejections": 0,
            "unavailable_was_clean": False,
            "unavailable_retry_converged": True,
            "scanner_backlog": backlog,
            "restart_preserved_state": True,
            "rollback_preserved_rejected_block": True,
            "rollback_standard_upload": True,
            "preview_success_count": 0,
            "scanner_isolation": isolation,
            "browser": browser,
            "database": database,
            "observed_initial_states": dict(sorted(state_counts.items())),
            "secret_log_matches": 0,
        }
        (arguments.out_dir / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        (arguments.out_dir / "quarantine-state.json").write_text(
            json.dumps(
                {
                    "assessment_state_counts": database["assessments"],
                    "append_only_event_count": database["events"],
                    "isolated_object_count": database["isolated"],
                    "contains_filename_or_object_key": False,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        (arguments.out_dir / "report.md").write_text(
            "# S06/P6.2 exact-image file security Oracle\n\n"
            f"- image: `{image_id}`\n"
            "- result: **PASS**\n"
            "- malicious/malformed clean or preview escape: `0`\n"
            "- final-image legal false rejection: `0/12` "
            "(100-fixture policy gate runs in backend tests)\n"
            "- scanner: non-root, read-only, no DB/object env, no state mount, "
            "private network only\n"
            "- unavailable scanner: durable non-clean; attachment-only; retry "
            "converged after scanner recovery\n"
            "- timeout state/retry is covered by the focused fake-client "
            "backend test, not by a real-time E2E delay\n"
            "- scanner backlog: `8/8` retryable assessments drained by "
            "synchronous fault recovery; no real-time window wait or "
            "wall-clock gate; preview/processing exposures `0`\n"
            "- rollback: persisted rejected remained blocked; standard upload "
            "and preserved safe download remained available\n"
            "- raw capabilities, shared secret, filenames and object keys are "
            "not written to this evidence directory\n",
            encoding="utf-8",
        )
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 0
    finally:
        resources.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
