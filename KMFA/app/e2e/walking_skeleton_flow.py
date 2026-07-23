#!/usr/bin/env python3
"""S03/P3.4 plus S04/P4.2-P4.3 final-image browser oracle.

The script owns one explicitly test-prefixed container and an initially empty
state directory. It never deletes the state directory. Evidence contains only
synthetic fixture metadata and hashes; recovery/access capabilities are kept in
memory and explicitly scanned out of URLs, Referers, browser errors, cache
keys, state files, screenshots and container logs. The persisted E2E trace is
deliberately structured and secret-redacted: a native browser trace would
retain capability-bearing DOM and POST bodies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

RECOVERY_RE = re.compile(r"^kmfa-r1-[A-Za-z0-9_-]{43}$")
ACCESS_RE = re.compile(r"^kmfa-a1-[A-Za-z0-9_-]{43}$")
CONTAINER_RE = re.compile(r"^kmfa-p34-[a-z0-9-]+$")
API_PREFIX = "/public-api/walking-skeleton/v1"
SESSION_COOKIE_NAME = "__Secure-kmfa_session"
RECOVERY_FILE_MEDIA_TYPE = "application/vnd.kmfa.recovery+json"
RECOVERY_FILE_KEYS = {"format", "version", "workspace_id", "workspace_secret"}
FIXTURE_NAME = "walking-skeleton.canary.double.exe.unknown"
PROJECT_CREATED = "P3.4 合成 canary 项目"
PROJECT_SAVED = "P3.4 重启恢复 canary"
PROGRESS_SAVED = 64
FIXTURE = b"KMFA-P34-SYNTHETIC-CANARY\x00\xff\n" + bytes(range(256)) * 19
EXPECTED_HASH = hashlib.sha256(FIXTURE).hexdigest()


class BrowserSurfaceProbe:
    """Collect only non-secret-bearing browser surfaces for an in-memory scan."""

    def __init__(self) -> None:
        self.request_urls: list[str] = []
        self.referers: list[str] = []
        self.console_messages: list[str] = []
        self.page_errors: list[str] = []
        self.performance_urls: list[str] = []
        self.cache_entries: list[str] = []
        self.application_error_bodies: list[str] = []
        self.response_cache_controls: list[tuple[str, str]] = []
        self.foreign_http_requests: list[str] = []

    def attach(self, page: Page, base_url: str) -> None:
        base = urlsplit(base_url)

        def record_request(request) -> None:
            self.request_urls.append(request.url)
            referer = request.headers.get("referer", "")
            if referer:
                self.referers.append(referer)
            parsed = urlsplit(request.url)
            if (
                parsed.scheme in {"http", "https"}
                and (parsed.scheme, parsed.netloc) != (base.scheme, base.netloc)
            ):
                self.foreign_http_requests.append(request.url)

        def record_response(response) -> None:
            if urlsplit(response.url).path.startswith(API_PREFIX):
                self.response_cache_controls.append(
                    (response.url, response.headers.get("cache-control", ""))
                )

        page.on("request", record_request)
        page.on("response", record_response)
        page.on("console", lambda message: self.console_messages.append(message.text))
        page.on("pageerror", lambda error: self.page_errors.append(str(error)))

    def capture_client_surfaces(self, page: Page) -> None:
        self.performance_urls.extend(
            page.evaluate(
                "() => performance.getEntriesByType('resource').map((entry) => entry.name)"
            )
        )
        self.cache_entries.extend(
            page.evaluate(
                """async () => {
                  if (!('caches' in window)) return []
                  const entries = []
                  for (const key of await caches.keys()) {
                    entries.push(`cache:${key}`)
                    const cache = await caches.open(key)
                    for (const request of await cache.keys()) entries.push(request.url)
                  }
                  return entries
                }"""
            )
        )
        assert page.evaluate("() => document.cookie") == ""

    def scan(self, capabilities: tuple[str, ...]) -> dict[str, object]:
        surfaces = {
            "url": self.request_urls + self.performance_urls,
            "referer": self.referers,
            "browser_console": self.console_messages,
            "browser_error": self.page_errors + self.application_error_bodies,
            "browser_cache": self.cache_entries,
        }
        hits = {
            name: sum(secret in value for secret in capabilities for value in values)
            for name, values in surfaces.items()
        }
        assert not any(hits.values()), hits
        assert not self.foreign_http_requests, self.foreign_http_requests
        assert self.response_cache_controls
        assert all(
            "private" in value.lower() and "no-store" in value.lower()
            for _, value in self.response_cache_controls
        )
        return {
            "canary_hits": hits,
            "request_urls_scanned": len(self.request_urls),
            "referers_scanned": len(self.referers),
            "console_messages_scanned": len(self.console_messages),
            "browser_errors_scanned": (
                len(self.page_errors) + len(self.application_error_bodies)
            ),
            "performance_urls_scanned": len(self.performance_urls),
            "cache_entries_scanned": len(self.cache_entries),
            "walking_responses_no_store": len(self.response_cache_controls),
            "foreign_http_requests": 0,
        }


def _session_cookie(
    context: BrowserContext,
) -> tuple[str, dict[str, object]]:
    matches = [
        cookie
        for cookie in context.cookies()
        if cookie["name"] == SESSION_COOKIE_NAME
    ]
    assert len(matches) == 1, matches
    cookie = matches[0]
    token = str(cookie["value"])
    assert ACCESS_RE.fullmatch(token)
    assert cookie["secure"] is True
    assert cookie["httpOnly"] is True
    assert cookie["sameSite"] == "Strict"
    assert cookie["path"] == API_PREFIX
    assert cookie["expires"] > time.time()
    assert cookie["expires"] <= time.time() + 3660
    return token, {
        "name": SESSION_COOKIE_NAME,
        "secure": True,
        "http_only": True,
        "same_site": "Strict",
        "path": API_PREFIX,
        "host_only": not str(cookie["domain"]).startswith("."),
        "max_age_seconds": 3600,
        "document_cookie_visible": False,
    }


def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        check=check,
        capture_output=True,
        text=True,
    )


def _container_exists(name: str) -> bool:
    return _run("docker", "inspect", name, check=False).returncode == 0


def _wait_ready(base_url: str, timeout: float = 60) -> None:
    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/healthz", timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError) as exc:
            last_error = str(exc)
        time.sleep(0.5)
    raise AssertionError(f"container health timeout: {last_error}")


def _post_status(
    url: str,
    payload: bytes,
    *,
    content_type: str,
    response_samples: list[str] | None = None,
) -> int:
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": content_type, "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            if response_samples is not None:
                response_samples.append(response.read().decode("utf-8", errors="replace"))
            return response.status
    except urllib.error.HTTPError as exc:
        if response_samples is not None:
            response_samples.append(exc.read().decode("utf-8", errors="replace"))
        return exc.code


def _authorized_workspace_status(
    base_url: str,
    workspace_id: str,
    access_token: str,
) -> int:
    request = urllib.request.Request(
        f"{base_url}{API_PREFIX}/workspaces/{workspace_id}",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code


class ContainerLifecycle:
    def __init__(
        self,
        *,
        name: str,
        image: str,
        state_dir: Path,
        port: int,
        user_spec: str | None,
    ) -> None:
        self.name = name
        self.image = image
        self.state_dir = state_dir
        self.port = port
        self.user_spec = user_spec
        self.owned = False
        # Chromium treats localhost as a potentially trustworthy origin, so
        # the production Secure cookie can be exercised without weakening it.
        self.base_url = f"http://localhost:{port}"

    def start(self, *, enabled: bool) -> None:
        assert not self.owned
        assert not _container_exists(self.name), (
            f"refusing to replace pre-existing container {self.name}"
        )
        user_args = ("--user", self.user_spec) if self.user_spec else ()
        result = _run(
            "docker",
            "run",
            "-d",
            "--name",
            self.name,
            "-p",
            f"127.0.0.1:{self.port}:8000",
            "-e",
            f"KMFA_WALKING_SKELETON_ENABLED={1 if enabled else 0}",
            "-e",
            "KMFA_PUBLIC_INDEXING_ENABLED=0",
            "-e",
            "KMFA_PRIVATE_OPS_REQUIRE_ACCESS=1",
            "-v",
            f"{self.state_dir}:/var/lib/kmfa/state",
            *user_args,
            self.image,
        )
        assert result.stdout.strip(), result.stderr
        self.owned = True
        try:
            _wait_ready(self.base_url)
        except Exception:
            logs = _run("docker", "logs", self.name, check=False)
            raise AssertionError(
                f"container failed to start:\n{logs.stdout}\n{logs.stderr}"
            )

    def restart(self) -> None:
        assert self.owned
        _run("docker", "restart", self.name)
        _wait_ready(self.base_url)

    def logs(self) -> str:
        if not self.owned:
            return ""
        result = _run("docker", "logs", self.name, check=False)
        return result.stdout + result.stderr

    def remove(self) -> None:
        if not self.owned:
            return
        _run("docker", "rm", "-f", self.name)
        self.owned = False


def _goto_ready(page: Page, base_url: str) -> None:
    response = page.goto(f"{base_url}/", wait_until="networkidle", timeout=30_000)
    assert response and response.status == 200
    page.locator('[data-walking-skeleton-state="ready"]').wait_for(timeout=10_000)
    page.locator('[data-walking-ready="true"]').wait_for(timeout=10_000)


def _browser_storage(page: Page) -> dict[str, int]:
    return page.evaluate(
        """() => ({
          localStorage: localStorage.length,
          sessionStorage: sessionStorage.length
        })"""
    )


def _seed(
    browser: Browser,
    base_url: str,
    probe: BrowserSurfaceProbe,
) -> dict[str, object]:
    context = browser.new_context(locale="zh-CN", accept_downloads=True)
    page = context.new_page()
    probe.attach(page, base_url)
    try:
        _goto_ready(page, base_url)
        warning = page.locator('[data-recovery-warning="visible"]')
        warning.wait_for()
        assert "邮箱" in warning.inner_text() and "无法" in warning.inner_text()
        page.get_by_label("项目名称", exact=True).fill(PROJECT_CREATED)
        page.get_by_role("button", name="创建并生成恢复码").click()
        page.locator('[data-workspace-ready="true"]').wait_for()
        recovery = page.locator("[data-recovery-code-value]").text_content()
        assert recovery and RECOVERY_RE.fullmatch(recovery)
        assert recovery not in page.url
        page.evaluate(
            "(secret) => console.error(new Error(`synthetic ${secret}`))",
            recovery,
        )

        page.locator("#walking-project-save").fill(PROJECT_SAVED)
        page.locator("#walking-progress").fill(str(PROGRESS_SAVED))
        page.get_by_role("button", name="保存项目与进度").click()
        page.locator('[data-walking-message="success"]', has_text="64%").wait_for()

        page.locator("#walking-file").set_input_files(
            {
                "name": FIXTURE_NAME,
                "mimeType": "application/x-kmfa-canary",
                "buffer": FIXTURE,
            }
        )
        page.get_by_role("button", name="上传到服务器").click()
        page.locator('[data-walking-artifact="ready"]').wait_for()
        page.locator(
            '[data-walking-message="success"]', has_text=EXPECTED_HASH
        ).wait_for()
        assert (
            page.locator(".walking-artifact code", has_text=EXPECTED_HASH).count() == 1
        )
        with page.expect_download(timeout=15_000) as download_info:
            page.get_by_role("button", name="下载 .kmfa-recovery").click()
        recovery_download = download_info.value
        assert recovery_download.suggested_filename == "kmfa-workspace.kmfa-recovery"
        recovery_path = recovery_download.path()
        assert recovery_path is not None
        recovery_file = Path(recovery_path).read_bytes()
        recovery_payload = json.loads(recovery_file)
        assert set(recovery_payload) == RECOVERY_FILE_KEYS
        assert recovery_payload == {
            "format": "kmfa-recovery",
            "version": 1,
            "workspace_id": recovery_payload["workspace_id"],
            "workspace_secret": recovery,
        }
        assert recovery not in page.url
        storage = _browser_storage(page)
        assert storage["localStorage"] == 0 and storage["sessionStorage"] == 0
        session_token, cookie = _session_cookie(context)
        probe.capture_client_surfaces(page)
        return {
            "recovery_code": recovery,
            "recovery_file": recovery_file,
            "_session_token": session_token,
            "recovery_file_bytes": len(recovery_file),
            "browser_storage": storage,
            "session_cookie": cookie,
            "project": PROJECT_SAVED,
            "progress": PROGRESS_SAVED,
            "upload_sha256": EXPECTED_HASH,
        }
    finally:
        context.close()


def _recover_and_download(
    browser: Browser,
    base_url: str,
    recovery_code: str,
    *,
    probe: BrowserSurfaceProbe,
    workspace_id: str,
    revoke: bool,
    screenshot: Path | None = None,
) -> dict[str, object]:
    context = browser.new_context(locale="zh-CN", accept_downloads=True)
    page = context.new_page()
    probe.attach(page, base_url)
    try:
        _goto_ready(page, base_url)
        warning = page.locator('[data-recovery-warning="visible"]')
        warning.wait_for()
        assert "邮箱" in warning.inner_text() and "无法" in warning.inner_text()
        page.get_by_role("button", name="使用恢复码").click()
        page.get_by_label("恢复码", exact=True).fill(recovery_code)
        page.get_by_role("button", name="恢复服务器工作区").click()
        page.locator('[data-workspace-ready="true"]').wait_for()
        assert page.locator("#walking-project-save").input_value() == PROJECT_SAVED
        assert page.locator("#walking-progress").input_value() == str(PROGRESS_SAVED)
        assert (
            page.locator(".walking-artifact code", has_text=EXPECTED_HASH).count() == 1
        )
        assert recovery_code not in page.url
        assert page.get_by_label("恢复码", exact=True).count() == 0

        with page.expect_download(timeout=15_000) as download_info:
            page.get_by_role("button", name="校验并下载").click()
        download = download_info.value
        assert download.suggested_filename == FIXTURE_NAME
        with tempfile.NamedTemporaryFile(
            prefix="kmfa-p34-download-", delete=True
        ) as out:
            download.save_as(out.name)
            downloaded = Path(out.name).read_bytes()
        assert downloaded == FIXTURE
        downloaded_hash = hashlib.sha256(downloaded).hexdigest()
        assert downloaded_hash == EXPECTED_HASH
        page.locator(
            '[data-walking-message="success"]', has_text=EXPECTED_HASH
        ).wait_for()
        if screenshot:
            page.screenshot(path=screenshot, full_page=True)
        storage = _browser_storage(page)
        assert storage["localStorage"] == 0 and storage["sessionStorage"] == 0
        session_token, cookie = _session_cookie(context)
        result: dict[str, object] = {
            "project": PROJECT_SAVED,
            "progress": PROGRESS_SAVED,
            "download_sha256": downloaded_hash,
            "download_bytes": len(downloaded),
            "browser_storage": storage,
            "session_cookie": cookie,
            "recovery_secret_in_url": False,
            "_session_token": session_token,
        }
        if revoke:
            page.get_by_role(
                "button",
                name="撤销并清除本页会话",
            ).click()
            page.locator(
                '[data-walking-message="success"]',
                has_text="已在服务器撤销",
            ).wait_for()
            page.locator('[data-walking-recover="true"]').wait_for()
            assert not [
                item
                for item in context.cookies()
                if item["name"] == SESSION_COOKIE_NAME
            ]
            replay_status = _authorized_workspace_status(
                base_url,
                workspace_id,
                session_token,
            )
            assert replay_status == 404
            result.update(
                {
                    "session_revoked": True,
                    "cookie_cleared": True,
                    "revoked_session_replay_status": replay_status,
                }
            )
        probe.capture_client_surfaces(page)
        return result
    finally:
        context.close()


def _recover_file_and_download(
    browser: Browser,
    base_url: str,
    recovery_file: bytes,
    *,
    probe: BrowserSurfaceProbe,
    rotate: bool,
    screenshot: Path | None = None,
) -> dict[str, object]:
    """Use an isolated device context and optionally rotate recovery material."""

    context = browser.new_context(locale="zh-CN", accept_downloads=True)
    page = context.new_page()
    probe.attach(page, base_url)
    try:
        source_recovery = json.loads(recovery_file)
        workspace_id = str(source_recovery["workspace_id"])
        _goto_ready(page, base_url)
        warning = page.locator('[data-recovery-warning="visible"]')
        warning.wait_for()
        assert "邮箱" in warning.inner_text() and "无法" in warning.inner_text()
        page.get_by_role("button", name="使用恢复码").click()
        page.get_by_label("恢复文件（.kmfa-recovery）", exact=True).set_input_files(
            {
                "name": "device-a.kmfa-recovery",
                "mimeType": RECOVERY_FILE_MEDIA_TYPE,
                "buffer": recovery_file,
            }
        )
        page.get_by_role("button", name="导入恢复文件").click()
        page.locator('[data-workspace-ready="true"]').wait_for()
        assert page.locator("#walking-project-save").input_value() == PROJECT_SAVED
        assert page.locator("#walking-progress").input_value() == str(PROGRESS_SAVED)
        assert (
            page.locator(".walking-artifact code", has_text=EXPECTED_HASH).count() == 1
        )
        assert page.locator("[data-recovery-code-value]").count() == 0

        with page.expect_download(timeout=15_000) as download_info:
            page.get_by_role("button", name="校验并下载").click()
        download = download_info.value
        assert download.suggested_filename == FIXTURE_NAME
        with tempfile.NamedTemporaryFile(
            prefix="kmfa-p42-device-b-download-", delete=True
        ) as out:
            download.save_as(out.name)
            downloaded = Path(out.name).read_bytes()
        downloaded_hash = hashlib.sha256(downloaded).hexdigest()
        assert downloaded == FIXTURE and downloaded_hash == EXPECTED_HASH
        if screenshot:
            page.screenshot(path=screenshot, full_page=True)

        storage = _browser_storage(page)
        assert storage["localStorage"] == 0 and storage["sessionStorage"] == 0
        session_token, cookie = _session_cookie(context)
        result: dict[str, object] = {
            "project": PROJECT_SAVED,
            "progress": PROGRESS_SAVED,
            "download_sha256": downloaded_hash,
            "download_bytes": len(downloaded),
            "recovery_file_bytes": len(recovery_file),
            "browser_storage": storage,
            "session_cookie": cookie,
            "_session_token": session_token,
            "recovery_secret_in_url": False,
        }
        if not rotate:
            probe.capture_client_surfaces(page)
            return result

        page.once("dialog", lambda dialog: dialog.accept())
        page.get_by_role("button", name="轮换并撤销旧密钥").click()
        page.locator(
            '[data-walking-message="success"]',
            has_text="旧恢复材料和旧会话均已失效",
        ).wait_for()
        replacement_token, replacement_cookie = _session_cookie(context)
        assert replacement_token != session_token
        old_session_replay_status = _authorized_workspace_status(
            base_url,
            workspace_id,
            session_token,
        )
        assert old_session_replay_status == 404
        new_recovery_code = page.locator(
            "[data-recovery-code-value]"
        ).text_content()
        assert new_recovery_code and RECOVERY_RE.fullmatch(new_recovery_code)
        assert new_recovery_code not in page.url

        with page.expect_download(timeout=15_000) as recovery_download_info:
            page.get_by_role("button", name="下载 .kmfa-recovery").click()
        recovery_download = recovery_download_info.value
        assert recovery_download.suggested_filename == "kmfa-workspace.kmfa-recovery"
        recovery_path = recovery_download.path()
        assert recovery_path is not None
        new_recovery_file = Path(recovery_path).read_bytes()
        parsed = json.loads(new_recovery_file)
        assert set(parsed) == RECOVERY_FILE_KEYS
        assert parsed["workspace_secret"] == new_recovery_code
        assert parsed["format"] == "kmfa-recovery" and parsed["version"] == 1

        probe.capture_client_surfaces(page)
        return {
            **result,
            "new_recovery_code": new_recovery_code,
            "new_recovery_file": new_recovery_file,
            "_replacement_session_token": replacement_token,
            "replacement_recovery_file_bytes": len(new_recovery_file),
            "rotation_old_material_revoked": True,
            "rotation_old_session_replay_status": old_session_replay_status,
            "replacement_session_cookie": replacement_cookie,
        }
    finally:
        context.close()


def _state_evidence(
    state_dir: Path,
    capabilities: tuple[str, ...],
) -> dict[str, object]:
    root = state_dir / "walking-skeleton"
    database = root / "walking_skeleton.sqlite3"
    assert database.is_file()
    connection = sqlite3.connect(database)
    try:
        workspace = connection.execute(
            "SELECT project_name, progress FROM workspaces"
        ).fetchall()
        artifact = connection.execute(
            "SELECT size_bytes, sha256, object_name FROM artifacts"
        ).fetchall()
        actions = [
            row[0]
            for row in connection.execute(
                "SELECT action FROM audit_events ORDER BY seq"
            )
        ]
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("workspaces", "artifacts", "access_tokens", "audit_events")
        }
    finally:
        connection.close()
    assert workspace == [(PROJECT_SAVED, PROGRESS_SAVED)]
    assert len(artifact) == 1
    size_bytes, artifact_hash, object_name = artifact[0]
    assert size_bytes == len(FIXTURE) and artifact_hash == EXPECTED_HASH
    object_path = root / "objects" / object_name
    assert object_path.is_file()
    object_hash = hashlib.sha256(object_path.read_bytes()).hexdigest()
    assert object_hash == EXPECTED_HASH
    required_actions = {
        "workspace_created",
        "workspace_saved",
        "artifact_uploaded",
        "workspace_recovered",
        "recovery_file_exported",
        "recovery_file_imported",
        "workspace_sessions_revoked",
        "workspace_secret_rotated",
        "workspace_session_revoked",
        "artifact_download",
    }
    assert required_actions <= set(actions)
    capability_hits = [
        str(path.relative_to(state_dir))
        for path in state_dir.rglob("*")
        if path.is_file()
        and any(
            capability.encode("ascii") in path.read_bytes()
            for capability in capabilities
        )
    ]
    assert not capability_hits
    return {
        "row_counts": counts,
        "workspace_project": PROJECT_SAVED,
        "workspace_progress": PROGRESS_SAVED,
        "object_count": 1,
        "object_sha256": object_hash,
        "audit_actions": actions,
        "capability_state_hits": 0,
    }


def _rollback_browser(
    browser: Browser,
    base_url: str,
    probe: BrowserSurfaceProbe,
) -> dict[str, object]:
    context = browser.new_context(locale="zh-CN")
    page = context.new_page()
    probe.attach(page, base_url)
    try:
        response = page.goto(f"{base_url}/", wait_until="networkidle", timeout=30_000)
        assert response and response.status == 200
        page.locator('[data-walking-skeleton-state="rollback"]').wait_for()
        page.locator('[data-walking-boundary="rollback"]').wait_for()
        assert page.locator('[data-walking-create="true"]').count() == 0
        probe.capture_client_surfaces(page)
        return {"root_status": 200, "ui_mode": "rollback", "create_form_count": 0}
    finally:
        context.close()


def _disabled_recovery_status(
    base_url: str,
    recovery_code: str,
    response_samples: list[str],
) -> int:
    request = urllib.request.Request(
        f"{base_url}/public-api/walking-skeleton/v1/recoveries",
        data=json.dumps({"recovery_code": recovery_code}).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            response_samples.append(response.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        response_samples.append(exc.read().decode("utf-8", errors="replace"))
        return exc.code
    raise AssertionError("disabled recovery unexpectedly succeeded")


def _negative_recovery_matrix(
    base_url: str,
    *,
    revoked_code: str,
    revoked_file: bytes,
    current_code: str,
    response_samples: list[str],
) -> dict[str, object]:
    parsed = json.loads(revoked_file)
    workspace_id = str(parsed["workspace_id"])
    wrong_code = "kmfa-r1-" + ("W" * 43)
    if wrong_code in {revoked_code, current_code}:
        wrong_code = "kmfa-r1-" + ("X" * 43)
    wrong_file_payload = dict(parsed)
    wrong_file_payload["workspace_secret"] = wrong_code

    statuses = {
        "wrong_code": _post_status(
            f"{base_url}/public-api/walking-skeleton/v1/recoveries",
            json.dumps({"recovery_code": wrong_code}).encode("utf-8"),
            content_type="application/json",
            response_samples=response_samples,
        ),
        "truncated_file": _post_status(
            f"{base_url}/public-api/walking-skeleton/v1/recovery-files/import",
            revoked_file[:-12],
            content_type=RECOVERY_FILE_MEDIA_TYPE,
            response_samples=response_samples,
        ),
        "wrong_file_secret": _post_status(
            f"{base_url}/public-api/walking-skeleton/v1/recovery-files/import",
            json.dumps(wrong_file_payload).encode("utf-8"),
            content_type=RECOVERY_FILE_MEDIA_TYPE,
            response_samples=response_samples,
        ),
        "revoked_code": _post_status(
            f"{base_url}/public-api/walking-skeleton/v1/recoveries",
            json.dumps({"recovery_code": revoked_code}).encode("utf-8"),
            content_type="application/json",
            response_samples=response_samples,
        ),
        "revoked_file": _post_status(
            f"{base_url}/public-api/walking-skeleton/v1/recovery-files/import",
            revoked_file,
            content_type=RECOVERY_FILE_MEDIA_TYPE,
            response_samples=response_samples,
        ),
        "revoked_session_exchange": _post_status(
            f"{base_url}/public-api/walking-skeleton/v1/sessions",
            json.dumps(
                {
                    "workspace_id": workspace_id,
                    "workspace_secret": revoked_code,
                }
            ).encode("utf-8"),
            content_type="application/json",
            response_samples=response_samples,
        ),
    }
    authorization_successes = sum(200 <= status < 300 for status in statuses.values())
    assert set(statuses.values()) == {404}
    assert authorization_successes == 0
    return {
        "attempts": len(statuses),
        "http_statuses": statuses,
        "authorization_successes": authorization_successes,
    }


def _screenshot_secret_scan(
    out_dir: Path,
    capabilities: tuple[str, ...],
) -> dict[str, int]:
    screenshots = sorted(out_dir.glob("*.png"))
    assert screenshots
    hits = sum(
        capability.encode("ascii") in screenshot.read_bytes()
        for capability in capabilities
        for screenshot in screenshots
    )
    assert hits == 0
    return {"screenshots_scanned": len(screenshots), "canary_hits": 0}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--container-name", default="kmfa-p34-e2e")
    parser.add_argument("--port", type=int, default=18099)
    args = parser.parse_args()

    assert CONTAINER_RE.fullmatch(args.container_name), (
        "container name must use the kmfa-p34-* test prefix"
    )
    args.state_dir = args.state_dir.resolve()
    args.out_dir = args.out_dir.resolve()
    args.state_dir.mkdir(parents=True, exist_ok=True)
    assert not any(args.state_dir.iterdir()), "state directory must start empty"
    args.out_dir.mkdir(parents=True, exist_ok=True)
    assert not _container_exists(args.container_name), "test container already exists"
    image_id = _run(
        "docker", "image", "inspect", "--format", "{{.Id}}", args.image
    ).stdout.strip()
    assert image_id.startswith("sha256:")

    lifecycle = ContainerLifecycle(
        name=args.container_name,
        image=args.image,
        state_dir=args.state_dir,
        port=args.port,
        # Bind-mounted evidence must remain readable by the host-side Oracle
        # on native Linux runners. Docker Desktop masks this UID/GID boundary.
        # Production keeps the image's default user; this override is test-only.
        user_spec=(
            f"{os.getuid()}:{os.getgid()}"
            if hasattr(os, "getuid") and hasattr(os, "getgid")
            else None
        ),
    )
    probe = BrowserSurfaceProbe()
    log_samples: list[str] = []
    try:
        lifecycle.start(enabled=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                seed = _seed(browser, lifecycle.base_url, probe)
                revoked_code = str(seed.pop("recovery_code"))
                revoked_file = bytes(seed.pop("recovery_file"))
                seed_session = str(seed.pop("_session_token"))
                lifecycle.restart()
                device_b = _recover_file_and_download(
                    browser,
                    lifecycle.base_url,
                    revoked_file,
                    probe=probe,
                    rotate=True,
                    screenshot=args.out_dir / "recovered-after-restart.png",
                )
                current_code = str(device_b.pop("new_recovery_code"))
                current_file = bytes(device_b.pop("new_recovery_file"))
                device_b_session = str(device_b.pop("_session_token"))
                replacement_session = str(
                    device_b.pop("_replacement_session_token")
                )
                negative = _negative_recovery_matrix(
                    lifecycle.base_url,
                    revoked_code=revoked_code,
                    revoked_file=revoked_file,
                    current_code=current_code,
                    response_samples=probe.application_error_bodies,
                )
                workspace_id = str(json.loads(current_file)["workspace_id"])
                current_code_recovery = _recover_and_download(
                    browser,
                    lifecycle.base_url,
                    current_code,
                    probe=probe,
                    workspace_id=workspace_id,
                    revoke=True,
                )
                revoked_current_session = str(
                    current_code_recovery.pop("_session_token")
                )
                pre_restore_capabilities = (
                    revoked_code,
                    current_code,
                    seed_session,
                    device_b_session,
                    replacement_session,
                    revoked_current_session,
                )
                first_state = _state_evidence(
                    args.state_dir,
                    pre_restore_capabilities,
                )
                log_samples.append(lifecycle.logs())

                lifecycle.remove()
                lifecycle.start(enabled=False)
                rollback = _rollback_browser(browser, lifecycle.base_url, probe)
                rollback["recovery_status"] = _disabled_recovery_status(
                    lifecycle.base_url,
                    current_code,
                    probe.application_error_bodies,
                )
                assert rollback["recovery_status"] == 404
                rollback_state = _state_evidence(
                    args.state_dir,
                    pre_restore_capabilities,
                )
                assert rollback_state["object_sha256"] == first_state["object_sha256"]
                assert rollback_state["row_counts"] == first_state["row_counts"]
                log_samples.append(lifecycle.logs())

                lifecycle.remove()
                lifecycle.start(enabled=True)
                restored = _recover_file_and_download(
                    browser,
                    lifecycle.base_url,
                    current_file,
                    probe=probe,
                    rotate=False,
                )
                restored_session = str(restored.pop("_session_token"))
                capabilities = (*pre_restore_capabilities, restored_session)
                final_state = _state_evidence(args.state_dir, capabilities)
                log_samples.append(lifecycle.logs())
            finally:
                browser.close()
        joined_logs = "\n".join(log_samples)
        capability_log_hits = sum(
            capability in joined_logs for capability in capabilities
        )
        assert capability_log_hits == 0
        browser_surface_scan = probe.scan(capabilities)
        screenshot_scan = _screenshot_secret_scan(args.out_dir, capabilities)

        trace = {
            "contract": "S04/P4.2 AC-WS-002 + S04/P4.3 AC-WS-003",
            "capabilities_redacted": True,
            "native_trace_omitted_reason": (
                "Browser traces retain capability-bearing DOM and POST bodies"
            ),
            "steps": [
                {
                    "seq": 1,
                    "device": "A",
                    "action": "warning-create-save-upload-export-recovery-file",
                    "status": "PASS",
                },
                {
                    "seq": 2,
                    "device": "server",
                    "action": "restart-with-durable-state",
                    "status": "PASS",
                },
                {
                    "seq": 3,
                    "device": "B-isolated-context",
                    "action": (
                        "import-file-compare-download-rotate-secret-and-sessions-"
                        "export-replacement"
                    ),
                    "status": "PASS",
                },
                {
                    "seq": 4,
                    "device": "negative-oracle",
                    "action": "wrong-truncated-revoked-material",
                    "authorization_successes": 0,
                    "status": "PASS",
                },
                {
                    "seq": 5,
                    "device": "C-isolated-context",
                    "action": (
                        "recover-with-rotated-code-compare-revoke-session-"
                        "reject-replay"
                    ),
                    "status": "PASS",
                },
                {
                    "seq": 6,
                    "device": "server",
                    "action": "flag-rollback-preserves-state",
                    "status": "PASS",
                },
                {
                    "seq": 7,
                    "device": "D-isolated-context",
                    "action": "reenable-import-rotated-file-and-compare",
                    "status": "PASS",
                },
                {
                    "seq": 8,
                    "device": "secret-hygiene-oracle",
                    "action": (
                        "scan-url-referer-logs-events-errors-cache-screenshot-"
                        "and-session-cookie"
                    ),
                    "canary_hits": 0,
                    "status": "PASS",
                },
            ],
        }
        (args.out_dir / "sanitized-e2e-trace.json").write_text(
            json.dumps(trace, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        result = {
            "contract": (
                "S03/P3.4 TEST-QA-001 + S04/P4.2 AC-WS-002 + "
                "S04/P4.3 AC-WS-003"
            ),
            "image_id": image_id,
            "fixture": {
                "name": FIXTURE_NAME,
                "bytes": len(FIXTURE),
                "sha256": EXPECTED_HASH,
                "synthetic": True,
            },
            "seed": seed,
            "restart_file_recovery_and_rotation": device_b,
            "rotated_code_recovery": current_code_recovery,
            "negative_recovery_matrix": negative,
            "durable_state_after_restart": first_state,
            "object_inventory": {
                "before_device_restore": {
                    "object_count": 1,
                    "object_sha256": seed["upload_sha256"],
                },
                "after_device_restore": {
                    "object_count": first_state["object_count"],
                    "object_sha256": first_state["object_sha256"],
                },
                "after_reenable_restore": {
                    "object_count": final_state["object_count"],
                    "object_sha256": final_state["object_sha256"],
                },
            },
            "flag_rollback": {
                **rollback,
                "state_rows_unchanged": True,
                "object_sha256_unchanged": True,
            },
            "reenable_recovery": restored,
            "final_state": final_state,
            "recovery_warning_visible_on_all_entry_devices": True,
            "valid_recovery_data_consistency_percent": 100,
            "invalid_authorization_successes": negative[
                "authorization_successes"
            ],
            "e2e_trace": "sanitized-e2e-trace.json",
            "secret_hygiene": {
                "browser_surfaces": browser_surface_scan,
                "container_log_canary_hits": capability_log_hits,
                "state_canary_hits": 0,
                "screenshots": screenshot_scan,
                "session_cookie_protected": True,
                "session_rotation_replay_status": device_b[
                    "rotation_old_session_replay_status"
                ],
                "explicit_revocation_replay_status": current_code_recovery[
                    "revoked_session_replay_status"
                ],
                "total_canary_hits": 0,
            },
            "status": "PASS",
        }
        (args.out_dir / "result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "contract": result["contract"],
                    "restart_download_sha256": device_b["download_sha256"],
                    "rollback_recovery_status": rollback["recovery_status"],
                    "reenable_download_sha256": restored["download_sha256"],
                    "invalid_authorization_successes": 0,
                    "secret_hygiene_canary_hits": 0,
                    "revoked_session_replay_status": current_code_recovery[
                        "revoked_session_replay_status"
                    ],
                    "status": "PASS",
                },
                ensure_ascii=False,
            )
        )
        return 0
    finally:
        lifecycle.remove()


if __name__ == "__main__":
    raise SystemExit(main())
