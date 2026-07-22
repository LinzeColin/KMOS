#!/usr/bin/env python3
"""S03/P3.4 TEST-QA-001 final-image restart/recovery/rollback oracle.

The script owns one explicitly test-prefixed container and an initially empty
state directory. It never deletes the state directory. Evidence contains only
synthetic fixture metadata and hashes; recovery/access capabilities are kept in
memory and are explicitly scanned out of state files and container logs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import Browser, Page, sync_playwright

RECOVERY_RE = re.compile(r"^kmfa-r1-[A-Za-z0-9_-]{43}$")
CONTAINER_RE = re.compile(r"^kmfa-p34-[a-z0-9-]+$")
FIXTURE_NAME = "walking-skeleton.canary.double.exe.unknown"
PROJECT_CREATED = "P3.4 合成 canary 项目"
PROJECT_SAVED = "P3.4 重启恢复 canary"
PROGRESS_SAVED = 64
FIXTURE = b"KMFA-P34-SYNTHETIC-CANARY\x00\xff\n" + bytes(range(256)) * 19
EXPECTED_HASH = hashlib.sha256(FIXTURE).hexdigest()


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
        self.owned = False
        self.base_url = f"http://127.0.0.1:{port}"

    def start(self, *, enabled: bool) -> None:
        assert not self.owned
        assert not _container_exists(self.name), (
            f"refusing to replace pre-existing container {self.name}"
        )
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


def _seed(browser: Browser, base_url: str) -> dict[str, object]:
    context = browser.new_context(locale="zh-CN")
    page = context.new_page()
    try:
        _goto_ready(page, base_url)
        page.get_by_label("项目名称", exact=True).fill(PROJECT_CREATED)
        page.get_by_role("button", name="创建并生成恢复码").click()
        page.locator('[data-workspace-ready="true"]').wait_for()
        recovery = page.locator("[data-recovery-code-value]").text_content()
        assert recovery and RECOVERY_RE.fullmatch(recovery)
        assert recovery not in page.url

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
        storage = _browser_storage(page)
        assert storage["localStorage"] == 0 and storage["sessionStorage"] == 0
        assert not context.cookies()
        return {
            "recovery_code": recovery,
            "browser_storage": storage,
            "cookies": 0,
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
    screenshot: Path | None = None,
) -> dict[str, object]:
    context = browser.new_context(locale="zh-CN", accept_downloads=True)
    page = context.new_page()
    try:
        _goto_ready(page, base_url)
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
        assert not context.cookies()
        return {
            "project": PROJECT_SAVED,
            "progress": PROGRESS_SAVED,
            "download_sha256": downloaded_hash,
            "download_bytes": len(downloaded),
            "browser_storage": storage,
            "cookies": 0,
            "recovery_secret_in_url": False,
        }
    finally:
        context.close()


def _state_evidence(state_dir: Path, recovery_code: str) -> dict[str, object]:
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
        "artifact_download",
    }
    assert required_actions <= set(actions)
    recovery_bytes = recovery_code.encode("ascii")
    secret_hits = [
        str(path.relative_to(state_dir))
        for path in state_dir.rglob("*")
        if path.is_file() and recovery_bytes in path.read_bytes()
    ]
    assert not secret_hits
    return {
        "row_counts": counts,
        "workspace_project": PROJECT_SAVED,
        "workspace_progress": PROGRESS_SAVED,
        "object_count": 1,
        "object_sha256": object_hash,
        "audit_actions": actions,
        "recovery_secret_state_hits": 0,
    }


def _rollback_browser(browser: Browser, base_url: str) -> dict[str, object]:
    context = browser.new_context(locale="zh-CN")
    page = context.new_page()
    try:
        response = page.goto(f"{base_url}/", wait_until="networkidle", timeout=30_000)
        assert response and response.status == 200
        page.locator('[data-walking-skeleton-state="rollback"]').wait_for()
        page.locator('[data-walking-boundary="rollback"]').wait_for()
        assert page.locator('[data-walking-create="true"]').count() == 0
        return {"root_status": 200, "ui_mode": "rollback", "create_form_count": 0}
    finally:
        context.close()


def _disabled_recovery_status(base_url: str, recovery_code: str) -> int:
    request = urllib.request.Request(
        f"{base_url}/public-api/walking-skeleton/v1/recoveries",
        data=json.dumps({"recovery_code": recovery_code}).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=5)
    except urllib.error.HTTPError as exc:
        return exc.code
    raise AssertionError("disabled recovery unexpectedly succeeded")


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
    )
    log_secret_hits = 0
    try:
        lifecycle.start(enabled=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                seed = _seed(browser, lifecycle.base_url)
                recovery_code = str(seed.pop("recovery_code"))
                lifecycle.restart()
                recovered = _recover_and_download(
                    browser,
                    lifecycle.base_url,
                    recovery_code,
                    screenshot=args.out_dir / "recovered-after-restart.png",
                )
                first_state = _state_evidence(args.state_dir, recovery_code)
                log_secret_hits += int(recovery_code in lifecycle.logs())

                lifecycle.remove()
                lifecycle.start(enabled=False)
                rollback = _rollback_browser(browser, lifecycle.base_url)
                rollback["recovery_status"] = _disabled_recovery_status(
                    lifecycle.base_url, recovery_code
                )
                assert rollback["recovery_status"] == 404
                rollback_state = _state_evidence(args.state_dir, recovery_code)
                assert rollback_state["object_sha256"] == first_state["object_sha256"]
                assert rollback_state["row_counts"] == first_state["row_counts"]
                log_secret_hits += int(recovery_code in lifecycle.logs())

                lifecycle.remove()
                lifecycle.start(enabled=True)
                restored = _recover_and_download(
                    browser,
                    lifecycle.base_url,
                    recovery_code,
                )
                final_state = _state_evidence(args.state_dir, recovery_code)
                log_secret_hits += int(recovery_code in lifecycle.logs())
            finally:
                browser.close()
        assert log_secret_hits == 0

        result = {
            "contract": "S03/P3.4 TEST-QA-001",
            "image_id": image_id,
            "fixture": {
                "name": FIXTURE_NAME,
                "bytes": len(FIXTURE),
                "sha256": EXPECTED_HASH,
                "synthetic": True,
            },
            "seed": seed,
            "restart_recovery": recovered,
            "durable_state_after_restart": first_state,
            "flag_rollback": {
                **rollback,
                "state_rows_unchanged": True,
                "object_sha256_unchanged": True,
            },
            "reenable_recovery": restored,
            "final_state": final_state,
            "recovery_secret_log_hits": log_secret_hits,
            "recovery_secret_state_hits": 0,
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
                    "restart_download_sha256": recovered["download_sha256"],
                    "rollback_recovery_status": rollback["recovery_status"],
                    "reenable_download_sha256": restored["download_sha256"],
                    "recovery_secret_hits": 0,
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
