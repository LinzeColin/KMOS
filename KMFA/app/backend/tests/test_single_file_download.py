"""S07/P7.1 exact, attachment-only single-file download contracts."""

from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import quote, unquote

import pytest
from app import anti_abuse
from app import walking_skeleton as skeleton
from app.artifact_lineage import (
    PROCESSOR_NAME,
    PROCESSOR_VERSION,
    run_artifact_derivation_once,
)
from app.file_security import FileSecurityClient, ScanOutcome
from app.main import app
from fastapi.testclient import TestClient

BASE = "/public-api/walking-skeleton/v1"
SECRET = "p71-state-test-shared-secret-32-bytes-minimum"


@pytest.fixture
def download_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, TestClient]:
    state = tmp_path / "walking-state"
    monkeypatch.setenv("KMFA_WALKING_SKELETON_ENABLED", "1")
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(state))
    monkeypatch.setenv("KMFA_SINGLE_FILE_DOWNLOAD_ENABLED", "1")
    monkeypatch.setenv("KMFA_FILE_SECURITY_ENABLED", "1")
    monkeypatch.setenv("KMFA_ARTIFACT_DERIVATION_ENABLED", "1")
    monkeypatch.setenv(
        "KMFA_FILE_SCANNER_URL",
        "http://127.0.0.1:18099/scan",
    )
    monkeypatch.setenv("KMFA_FILE_SCANNER_SHARED_SECRET", SECRET)
    monkeypatch.setenv("KMFA_FILE_SCANNER_TIMEOUT_SECONDS", "0.1")
    monkeypatch.setenv("KMFA_FILE_SCAN_LEASE_SECONDS", "1")
    monkeypatch.setenv("KMFA_FILE_SCAN_RETRY_DELAY_SECONDS", "0")
    monkeypatch.setenv("KMFA_FILE_SCAN_MAX_ATTEMPTS", "3")
    monkeypatch.setenv("KMFA_CONSISTENCY_STATE_MODE", "recoverable-v1")
    monkeypatch.setenv("KMFA_LIFECYCLE_MODE", "paused")
    monkeypatch.delenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", raising=False)
    monkeypatch.delenv("KMFA_STRUCTURED_DATABASE_MODE", raising=False)
    monkeypatch.delenv("KMFA_STRUCTURED_DATABASE_URL", raising=False)
    monkeypatch.delenv("KMFA_ARTIFACT_STORAGE_MODE", raising=False)
    return state, TestClient(
        app,
        base_url="https://testserver",
        headers={"Origin": "https://testserver"},
    )


def _outcome(*, verdict: str, reason: str, media_type: str) -> ScanOutcome:
    return ScanOutcome(
        verdict=verdict,
        reason_code=reason,
        detected_media_type=media_type,
        scanner_engine="kmfa-bounded-content-firewall",
        scanner_version="1.0",
        policy_version="kmfa-upload-security-v1",
    )


def _create(client: TestClient, name: str) -> str:
    response = client.post(f"{BASE}/workspaces", json={"project_name": name})
    assert response.status_code == 201, response.text
    return str(response.json()["workspace"]["workspace_id"])


def _upload(
    client: TestClient,
    workspace_id: str,
    *,
    body: bytes,
    name: str,
    media_type: str,
    key: str,
) -> dict:
    response = client.put(
        f"{BASE}/workspaces/{workspace_id}/artifact",
        content=body,
        headers={
            "Content-Type": media_type,
            "Idempotency-Key": key,
            "X-KMFA-Filename": quote(name, safe=""),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["artifact"]


def _download(
    client: TestClient,
    workspace_id: str,
    item: dict,
):
    return client.post(
        f"{BASE}/workspaces/{workspace_id}/artifact/downloads",
        json={"kind": item["kind"], "asset_id": item["id"]},
    )


def _assert_attachment(
    response,
    *,
    item: dict,
    expected: bytes,
) -> None:
    assert response.status_code == 200, response.text
    assert response.content == expected
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-robots-tag"] == "noindex, nofollow, noarchive"
    assert response.headers["x-kmfa-artifact-sha256"] == item["sha256"]
    assert response.headers["x-kmfa-artifact-size"] == str(item["size_bytes"])
    assert response.headers["x-kmfa-artifact-media-type"] == item["media_type"]
    assert response.headers["x-kmfa-artifact-kind"] == item["kind"]
    assert response.headers["x-kmfa-artifact-id"] == item["id"]
    assert response.headers["content-type"].split(";", 1)[0] == item["media_type"]
    disposition = response.headers["content-disposition"]
    assert disposition.lower().startswith("attachment;")
    if "filename*=utf-8''" in disposition:
        encoded_name = disposition.split("filename*=utf-8''", 1)[1]
        assert unquote(encoded_name) == item["name"]
    else:
        assert f'filename="{item["name"]}"' in disposition


def test_single_file_download_flag_defaults_and_typos_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    state = tmp_path / "walking-state"
    monkeypatch.setenv("KMFA_WALKING_SKELETON_ENABLED", "1")
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(state))
    monkeypatch.setenv("KMFA_LIFECYCLE_MODE", "paused")
    monkeypatch.delenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", raising=False)
    client = TestClient(
        app,
        base_url="https://testserver",
        headers={"Origin": "https://testserver"},
    )

    for value in (None, "", "enable-ish", "truthy"):
        if value is None:
            monkeypatch.delenv(
                "KMFA_SINGLE_FILE_DOWNLOAD_ENABLED",
                raising=False,
            )
        else:
            monkeypatch.setenv("KMFA_SINGLE_FILE_DOWNLOAD_ENABLED", value)
        contract = client.get(f"{BASE}/status").json()["single_file_download"]
        assert contract == {
            "enabled": False,
            "selector_transport": "authorized-json-body",
            "asset_kinds": ["original", "derivative"],
            "content_disposition": "attachment-only",
            "legacy_latest_original_fallback": True,
            "public_snapshot_access": "deferred-to-s08",
        }
    classified = anti_abuse._classify(
        "POST",
        f"{BASE}/workspaces/ws_{'x' * 22}/artifact/downloads",
    )
    assert classified == ("export", f"ws_{'x' * 22}")
    repo = Path(__file__).resolve().parents[4]
    local_compose = (repo / "KMFA/app/docker-compose.yml").read_text(
        encoding="utf-8"
    )
    coolify_compose = (
        repo / "KMFA/deploy/coolify/docker-compose.yml"
    ).read_text(encoding="utf-8")
    env_example = (
        repo / "KMFA/deploy/coolify/.env.example"
    ).read_text(encoding="utf-8")
    workflow = (repo / ".github/workflows/app-e2e.yml").read_text(
        encoding="utf-8"
    )
    for compose in (local_compose, coolify_compose):
        assert (
            "KMFA_SINGLE_FILE_DOWNLOAD_ENABLED:"
            ' "${KMFA_SINGLE_FILE_DOWNLOAD_ENABLED:-0}"'
        ) in compose
    assert "KMFA_SINGLE_FILE_DOWNLOAD_ENABLED=0" in env_example
    assert "KMFA/app/e2e/single_file_download_flow.py" in workflow
    assert "single-file-download-e2e/" in workflow
    assert skeleton._clean_media_type(
        "text/plain; charset=UTF-8"
    ) == "text/plain"
    assert skeleton._clean_media_type(
        "application/中文"
    ) == "application/octet-stream"


def test_exact_original_derivative_and_stored_report_downloads_match_metadata(
    download_runtime: tuple[Path, TestClient],
    monkeypatch: pytest.MonkeyPatch,
):
    state, owner = download_runtime

    def scan(_self, _source, *, filename: str, **_kwargs):
        if filename.endswith(".txt"):
            return _outcome(
                verdict="clean",
                reason="security_scan_clean",
                media_type="text/plain",
            )
        return _outcome(
            verdict="attachment_only",
            reason="security_format_attachment_only",
            media_type="application/pdf",
        )

    monkeypatch.setattr(FileSecurityClient, "scan", scan)
    workspace_id = _create(owner, "P7.1 synthetic exact downloads")
    source_name = "预算 #1 + 复核[甲].txt"
    source = b"synthetic downloadable source\n"
    first = _upload(
        owner,
        workspace_id,
        body=source,
        name=source_name,
        media_type="text/plain",
        key="p71-download-upload-idempotency-000001",
    )
    derived = run_artifact_derivation_once(state_root=state)
    assert derived is not None and derived.state == "converged"

    report_name = "财务报告 终版[1].pdf"
    report = b"%PDF-1.7\nsynthetic report fixture only\n%%EOF\n"
    second = _upload(
        owner,
        workspace_id,
        body=report,
        name=report_name,
        media_type="application/pdf",
        key="p71-download-upload-idempotency-000002",
    )

    refreshed = owner.get(f"{BASE}/workspaces/{workspace_id}")
    assert refreshed.status_code == 200, refreshed.text
    artifact = refreshed.json()["artifact"]
    items = artifact["downloadables"]
    originals = [item for item in items if item["kind"] == "original"]
    derivatives = [item for item in items if item["kind"] == "derivative"]
    assert len(originals) == 2
    assert len(derivatives) == 1
    assert [item["version_number"] for item in originals] == [1, 2]
    assert [item["name"] for item in originals] == [source_name, report_name]
    assert originals[0]["id"] == first["artifact_version_id"]
    assert originals[1]["id"] == second["artifact_version_id"]
    assert originals[1]["media_type"] == "application/pdf"
    assert originals[1]["source"]["kind"] == "upload"
    assert originals[1]["source"]["operation_id"]
    assert derivatives[0]["source"] == {
        "kind": "processor",
        "artifact_version_id": first["artifact_version_id"],
        "processor": {
            "name": PROCESSOR_NAME,
            "version": PROCESSOR_VERSION,
        },
        "generation_number": 1,
    }

    historical_response = _download(owner, workspace_id, originals[0])
    _assert_attachment(
        historical_response,
        item=originals[0],
        expected=source,
    )
    assert (
        historical_response.headers["x-kmfa-source-operation"]
        == originals[0]["source"]["operation_id"]
    )
    assert (
        historical_response.headers["x-kmfa-source-artifact-version"]
        == originals[0]["id"]
    )

    derivative_response = _download(owner, workspace_id, derivatives[0])
    _assert_attachment(
        derivative_response,
        item=derivatives[0],
        expected=source,
    )
    assert (
        derivative_response.headers["x-kmfa-source-artifact-version"]
        == first["artifact_version_id"]
    )
    assert (
        derivative_response.headers["x-kmfa-processor"]
        == f"{PROCESSOR_NAME}/{PROCESSOR_VERSION}"
    )

    report_response = _download(owner, workspace_id, originals[1])
    _assert_attachment(
        report_response,
        item=originals[1],
        expected=report,
    )
    assert report_response.headers["content-type"] == "application/pdf"
    assert report_response.headers["content-disposition"].startswith(
        "attachment;"
    )

    downloaded_hashes = {
        item["id"]: hashlib.sha256(
            _download(owner, workspace_id, item).content
        ).hexdigest()
        for item in items
    }
    assert downloaded_hashes == {
        item["id"]: item["sha256"] for item in items
    }


def test_download_idor_integrity_failure_and_flag_rollback_fail_closed(
    download_runtime: tuple[Path, TestClient],
    monkeypatch: pytest.MonkeyPatch,
):
    state, owner = download_runtime
    monkeypatch.setattr(
        FileSecurityClient,
        "scan",
        lambda self, *args, **kwargs: _outcome(
            verdict="attachment_only",
            reason="security_format_attachment_only",
            media_type="text/html",
        ),
    )
    owner_workspace = _create(owner, "P7.1 owner")
    dangerous = b"<script>synthetic-never-inline()</script>"
    _upload(
        owner,
        owner_workspace,
        body=dangerous,
        name="dangerous fixture.html",
        media_type="text/html",
        key="p71-download-upload-idempotency-000003",
    )
    item = owner.get(
        f"{BASE}/workspaces/{owner_workspace}"
    ).json()["artifact"]["downloadables"][0]

    attacker = TestClient(
        app,
        base_url="https://testserver",
        headers={"Origin": "https://testserver"},
    )
    attacker_workspace = _create(attacker, "P7.1 other workspace")
    wrong_workspace = _download(attacker, attacker_workspace, item)
    assert wrong_workspace.status_code == 404
    assert wrong_workspace.json()["detail"] == "artifact_download_not_found"

    anonymous = TestClient(
        app,
        base_url="https://testserver",
        headers={"Origin": "https://testserver"},
    )
    unauthorized = _download(anonymous, owner_workspace, item)
    assert unauthorized.status_code == 404
    assert unauthorized.json()["detail"] == "workspace_not_found"

    object_path = next((state / "objects").glob("*.blob"))
    object_path.write_bytes(b"tampered")
    corrupt = _download(owner, owner_workspace, item)
    assert corrupt.status_code == 503
    assert corrupt.json()["detail"] == "artifact_integrity_failed"

    object_path.write_bytes(dangerous)
    monkeypatch.setenv("KMFA_SINGLE_FILE_DOWNLOAD_ENABLED", "0")
    rolled_back = _download(owner, owner_workspace, item)
    assert rolled_back.status_code == 404
    assert rolled_back.json()["detail"] == "single_file_download_disabled"
    legacy = owner.post(
        f"{BASE}/workspaces/{owner_workspace}/artifact/download"
    )
    assert legacy.status_code == 200
    assert legacy.content == dangerous
    assert legacy.headers["content-disposition"].startswith("attachment;")
    assert legacy.headers["content-type"].startswith(
        "application/octet-stream"
    )
