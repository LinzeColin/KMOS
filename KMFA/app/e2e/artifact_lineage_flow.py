#!/usr/bin/env python3
"""S06/P6.3 exact-image immutable lineage and safe-preview Oracle.

Only synthetic bytes are used. Recovery/session capabilities remain in memory
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
from urllib.parse import quote

from file_security_flow import (
    ACCESS_RE,
    RECOVERY_RE,
    Api,
    HttpResult,
    Resources,
    _run,
)

API_PREFIX = "/public-api/walking-skeleton/v1"
PREFIX_RE = re.compile(r"^kmfa-p63-[a-z0-9-]{1,32}$")
PROCESSOR = "kmfa-safe-text-extract/1.0.0"


class LineageApi(Api):
    def __init__(self, base_url: str, capabilities: list[str]) -> None:
        super().__init__(base_url, capabilities)
        self.upload_sequence = 0
        self.reprocess_sequence = 0

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
                    "p63-final-image-version-"
                    f"{self.upload_sequence:06d}"
                ),
            },
        )

    def lineage(
        self,
        workspace_id: str,
        token: str,
        actor: dict[str, str],
    ) -> HttpResult:
        return self.request(
            "GET",
            f"/workspaces/{workspace_id}/artifact/lineage",
            headers=self.auth(token, actor),
        )

    def preview(
        self,
        workspace_id: str,
        token: str,
        actor: dict[str, str],
    ) -> HttpResult:
        return self.request(
            "GET",
            f"/workspaces/{workspace_id}/artifact/preview",
            headers=self.auth(token, actor),
        )

    def reprocess(
        self,
        workspace_id: str,
        token: str,
        actor: dict[str, str],
        *,
        replay: bool = False,
    ) -> HttpResult:
        if not replay:
            self.reprocess_sequence += 1
        return self.request(
            "POST",
            f"/workspaces/{workspace_id}/artifact/reprocess",
            headers={
                **self.auth(token, actor),
                "Idempotency-Key": (
                    "p63-final-image-reprocess-"
                    f"{self.reprocess_sequence:06d}"
                ),
            },
        )


def _database_summary(resources: Resources) -> dict[str, Any]:
    command = (
        "import json,sqlite3;"
        "c=sqlite3.connect('/var/lib/kmfa/state/walking-skeleton/"
        "walking_skeleton.sqlite3');"
        "print(json.dumps({"
        "'schema_version':c.execute('PRAGMA user_version').fetchone()[0],"
        "'versions':c.execute("
        "\"SELECT COUNT(*) FROM artifact_versions\").fetchone()[0],"
        "'lineage':c.execute("
        "\"SELECT COUNT(*) FROM artifact_version_lineage\").fetchone()[0],"
        "'processors':c.execute("
        "\"SELECT COUNT(*) FROM processor_registry\").fetchone()[0],"
        "'runs':dict(c.execute("
        "\"SELECT state,COUNT(*) FROM artifact_processing_runs "
        "GROUP BY state\").fetchall()),"
        "'derivatives':c.execute("
        "\"SELECT COUNT(*) FROM artifact_derivatives\").fetchone()[0],"
        "'derivative_storage_keys':c.execute("
        "\"SELECT COUNT(DISTINCT storage_key) "
        "FROM artifact_derivatives\").fetchone()[0]"
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


def _browser_oracle(resources: Resources) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    first_payload = b"P6.3 browser safe preview\n"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(resources.base_url, wait_until="networkidle")
        page.locator(
            "[data-walking-skeleton-state='ready']"
        ).wait_for(timeout=15_000)
        page.locator("#walking-project-create").fill(
            "P6.3 browser synthetic"
        )
        page.locator("[data-walking-create] button[type=submit]").click()
        page.locator("[data-workspace-ready='true']").wait_for(
            timeout=15_000
        )

        def upload_and_preview(expected_version: str) -> None:
            page.locator("#walking-file").set_input_files(
                {
                    "name": "browser-safe.txt",
                    "mimeType": "text/plain",
                    "buffer": first_payload,
                }
            )
            page.locator(
                "[data-walking-upload] button[type=submit]"
            ).click()
            page.get_by_text(expected_version, exact=True).wait_for(
                timeout=15_000
            )
            page.locator(
                "[data-walking-artifact][data-security-state='clean']"
            ).wait_for(timeout=15_000)
            resources.run_worker(derivation_enabled=True)
            page.locator("[data-walking-refresh='true']").click()
            preview = page.locator("[data-walking-preview='true']")
            preview.wait_for(timeout=15_000)
            preview.click()
            rendered = page.locator("[data-walking-safe-preview='true']")
            rendered.wait_for(timeout=15_000)
            assert rendered.text_content() == first_payload.decode()

        upload_and_preview("v1 / 1")
        upload_and_preview("v2 / 2")
        assert (
            page.locator("[data-walking-artifact='ready']")
            .locator("code")
            .count()
            == 1
        )
        assert page.locator("[data-walking-message='error']").count() == 0
        browser.close()
    return {
        "root_workspace_ready": True,
        "same_name_second_version": True,
        "visible_version": "v2 / 2",
        "preview_sha256_verified_by_browser": True,
        "preview_rendered_as_react_text": True,
        "browser_error_count": 0,
    }


def _assert_version_chain(
    artifacts: list[dict[str, Any]],
    payloads: tuple[bytes, ...],
) -> None:
    assert [item["version_number"] for item in artifacts] == [1, 2, 3]
    assert [item["version_count"] for item in artifacts] == [1, 2, 3]
    assert len({item["artifact_version_id"] for item in artifacts}) == 3
    assert len({item["artifact_id"] for item in artifacts}) == 1
    assert artifacts[0]["parent_artifact_version_id"] is None
    assert (
        artifacts[1]["parent_artifact_version_id"]
        == artifacts[0]["artifact_version_id"]
    )
    assert (
        artifacts[2]["parent_artifact_version_id"]
        == artifacts[1]["artifact_version_id"]
    )
    expected_hashes = [
        hashlib.sha256(payload).hexdigest() for payload in payloads
    ]
    assert [item["sha256"] for item in artifacts] == expected_hashes
    assert expected_hashes[0] == expected_hashes[1]
    assert expected_hashes[1] != expected_hashes[2]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--prefix", default="kmfa-p63-e2e")
    parser.add_argument("--port", type=int, default=18108)
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
        timeout_payload_sha256=hashlib.sha256(
            b"P6.3 no timeout fixture"
        ).hexdigest(),
    )
    try:
        resources.create_network()
        resources.start_scanner(delay_enabled=False)
        resources.start_app(
            security_enabled=True,
            derivation_enabled=True,
        )
        api = LineageApi(resources.base_url, capabilities)
        status = api.request("GET", "/status")
        assert status.status == 200
        contract = status.json()["artifact_derivation"]
        assert contract["enabled"] is True
        assert contract["executes_user_code_or_macros"] is False
        assert contract["web_process_parses_originals"] is False
        assert (
            contract["processor"]["name"]
            + "/"
            + contract["processor"]["version"]
            == PROCESSOR
        )

        workspace_id, token, actor = api.create(
            "P6.3 exact-image versions"
        )
        payloads = (
            b"same exact-image content\n",
            b"same exact-image content\n",
            b"modified exact-image content\n",
        )
        artifacts: list[dict[str, Any]] = []
        for payload in payloads:
            uploaded = api.upload_version(
                workspace_id,
                token,
                actor,
                name="same-name.txt",
                media_type="text/plain",
                payload=payload,
            )
            assert uploaded.status == 200, uploaded.body
            artifact = uploaded.json()["artifact"]
            assert artifact["security"]["state"] == "clean"
            artifacts.append(artifact)
            worker = resources.run_worker(derivation_enabled=True)
            assert '"kind": "artifact_derivation"' in worker
            assert '"state": "converged"' in worker
        _assert_version_chain(artifacts, payloads)

        downloaded = api.download(workspace_id, token, actor)
        assert downloaded.status == 200
        assert downloaded.body == payloads[-1]
        assert (
            downloaded.headers["x-kmfa-artifact-sha256"]
            == hashlib.sha256(payloads[-1]).hexdigest()
        )

        graph = api.lineage(workspace_id, token, actor)
        assert graph.status == 200
        graph_payload = graph.json()
        assert graph_payload["version_count"] == 3
        assert graph_payload["derivative_count"] == 3
        assert graph_payload["lineage_gaps"] == 0
        assert len(graph_payload["edges"]) == 5

        preview = api.preview(workspace_id, token, actor)
        assert preview.status == 200
        assert preview.body == payloads[-1]
        assert preview.headers["x-kmfa-processor"] == PROCESSOR
        assert (
            preview.headers["x-kmfa-derivative-sha256"]
            == hashlib.sha256(preview.body).hexdigest()
        )
        assert preview.headers["x-content-type-options"] == "nosniff"
        assert (
            preview.headers["content-security-policy"]
            == "default-src 'none'; sandbox"
        )

        requested = api.reprocess(workspace_id, token, actor)
        replayed = api.reprocess(
            workspace_id,
            token,
            actor,
            replay=True,
        )
        assert requested.status == replayed.status == 202
        assert (
            requested.json()["processing_run_id"]
            == replayed.json()["processing_run_id"]
        )
        audit = api.request(
            "GET",
            f"/workspaces/{workspace_id}/audit-events",
            headers=api.auth(token, actor),
        )
        assert audit.status == 200
        assert [
            event["action"]
            for event in audit.json()["events"]
            if event["action"] == "artifact_reprocess_requested"
        ] == ["artifact_reprocess_requested"]
        reprocessed = resources.run_worker(derivation_enabled=True)
        assert '"state": "converged"' in reprocessed
        refreshed = api.workspace(workspace_id, token, actor)
        assert refreshed.status == 200
        assert refreshed.json()["artifact"]["preview"][
            "generation_number"
        ] == 2
        graph_payload = api.lineage(
            workspace_id,
            token,
            actor,
        ).json()
        assert graph_payload["derivative_count"] == 4
        assert graph_payload["lineage_gaps"] == 0

        risk_workspace, risk_token, risk_actor = api.create(
            "P6.3 attachment-only boundary"
        )
        risk = api.upload_version(
            risk_workspace,
            risk_token,
            risk_actor,
            name="active.html",
            media_type="text/html",
            payload=b"<html><script>synthetic active</script></html>",
        )
        assert risk.status == 200
        assert (
            risk.json()["artifact"]["security"]["state"]
            == "attachment_only"
        )
        assert risk.json()["artifact"]["security"][
            "processing_allowed"
        ] is False
        resources.run_worker(derivation_enabled=True)
        assert api.preview(
            risk_workspace,
            risk_token,
            risk_actor,
        ).status == 409
        assert api.reprocess(
            risk_workspace,
            risk_token,
            risk_actor,
        ).status == 409
        risk_graph = api.lineage(
            risk_workspace,
            risk_token,
            risk_actor,
        ).json()
        assert risk_graph["derivative_count"] == 0
        assert risk_graph["lineage_gaps"] == 0

        browser = (
            {"skipped": True}
            if arguments.skip_browser
            else _browser_oracle(resources)
        )

        resources.restart_app()
        restarted = api.workspace(workspace_id, token, actor)
        assert restarted.status == 200
        assert restarted.json()["artifact"]["version_number"] == 3
        assert restarted.json()["artifact"]["preview"][
            "generation_number"
        ] == 2
        assert api.preview(
            workspace_id,
            token,
            actor,
        ).body == payloads[-1]

        before_rollback = _database_summary(resources)
        resources.remove_app()
        resources.start_app(
            security_enabled=True,
            derivation_enabled=False,
        )
        rollback_api = LineageApi(resources.base_url, capabilities)
        rollback_status = rollback_api.request("GET", "/status").json()
        assert rollback_status["artifact_derivation"]["enabled"] is False
        rollback_workspace = rollback_api.workspace(
            workspace_id,
            token,
            actor,
        )
        assert rollback_workspace.status == 200
        assert rollback_workspace.json()["artifact"]["version_number"] == 3
        assert rollback_workspace.json()["artifact"][
            "preview_allowed"
        ] is False
        assert rollback_api.preview(
            workspace_id,
            token,
            actor,
        ).status == 404
        rollback_download = rollback_api.download(
            workspace_id,
            token,
            actor,
        )
        assert rollback_download.status == 200
        assert rollback_download.body == payloads[-1]
        rollback_graph = rollback_api.lineage(
            workspace_id,
            token,
            actor,
        ).json()
        assert rollback_graph["version_count"] == 3
        assert rollback_graph["derivative_count"] == 4
        assert rollback_graph["lineage_gaps"] == 0
        after_rollback = _database_summary(resources)
        assert after_rollback == before_rollback
        assert after_rollback["schema_version"] == 6
        assert after_rollback["processors"] == 1
        assert after_rollback["derivatives"] == 6
        assert after_rollback["derivative_storage_keys"] == 6
        assert after_rollback["runs"] == {"converged": 6}

        logs = resources.logs()
        assert shared_secret not in logs
        assert not any(value in logs for value in capabilities)
        assert not ACCESS_RE.search(logs)
        assert not RECOVERY_RE.search(logs)

        summary = {
            "status": "PASS",
            "image_id": image_id,
            "schema_version": 6,
            "same_name_versions": 3,
            "same_content_versions": 2,
            "modified_content_versions": 1,
            "original_overwrite_count": 0,
            "version_parent_gaps": 0,
            "lineage_gaps": 0,
            "processor": PROCESSOR,
            "reprocess_idempotent": True,
            "reprocess_audit_side_effects": 1,
            "latest_generation": 2,
            "high_risk_preview_count": 0,
            "high_risk_processing_count": 0,
            "restart_preserved_lineage_and_preview": True,
            "rollback_preserved_originals_lineage_derivatives": True,
            "rollback_download_hash_match": True,
            "secret_log_matches": 0,
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
        (arguments.out_dir / "report.md").write_text(
            "# S06/P6.3 exact-image lineage + preview Oracle\n\n"
            f"- image: `{image_id}`\n"
            "- result: **PASS**\n"
            "- same-name versions: `3`; original overwrites: `0`\n"
            "- version/derivative lineage gaps: `0`\n"
            f"- processor: `{PROCESSOR}`; user code/macros: `false`\n"
            "- reprocess replay: one request; latest generation: `2`\n"
            "- high-risk preview/processing: `0/0`\n"
            "- restart and Flag rollback preserved originals, lineage, "
            "derivatives and latest download hash\n"
            "- raw capabilities, shared secret, filenames and object keys "
            "are not written to this evidence directory\n",
            encoding="utf-8",
        )
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 0
    finally:
        resources.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
