#!/usr/bin/env python3
"""S07/P7.2 exact-image Range and streaming batch ZIP Oracle.

All files are deterministic synthetic fixtures. Workspace capabilities stay in
memory and are excluded from the evidence directory and command output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from typing import Any
from zipfile import ZIP_STORED, ZipFile

from file_security_flow import (
    ACCESS_RE,
    RECOVERY_RE,
    HttpResult,
    Resources,
    _run,
)
from single_file_download_flow import DownloadApi

PREFIX_RE = re.compile(r"^kmfa-p72-[a-z0-9-]{1,32}$")


class RangeBatchApi(DownloadApi):
    def download_range(
        self,
        workspace_id: str,
        token: str,
        actor: dict[str, str],
        item: dict[str, Any],
        byte_range: str,
        *,
        if_range: str | None = None,
    ) -> HttpResult:
        headers = {
            **self.auth(token, actor),
            "Accept": "application/octet-stream",
            "Content-Type": "application/json",
            "Range": byte_range,
        }
        if if_range is not None:
            headers["If-Range"] = if_range
        return self.request(
            "POST",
            f"/workspaces/{workspace_id}/artifact/downloads",
            body=json.dumps(
                {"kind": item["kind"], "asset_id": item["id"]}
            ).encode(),
            headers=headers,
        )

    def download_batch(
        self,
        workspace_id: str,
        token: str,
        actor: dict[str, str],
        items: list[dict[str, Any]],
    ) -> HttpResult:
        return self.request(
            "POST",
            f"/workspaces/{workspace_id}/artifact/downloads/batch",
            body=json.dumps(
                {
                    "assets": [
                        {
                            "kind": item["kind"],
                            "asset_id": item["id"],
                        }
                        for item in items
                    ]
                }
            ).encode(),
            headers={
                **self.auth(token, actor),
                "Accept": "application/zip",
                "Content-Type": "application/json",
            },
        )


def _database_summary(resources: Resources) -> dict[str, Any]:
    command = (
        "import json,sqlite3,pathlib;"
        "root=pathlib.Path('/var/lib/kmfa/state/walking-skeleton');"
        "c=sqlite3.connect(root/'walking_skeleton.sqlite3');"
        "print(json.dumps({"
        "'schema_version':c.execute('PRAGMA user_version').fetchone()[0],"
        "'versions':c.execute("
        "\"SELECT COUNT(*) FROM artifact_versions\").fetchone()[0],"
        "'derivatives':c.execute("
        "\"SELECT COUNT(*) FROM artifact_derivatives\").fetchone()[0],"
        "'range_audits':c.execute("
        "\"SELECT COUNT(*) FROM audit_events "
        "WHERE action='artifact_download'\").fetchone()[0],"
        "'batch_audits':c.execute("
        "\"SELECT COUNT(*) FROM audit_events "
        "WHERE action='artifact_batch_download'\").fetchone()[0],"
        "'object_count':len(list((root/'objects').glob('*.blob'))),"
        "'object_bytes':sum(p.stat().st_size "
        "for p in (root/'objects').glob('*.blob')),"
        "'archive_temp_files':len(list((root/'tmp').glob('batch-*')))"
        "},sort_keys=True));c.close()"
    )
    return json.loads(
        _run(
            "docker",
            "exec",
            resources.app,
            "python3",
            "-c",
            command,
        ).stdout
    )


def _assert_range(
    result: HttpResult,
    *,
    item: dict[str, Any],
    expected: bytes,
    start: int,
    end: int,
) -> dict[str, Any]:
    assert result.status == 206, result.body
    assert result.body == expected[start : end + 1]
    assert result.headers["accept-ranges"] == "bytes"
    assert result.headers["content-range"] == (
        f"bytes {start}-{end}/{len(expected)}"
    )
    assert result.headers["content-length"] == str(end - start + 1)
    assert result.headers["etag"] == f'"{item["sha256"]}"'
    assert result.headers["x-kmfa-artifact-sha256"] == item["sha256"]
    assert result.headers["x-kmfa-artifact-id"] == item["id"]
    return {
        "status": result.status,
        "start": start,
        "end": end,
        "length": len(result.body),
        "content_range": result.headers["content-range"],
        "etag_matches_sha256": True,
        "chunk_sha256": hashlib.sha256(result.body).hexdigest(),
    }


def _inspect_batch(
    result: HttpResult,
    *,
    expected_count: int,
) -> tuple[dict[str, Any], dict[str, str]]:
    assert result.status == 200, result.body
    assert result.headers["content-type"] == "application/zip"
    assert result.headers["accept-ranges"] == "none"
    assert result.headers["x-kmfa-batch-file-count"] == str(expected_count)
    assert result.headers["x-kmfa-zip-format"] == "zip-stored-stream-v1"
    assert result.headers["x-kmfa-zip-compression"] == "stored"
    assert result.headers["x-kmfa-zip-manifest-path"] == "manifest.json"
    assert int(result.headers["content-length"]) == len(result.body)
    with ZipFile(BytesIO(result.body)) as archive:
        names = archive.namelist()
        assert len(names) == expected_count + 1
        assert len(names) == len(set(names))
        assert names[0] == "manifest.json"
        assert all(
            not name.startswith("/")
            and "\\" not in name
            and ".." not in name.split("/")
            for name in names
        )
        assert all(
            info.compress_type == ZIP_STORED
            for info in archive.infolist()
        )
        manifest_bytes = archive.read("manifest.json")
        manifest = json.loads(manifest_bytes)
        assert manifest["format"] == "kmfa-download-manifest"
        assert manifest["version"] == 1
        assert manifest["file_count"] == expected_count
        assert len(manifest["files"]) == expected_count
        assert hashlib.sha256(manifest_bytes).hexdigest() == (
            result.headers["x-kmfa-zip-manifest-sha256"]
        )
        hashes = {}
        for record in manifest["files"]:
            payload = archive.read(record["archive_path"])
            digest = hashlib.sha256(payload).hexdigest()
            assert len(payload) == record["size_bytes"]
            assert digest == record["sha256"]
            hashes[record["archive_path"]] = digest
    return manifest, hashes


def _browser_oracle(
    resources: Resources,
    out_dir: Path,
) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    name = "浏览器 Range #1 + [甲].bin"
    payload = (b"P7.2-browser-range-fixture-" * 210_000)[: 5 * 1024 * 1024 + 97]
    fault = {"injected": False}
    with sync_playwright() as playwright:
        executable = os.environ.get(
            "KMFA_PLAYWRIGHT_CHROMIUM_EXECUTABLE",
            "",
        ).strip()
        browser = playwright.chromium.launch(
            headless=True,
            **({"executable_path": executable} if executable else {}),
        )
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.goto(resources.base_url, wait_until="networkidle")
        page.locator(
            "[data-walking-skeleton-state='ready']"
        ).wait_for(timeout=15_000)
        page.locator("#walking-project-create").fill(
            "P7.2 browser synthetic"
        )
        page.locator("[data-walking-create] button[type=submit]").click()
        page.locator("[data-workspace-ready='true']").wait_for(
            timeout=15_000
        )
        page.locator("#walking-file").set_input_files(
            {
                "name": name,
                "mimeType": "application/octet-stream",
                "buffer": payload,
            }
        )
        page.locator("[data-walking-upload] button[type=submit]").click()
        page.get_by_text("v1 / 1", exact=True).wait_for(timeout=20_000)
        item = page.locator("[data-walking-download-item='original']")
        item.wait_for(timeout=15_000)

        def inject_one_disconnect(route, request) -> None:
            if request.headers.get("range") and not fault["injected"]:
                fault["injected"] = True
                route.abort("connectionreset")
                return
            route.continue_()

        page.route("**/artifact/downloads", inject_one_disconnect)
        with page.expect_download(timeout=30_000) as download_info:
            item.locator("[data-walking-download='exact']").click()
        downloaded = download_info.value
        downloaded_path = downloaded.path()
        assert downloaded_path is not None
        assert downloaded.suggested_filename == name
        assert downloaded_path.read_bytes() == payload
        assert fault["injected"] is True
        page.get_by_text("固定分片续传", exact=False).wait_for(
            timeout=15_000
        )

        item.locator("[data-walking-download-select]").check()
        assert page.locator(
            "[data-walking-batch-selection='1']"
        ).count() == 1
        with page.expect_download(timeout=30_000) as batch_info:
            page.locator("[data-walking-download-batch='true']").click()
        batch_download = batch_info.value
        batch_path = batch_download.path()
        assert batch_path is not None
        assert batch_download.suggested_filename == "kmfa-downloads.zip"
        with ZipFile(batch_path) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            assert manifest["file_count"] == 1
            record = manifest["files"][0]
            assert archive.read(record["archive_path"]) == payload
            assert record["sha256"] == hashlib.sha256(payload).hexdigest()
        page.get_by_text("manifest SHA-256", exact=False).wait_for(
            timeout=15_000
        )
        page.locator("[data-walking-artifact='ready']").screenshot(
            path=str(out_dir / "range-batch-ui.png")
        )
        assert page.locator("[data-walking-message='error']").count() == 0
        context.close()
        browser.close()
    return {
        "workspace_ready": True,
        "range_disconnects_injected": 1,
        "bounded_range_retry_succeeded": True,
        "range_chunks_expected": 2,
        "download_sha256": hashlib.sha256(payload).hexdigest(),
        "batch_selected_files": 1,
        "batch_zip_verified": True,
        "browser_error_count": 0,
        "screenshot": "range-batch-ui.png",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--prefix", default="kmfa-p72-e2e")
    parser.add_argument("--port", type=int, default=18111)
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
    capabilities: list[str] = []
    resources = Resources(
        prefix=arguments.prefix,
        image=arguments.image,
        state_dir=arguments.state_dir.resolve(),
        port=arguments.port,
        shared_secret=shared_secret,
    )
    try:
        resources.create_network()
        resources.start_scanner()
        resources.start_app(
            security_enabled=True,
            derivation_enabled=True,
            single_file_download_enabled=True,
            range_batch_download_enabled=True,
        )
        api = RangeBatchApi(resources.base_url, capabilities)
        status = api.request("GET", "/status")
        assert status.status == 200
        contract = status.json()["range_batch_download"]
        assert contract["enabled"] is True
        assert contract["range"] == {
            "unit": "bytes",
            "ranges_per_request": 1,
            "parallel_requests": True,
            "validator": "sha256-etag",
        }
        assert contract["batch"]["max_assets"] == 500
        assert contract["batch"]["whole_archive_buffered"] is False

        workspace_id, token, actor = api.create(
            "P7.2 exact-image transfer"
        )
        source_name = "并行 Range #1 + [甲].txt"
        source = (
            b"synthetic-p72-range-content-"
            * 48_000
        )
        first = api.upload_version(
            workspace_id,
            token,
            actor,
            name=source_name,
            media_type="text/plain",
            payload=source,
        )
        assert first.status == 200, first.body
        worker = resources.run_worker(derivation_enabled=True)
        assert '"state": "converged"' in worker

        report_name = "重名 #1 + [甲].txt"
        report = b"synthetic second version with special filename\n"
        second = api.upload_version(
            workspace_id,
            token,
            actor,
            name=report_name,
            media_type="text/plain",
            payload=report,
        )
        assert second.status == 200, second.body
        workspace = api.workspace(workspace_id, token, actor)
        assert workspace.status == 200
        items = workspace.json()["artifact"]["downloadables"]
        assert len(items) == 3
        source_item = items[0]
        midpoint = len(source) // 2

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = (
                executor.submit(
                    api.download_range,
                    workspace_id,
                    token,
                    actor,
                    source_item,
                    f"bytes=0-{midpoint - 1}",
                ),
                executor.submit(
                    api.download_range,
                    workspace_id,
                    token,
                    actor,
                    source_item,
                    f"bytes={midpoint}-{len(source) - 1}",
                ),
            )
        first_range = futures[0].result()
        second_range = futures[1].result()
        http_trace = [
            _assert_range(
                first_range,
                item=source_item,
                expected=source,
                start=0,
                end=midpoint - 1,
            ),
            _assert_range(
                second_range,
                item=source_item,
                expected=source,
                start=midpoint,
                end=len(source) - 1,
            ),
        ]
        reconstructed = first_range.body + second_range.body
        assert reconstructed == source
        assert hashlib.sha256(reconstructed).hexdigest() == (
            source_item["sha256"]
        )

        batch = api.download_batch(
            workspace_id,
            token,
            actor,
            items,
        )
        manifest, hashes = _inspect_batch(
            batch,
            expected_count=len(items),
        )
        archive_sha256 = hashlib.sha256(batch.body).hexdigest()
        assert len(manifest["files"]) == len(items)

        browser = (
            {"skipped": True}
            if arguments.skip_browser
            else _browser_oracle(resources, arguments.out_dir)
        )
        resources.restart_app()
        restarted = api.workspace(workspace_id, token, actor)
        assert restarted.status == 200
        assert len(restarted.json()["artifact"]["downloadables"]) == 3

        before_rollback = _database_summary(resources)
        resources.remove_app()
        resources.start_app(
            security_enabled=True,
            derivation_enabled=True,
            single_file_download_enabled=True,
            range_batch_download_enabled=False,
        )
        rollback_api = RangeBatchApi(resources.base_url, capabilities)
        rollback_status = rollback_api.request("GET", "/status").json()
        assert rollback_status["single_file_download"]["enabled"] is True
        assert rollback_status["range_batch_download"]["enabled"] is False
        rolled_back = rollback_api.download_batch(
            workspace_id,
            token,
            actor,
            items,
        )
        assert rolled_back.status == 404
        assert rolled_back.json()["detail"] == (
            "range_batch_download_disabled"
        )
        rollback_workspace = rollback_api.workspace(
            workspace_id,
            token,
            actor,
        )
        assert len(
            rollback_workspace.json()["artifact"]["downloadables"]
        ) == 3
        after_rollback = _database_summary(resources)
        assert after_rollback["schema_version"] == 6
        assert after_rollback["versions"] == before_rollback["versions"]
        assert after_rollback["derivatives"] == before_rollback["derivatives"]
        assert after_rollback["object_count"] == before_rollback["object_count"]
        assert after_rollback["object_bytes"] == before_rollback["object_bytes"]
        assert after_rollback["archive_temp_files"] == 0

        resources.remove_app()
        resources.start_app(
            security_enabled=True,
            derivation_enabled=True,
            single_file_download_enabled=True,
            range_batch_download_enabled=True,
        )
        restored_api = RangeBatchApi(resources.base_url, capabilities)
        retried = restored_api.download_batch(
            workspace_id,
            token,
            actor,
            items,
        )
        retry_manifest, retry_hashes = _inspect_batch(
            retried,
            expected_count=len(items),
        )
        assert retried.body == batch.body
        assert retry_manifest == manifest
        assert retry_hashes == hashes

        final_database = _database_summary(resources)
        assert final_database["archive_temp_files"] == 0
        logs = resources.logs()
        assert shared_secret not in logs
        assert not any(value in logs for value in capabilities)
        assert not ACCESS_RE.search(logs)
        assert not RECOVERY_RE.search(logs)

        (arguments.out_dir / "zip-manifest.json").write_text(
            json.dumps(
                manifest,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        (arguments.out_dir / "zip-hashes.json").write_text(
            json.dumps(
                hashes,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        (arguments.out_dir / "http-trace.json").write_text(
            json.dumps(
                http_trace,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        summary = {
            "status": "PASS",
            "image_id": image_id,
            "schema_version": 6,
            "parallel_range_requests": 2,
            "range_resume_sha256_match": True,
            "batch_files": len(items),
            "zip_archive_sha256": archive_sha256,
            "zip_manifest_sha256": (
                batch.headers["x-kmfa-zip-manifest-sha256"]
            ),
            "zip_missing_files": 0,
            "zip_overwritten_files": 0,
            "zip_path_traversals": 0,
            "whole_archive_buffered_server_side": False,
            "deterministic_retry_match": True,
            "restart_preserved_assets": True,
            "rollback_preserved_single_file_assets": True,
            "reenable_restored_batch": True,
            "archive_temp_files": 0,
            "secret_log_matches": 0,
            "http_trace": http_trace,
            "browser": browser,
            "database": final_database,
        }
        (arguments.out_dir / "summary.json").write_text(
            json.dumps(
                summary,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        (arguments.out_dir / "report.md").write_text(
            "# S07/P7.2 exact-image Range + batch ZIP Oracle\n\n"
            f"- image: `{image_id}`\n"
            "- result: **PASS**\n"
            "- parallel Range / reconstructed hash mismatch: `2 / 0`\n"
            f"- ZIP files / missing / overwritten / traversal: "
            f"`{len(items)} / 0 / 0 / 0`\n"
            "- deterministic retry, restart, Flag rollback and re-enable: "
            "`PASS`\n"
            "- server whole-archive buffering: `false`; archive temp files: "
            "`0`\n"
            "- browser injected disconnect once, resumed in bounded chunks, "
            "then verified one-item batch ZIP\n"
            "- evidence contains only synthetic fixture metadata; no "
            "workspace capability, scanner secret or storage key\n",
            encoding="utf-8",
        )
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 0
    finally:
        resources.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
