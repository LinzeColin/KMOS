#!/usr/bin/env python3
"""S07/P7.1 exact-image single-file download Oracle.

The flow uses only synthetic files. Workspace capabilities remain in memory
and are never written to the evidence directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

from file_security_flow import (
    ACCESS_RE,
    RECOVERY_RE,
    Api,
    HttpResult,
    Resources,
    _run,
)

API_PREFIX = "/public-api/walking-skeleton/v1"
PREFIX_RE = re.compile(r"^kmfa-p71-[a-z0-9-]{1,32}$")
PROCESSOR = "kmfa-safe-text-extract/1.0.0"


class DownloadApi(Api):
    def __init__(self, base_url: str, capabilities: list[str]) -> None:
        super().__init__(base_url, capabilities)
        self.upload_sequence = 0

    def upload_version(
        self,
        workspace_id: str,
        token: str,
        actor: dict[str, str],
        *,
        name: str,
        media_type: str,
        payload: bytes,
    ) -> HttpResult:
        self.upload_sequence += 1
        return self.request(
            "PUT",
            f"/workspaces/{workspace_id}/artifact",
            body=payload,
            headers={
                **self.auth(token, actor),
                "Content-Type": media_type,
                "X-KMFA-Filename": quote(name, safe=""),
                "Idempotency-Key": (
                    "p71-final-image-upload-"
                    f"{self.upload_sequence:06d}"
                ),
            },
        )

    def download_asset(
        self,
        workspace_id: str,
        token: str | None,
        actor: dict[str, str],
        item: dict[str, Any],
    ) -> HttpResult:
        headers = {
            **actor,
            "Content-Type": "application/json",
        }
        if token is not None:
            headers.update(self.auth(token, actor))
        return self.request(
            "POST",
            f"/workspaces/{workspace_id}/artifact/downloads",
            body=json.dumps(
                {"kind": item["kind"], "asset_id": item["id"]}
            ).encode(),
            headers=headers,
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
        "'download_audits':c.execute("
        "\"SELECT COUNT(*) FROM audit_events "
        "WHERE action='artifact_download'\").fetchone()[0],"
        "'object_count':len(list((root/'objects').glob('*.blob'))),"
        "'object_bytes':sum(p.stat().st_size "
        "for p in (root/'objects').glob('*.blob'))"
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


def _disposition_name(value: str) -> str:
    marker = "filename*=utf-8''"
    if marker in value:
        return unquote(value.split(marker, 1)[1])
    match = re.search(r'filename="([^"]+)"', value)
    assert match is not None
    return match.group(1)


def _assert_download(
    result: HttpResult,
    item: dict[str, Any],
    expected: bytes,
) -> dict[str, Any]:
    assert result.status == 200, result.body
    assert result.body == expected
    assert result.headers["x-content-type-options"] == "nosniff"
    assert result.headers["cache-control"] == "private, no-store"
    assert result.headers["content-disposition"].startswith("attachment;")
    assert _disposition_name(result.headers["content-disposition"]) == item[
        "name"
    ]
    assert result.headers["content-type"].split(";", 1)[0] == item[
        "media_type"
    ]
    assert result.headers["x-kmfa-artifact-sha256"] == item["sha256"]
    assert result.headers["x-kmfa-artifact-size"] == str(item["size_bytes"])
    assert result.headers["x-kmfa-artifact-media-type"] == item["media_type"]
    assert result.headers["x-kmfa-artifact-kind"] == item["kind"]
    assert result.headers["x-kmfa-artifact-id"] == item["id"]
    assert (
        result.headers["x-kmfa-source-artifact-version"]
        == item["source"]["artifact_version_id"]
    )
    assert hashlib.sha256(result.body).hexdigest() == item["sha256"]
    if item["kind"] == "derivative":
        processor = item["source"]["processor"]
        assert (
            result.headers["x-kmfa-processor"]
            == f"{processor['name']}/{processor['version']}"
        )
    elif item["source"]["operation_id"] is not None:
        assert (
            result.headers["x-kmfa-source-operation"]
            == item["source"]["operation_id"]
        )
    return {
        "kind": item["kind"],
        "status": result.status,
        "media_type": item["media_type"],
        "size_bytes": len(result.body),
        "sha256": hashlib.sha256(result.body).hexdigest(),
        "content_disposition": "attachment",
        "source_kind": item["source"]["kind"],
    }


def _replace_original(
    resources: Resources,
    artifact_version_id: str,
    replacement: bytes,
) -> None:
    assert re.fullmatch(r"[A-Za-z0-9_-]{20,200}", artifact_version_id)
    command = (
        "import pathlib,sqlite3;"
        "root=pathlib.Path('/var/lib/kmfa/state/walking-skeleton');"
        "c=sqlite3.connect(root/'walking_skeleton.sqlite3');"
        "key=c.execute("
        "\"SELECT storage_key FROM artifact_versions "
        "WHERE artifact_version_id=?\","
        f"('{artifact_version_id}',)"
        ").fetchone()[0];c.close();"
        f"(root/'objects'/key).write_bytes(bytes.fromhex('{replacement.hex()}'))"
    )
    _run(
        "docker",
        "exec",
        resources.app,
        "python3",
        "-c",
        command,
    )


def _browser_oracle(
    resources: Resources,
    out_dir: Path,
) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    text_name = "浏览器 预算 #1[甲].txt"
    text_payload = b"P7.1 browser exact text\n"
    report_name = "浏览器 财务报告[终版].pdf"
    report_payload = b"%PDF-1.7\nsynthetic browser report\n%%EOF\n"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.goto(resources.base_url, wait_until="networkidle")
        page.locator(
            "[data-walking-skeleton-state='ready']"
        ).wait_for(timeout=15_000)
        page.locator("#walking-project-create").fill(
            "P7.1 browser synthetic"
        )
        page.locator("[data-walking-create] button[type=submit]").click()
        page.locator("[data-workspace-ready='true']").wait_for(
            timeout=15_000
        )

        page.locator("#walking-file").set_input_files(
            {
                "name": text_name,
                "mimeType": "text/plain",
                "buffer": text_payload,
            }
        )
        page.locator("[data-walking-upload] button[type=submit]").click()
        page.get_by_text("v1 / 1", exact=True).wait_for(timeout=15_000)
        worker = resources.run_worker(derivation_enabled=True)
        assert '"state": "converged"' in worker
        page.locator("[data-walking-refresh='true']").click()
        page.locator("[data-walking-download-list='ready']").wait_for(
            timeout=15_000
        )

        page.locator("#walking-file").set_input_files(
            {
                "name": report_name,
                "mimeType": "application/pdf",
                "buffer": report_payload,
            }
        )
        page.locator("[data-walking-upload] button[type=submit]").click()
        page.get_by_text("v2 / 2", exact=True).wait_for(timeout=15_000)
        items = page.locator("[data-download-asset-id]")
        assert items.count() == 3
        assert (
            page.locator("[data-walking-download-item='original']").count()
            == 2
        )
        assert (
            page.locator(
                "[data-walking-download-item='derivative']"
            ).count()
            == 1
        )
        report_item = page.locator(
            "[data-walking-download-item='original']"
        ).filter(has_text=report_name)
        report_item.get_by_text("application/pdf", exact=False).wait_for()
        with page.expect_download(timeout=15_000) as download_info:
            report_item.locator(
                "[data-walking-download='exact']"
            ).click()
        downloaded = download_info.value
        downloaded_path = downloaded.path()
        assert downloaded_path is not None
        assert downloaded.suggested_filename == report_name
        assert downloaded_path.read_bytes() == report_payload
        page.get_by_text(
            "类型、大小、来源与 SHA-256 均一致",
            exact=False,
        ).wait_for(timeout=15_000)
        page.locator("[data-walking-artifact='ready']").screenshot(
            path=str(out_dir / "download-ui.png")
        )
        assert page.locator("[data-walking-message='error']").count() == 0
        context.close()
        browser.close()
    return {
        "workspace_ready": True,
        "visible_download_items": 3,
        "visible_originals": 2,
        "visible_derivatives": 1,
        "unicode_report_filename_preserved": True,
        "browser_download_sha256": hashlib.sha256(
            report_payload
        ).hexdigest(),
        "browser_metadata_and_hash_check": True,
        "browser_error_count": 0,
        "screenshot": "download-ui.png",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--prefix", default="kmfa-p71-e2e")
    parser.add_argument("--port", type=int, default=18110)
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
        )
        api = DownloadApi(resources.base_url, capabilities)
        status = api.request("GET", "/status")
        assert status.status == 200
        contract = status.json()["single_file_download"]
        assert contract == {
            "enabled": True,
            "selector_transport": "authorized-json-body",
            "asset_kinds": ["original", "derivative"],
            "content_disposition": "attachment-only",
            "legacy_latest_original_fallback": True,
            "public_snapshot_access": "deferred-to-s08",
        }

        workspace_id, token, actor = api.create(
            "P7.1 exact-image downloads"
        )
        source_name = "预算 #1 + 复核[甲].txt"
        source = b"synthetic exact-image text\n"
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

        report_name = "财务报告 终版[1].pdf"
        report = b"%PDF-1.7\nsynthetic stored report\n%%EOF\n"
        second = api.upload_version(
            workspace_id,
            token,
            actor,
            name=report_name,
            media_type="application/pdf",
            payload=report,
        )
        assert second.status == 200, second.body
        assert second.json()["artifact"]["security"]["state"] == (
            "attachment_only"
        )

        workspace = api.workspace(workspace_id, token, actor)
        assert workspace.status == 200
        items = workspace.json()["artifact"]["downloadables"]
        assert [item["kind"] for item in items] == [
            "original",
            "derivative",
            "original",
        ]
        assert [item["name"] for item in items if item["kind"] == "original"] == [
            source_name,
            report_name,
        ]
        expected_by_name = {
            source_name: source,
            "kmfa-safe-text-preview.txt": source,
            report_name: report,
        }
        http_trace = [
            _assert_download(
                api.download_asset(
                    workspace_id,
                    token,
                    actor,
                    item,
                ),
                item,
                expected_by_name[item["name"]],
            )
            for item in items
        ]

        attacker_workspace, attacker_token, attacker_actor = api.create(
            "P7.1 other workspace"
        )
        idor = api.download_asset(
            attacker_workspace,
            attacker_token,
            attacker_actor,
            items[0],
        )
        assert idor.status == 404
        assert idor.json()["detail"] == "artifact_download_not_found"
        attacker_source = b"%PDF-1.7\nsynthetic unlisted workspace\n%%EOF\n"
        attacker_upload = api.upload_version(
            attacker_workspace,
            attacker_token,
            attacker_actor,
            name="unlisted.pdf",
            media_type="application/pdf",
            payload=attacker_source,
        )
        assert attacker_upload.status == 200
        attacker_item = api.workspace(
            attacker_workspace,
            attacker_token,
            attacker_actor,
        ).json()["artifact"]["downloadables"][0]
        unauthenticated = api.download_asset(
            attacker_workspace,
            None,
            api._actor(),
            attacker_item,
        )
        assert unauthenticated.status == 404
        assert unauthenticated.json()["detail"] == "workspace_not_found"

        before_fault = _database_summary(resources)
        _replace_original(resources, items[-1]["id"], b"tampered")
        integrity = api.download_asset(
            workspace_id,
            token,
            actor,
            items[-1],
        )
        assert integrity.status == 503
        assert integrity.json()["detail"] == "artifact_integrity_failed"
        _replace_original(resources, items[-1]["id"], report)
        after_fault = _database_summary(resources)
        assert after_fault["object_count"] == before_fault["object_count"]
        assert after_fault["object_bytes"] == before_fault["object_bytes"]

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
            single_file_download_enabled=False,
        )
        rollback_api = DownloadApi(resources.base_url, capabilities)
        rollback_status = rollback_api.request("GET", "/status").json()
        assert rollback_status["single_file_download"]["enabled"] is False
        rolled_back = rollback_api.download_asset(
            attacker_workspace,
            attacker_token,
            attacker_actor,
            items[-1],
        )
        assert rolled_back.status == 404
        assert rolled_back.json()["detail"] == (
            "single_file_download_disabled"
        )
        rollback_workspace = rollback_api.workspace(
            workspace_id,
            token,
            actor,
        )
        assert "downloadables" not in rollback_workspace.json()["artifact"]
        legacy = rollback_api.download(workspace_id, token, actor)
        assert legacy.status == 200
        assert legacy.body == report
        assert legacy.headers["content-disposition"].startswith("attachment;")
        after_rollback = _database_summary(resources)
        assert after_rollback["schema_version"] == 6
        assert after_rollback["versions"] == before_rollback["versions"]
        assert after_rollback["derivatives"] == before_rollback["derivatives"]
        assert after_rollback["object_count"] == before_rollback["object_count"]
        assert after_rollback["object_bytes"] == before_rollback["object_bytes"]

        resources.remove_app()
        resources.start_app(
            security_enabled=True,
            derivation_enabled=True,
            single_file_download_enabled=True,
        )
        restored_api = DownloadApi(resources.base_url, capabilities)
        restored = restored_api.download_asset(
            workspace_id,
            token,
            actor,
            items[-1],
        )
        _assert_download(restored, items[-1], report)

        logs = resources.logs()
        assert shared_secret not in logs
        assert not any(value in logs for value in capabilities)
        assert not ACCESS_RE.search(logs)
        assert not RECOVERY_RE.search(logs)

        summary = {
            "status": "PASS",
            "image_id": image_id,
            "schema_version": 6,
            "downloadable_assets": 3,
            "original_versions": 2,
            "derivatives": 1,
            "stored_report_files": 1,
            "byte_or_metadata_mismatches": 0,
            "unauthorized_downloads": 0,
            "high_risk_inline_downloads": 0,
            "integrity_faults_blocked": 1,
            "selector_ids_in_url": 0,
            "restart_preserved_assets": True,
            "rollback_preserved_assets": True,
            "reenable_restored_exact_download": True,
            "secret_log_matches": 0,
            "http_trace": http_trace,
            "browser": browser,
            "database": after_rollback,
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
        (arguments.out_dir / "report.md").write_text(
            "# S07/P7.1 exact-image single-file download Oracle\n\n"
            f"- image: `{image_id}`\n"
            "- result: **PASS**\n"
            "- originals / derivatives / stored reports: `2 / 1 / 1`\n"
            "- byte or metadata mismatches: `0`\n"
            "- unauthorized downloads: `0`; selector IDs in URLs: `0`\n"
            "- high-risk inline responses: `0`; integrity fault blocked: `1`\n"
            "- restart, Flag rollback and re-enable preserved all assets\n"
            "- evidence contains no workspace capability, scanner secret, "
            "object key or private report body\n",
            encoding="utf-8",
        )
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 0
    finally:
        resources.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
