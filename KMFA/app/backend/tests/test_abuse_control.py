"""S04/P4.4 TEST-WS-004 anonymous abuse-control contract."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import anti_abuse as abuse
from app import walking_skeleton as skeleton
from app.main import app

BASE = "/public-api/walking-skeleton/v1"
ORIGIN = "https://kmfa.test"
SYNTHETIC_FILE = b"synthetic-p44-abuse-fixture"


@pytest.fixture
def abuse_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    state = tmp_path / "abuse-control"
    monkeypatch.setenv("KMFA_WALKING_SKELETON_ENABLED", "1")
    monkeypatch.setenv("KMFA_WALKING_SKELETON_STATE_DIR", str(state))
    monkeypatch.setenv("KMFA_ABUSE_POLICY_MODE", "enforced")
    monkeypatch.delenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", raising=False)
    return state


def _client() -> TestClient:
    return TestClient(
        app,
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
    )


def _signals(index: int, workspace: int | None = None) -> abuse.RequestSignals:
    def digest(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    return abuse.RequestSignals(
        ip_tag=digest(f"ip-{index}"),
        device_tag=digest(f"device-{index}"),
        actor_tag=digest(f"actor-{index}"),
        workspace_tag=(
            digest(f"workspace-{workspace}") if workspace is not None else None
        ),
    )


def _solve(challenge: dict) -> str:
    assert challenge["algorithm"] == "sha256-leading-zero-bits"
    token = str(challenge["token"])
    difficulty = int(challenge["difficulty_bits"])
    for nonce in range(2**32):
        proof = f"{token}:{nonce}"
        digest = hashlib.sha256(proof.encode("ascii")).digest()
        if abuse._leading_zero_bits(digest) >= difficulty:
            return proof
    raise AssertionError("challenge solver exhausted")


def _create(client: TestClient, *, ip: str, name: str) -> tuple[dict, str]:
    response = client.post(
        f"{BASE}/workspaces",
        headers={"CF-Connecting-IP": ip},
        json={"project_name": name},
    )
    assert response.status_code == 201, response.text
    session = response.cookies.get(skeleton.SESSION_COOKIE_NAME)
    assert skeleton.ACCESS_TOKEN_RE.fullmatch(session)
    return response.json(), session


def test_normal_fixture_has_zero_false_positives_and_public_browse_stays_open(
    abuse_store: Path,
):
    del abuse_store
    statuses: list[int] = []
    for index in range(20):
        ip = f"198.51.100.{index + 1}"
        with _client() as client:
            root = client.get("/", headers={"CF-Connecting-IP": ip})
            status = client.get(f"{BASE}/status", headers={"CF-Connecting-IP": ip})
            created, _ = _create(
                client,
                ip=ip,
                name=f"normal-synthetic-{index}",
            )
            workspace_id = created["workspace"]["workspace_id"]
            read = client.get(
                f"{BASE}/workspaces/{workspace_id}",
                headers={"CF-Connecting-IP": ip},
            )
            saved = client.patch(
                f"{BASE}/workspaces/{workspace_id}",
                headers={"CF-Connecting-IP": ip},
                json={"progress": index},
            )
            statuses.extend(
                (
                    root.status_code,
                    status.status_code,
                    201,
                    read.status_code,
                    saved.status_code,
                )
            )
            assert root.status_code == status.status_code == read.status_code == 200
            assert saved.status_code == 200
            assert status.headers["x-kmfa-abuse-decision"] == (
                "public-browse-exempt"
            )
            assert status.json()["abuse_control"]["login_required"] is False

    false_positives = sum(status in {403, 429} for status in statuses)
    assert len(statuses) == 100
    assert false_positives == 0
    assert false_positives / len(statuses) < 0.01


def test_actor_limit_issues_one_use_bound_challenge_without_login(
    abuse_store: Path,
):
    del abuse_store
    ip = "198.51.100.81"
    with _client() as client:
        status = client.get(f"{BASE}/status", headers={"CF-Connecting-IP": ip})
        device_cookie = next(
            value
            for value in status.headers.get_list("set-cookie")
            if value.startswith(f"{abuse.DEVICE_COOKIE_NAME}=")
        )
        assert "Secure" in device_cookie
        assert "HttpOnly" in device_cookie
        assert "SameSite=Strict" in device_cookie
        assert "Path=/" in device_cookie
        assert "Domain=" not in device_cookie
        allowed = [
            client.post(
                f"{BASE}/workspaces",
                headers={"CF-Connecting-IP": ip},
                json={"project_name": f"burst-{index}"},
            )
            for index in range(6)
        ]
        challenged = client.post(
            f"{BASE}/workspaces",
            headers={"CF-Connecting-IP": ip},
            json={"project_name": "challenge-target"},
        )
        assert [response.status_code for response in allowed] == [201] * 6
        assert challenged.status_code == 429
        assert challenged.json()["detail"] == "risk_challenge_required"
        assert challenged.headers["x-kmfa-abuse-decision"] == "challenge-required"
        proof = _solve(challenged.json()["challenge"])

        passed = client.post(
            f"{BASE}/workspaces",
            headers={
                "CF-Connecting-IP": ip,
                "X-KMFA-Challenge-Proof": proof,
            },
            json={"project_name": "challenge-passed"},
        )
        replay = client.post(
            f"{BASE}/workspaces",
            headers={
                "CF-Connecting-IP": ip,
                "X-KMFA-Challenge-Proof": proof,
            },
            json={"project_name": "challenge-replayed"},
        )
        cross_actor = client.post(
            f"{BASE}/workspaces",
            headers={
                "CF-Connecting-IP": "203.0.113.201",
                "X-KMFA-Challenge-Proof": proof,
            },
            json={"project_name": "challenge-cross-actor"},
        )

    assert passed.status_code == 201
    assert passed.headers["x-kmfa-abuse-decision"] == "challenge-passed"
    assert replay.status_code == 403
    assert replay.json()["detail"] == "risk_challenge_replayed"
    assert cross_actor.status_code == 403
    assert cross_actor.json()["detail"] == "risk_challenge_invalid"
    assert all("login" not in response.text.lower() for response in (challenged, replay))


def test_upload_and_export_floods_are_isolated_and_growth_is_bounded(
    abuse_store: Path,
):
    ip = "198.51.100.91"
    with _client() as client:
        client.get(f"{BASE}/status", headers={"CF-Connecting-IP": ip})
        created, _ = _create(client, ip=ip, name="bounded-flood")
        workspace_id = created["workspace"]["workspace_id"]
        upload_headers = {
            "CF-Connecting-IP": ip,
            "Content-Type": "application/octet-stream",
            "X-KMFA-Filename": "bounded.bin",
        }
        uploads = [
            client.put(
                f"{BASE}/workspaces/{workspace_id}/artifact",
                headers=upload_headers,
                content=(
                    SYNTHETIC_FILE if index == 0 else b"must-not-replace"
                ),
            )
            for index in range(7)
        ]
        assert uploads[0].status_code == 200
        assert [response.status_code for response in uploads[1:6]] == [409] * 5
        blocked_upload = uploads[6]
        assert blocked_upload.status_code == 429
        assert blocked_upload.json()["detail"] == "risk_challenge_required"

        downloads = [
            client.post(
                f"{BASE}/workspaces/{workspace_id}/artifact/download",
                headers={"CF-Connecting-IP": ip},
            )
            for _ in range(7)
        ]
        root_after_flood = client.get("/", headers={"CF-Connecting-IP": ip})
        status_after_flood = client.get(
            f"{BASE}/status",
            headers={"CF-Connecting-IP": ip},
        )

    assert [response.status_code for response in downloads[:6]] == [200] * 6
    assert all(response.content == SYNTHETIC_FILE for response in downloads[:6])
    assert downloads[6].status_code == 429
    assert downloads[6].json()["detail"] == "risk_challenge_required"
    assert root_after_flood.status_code == status_after_flood.status_code == 200

    database = abuse_store / "walking_skeleton.sqlite3"
    connection = sqlite3.connect(database)
    try:
        artifact_count, artifact_bytes = connection.execute(
            "SELECT COUNT(*), COALESCE(SUM(size_bytes), 0) FROM artifacts"
        ).fetchone()
        download_events = connection.execute(
            "SELECT COUNT(*) FROM audit_events WHERE action = 'artifact_download'"
        ).fetchone()[0]
    finally:
        connection.close()
    assert (artifact_count, artifact_bytes) == (1, len(SYNTHETIC_FILE))
    assert download_events == 6
    assert not list((abuse_store / "tmp").glob("*"))


def test_global_sustained_budget_blocks_distributed_low_speed_and_recovers(
    abuse_store: Path,
):
    del abuse_store
    policy = abuse.POLICIES["identity"]
    sustained = next(window for window in policy.windows if window.seconds == 3600)
    base = (1_800_000_000 // 3600) * 3600 + 1
    allowed = 0
    for index in range(sustained.global_limit):
        admission = abuse.admit_request(
            operation="identity",
            signals=_signals(index),
            proof_header=None,
            now_value=base + (index * 5),
        )
        assert admission.allowed
        abuse.release_lease(admission.lease_id)
        allowed += 1

    blocked = abuse.admit_request(
        operation="identity",
        signals=_signals(sustained.global_limit + 1),
        proof_header=None,
        now_value=base + (sustained.global_limit * 5),
    )
    recovered = abuse.admit_request(
        operation="identity",
        signals=_signals(sustained.global_limit + 2),
        proof_header=None,
        now_value=base + 3600,
    )
    abuse.release_lease(recovered.lease_id)

    assert allowed == sustained.global_limit
    assert not blocked.allowed
    assert blocked.decision == "capacity-blocked"
    assert blocked.reason == "global-3600s"
    assert blocked.challenge is None
    assert recovered.allowed
    snapshot = abuse.operations_snapshot()
    # Long-window rows are bounded by accepted global capacity and two hashed
    # actor scopes per accepted request; no attacker-controlled raw key exists.
    assert snapshot["state_counts"]["rate_counters"] <= (
        sustained.global_limit * 3 + 32
    )
    assert snapshot["raw_identifiers_stored"] is False


def test_concurrency_budget_is_global_non_bypassable_and_releases(
    abuse_store: Path,
):
    del abuse_store
    first = abuse.admit_request(
        operation="upload",
        signals=_signals(1, 1),
        proof_header=None,
        now_value=1_900_000_001,
    )
    second = abuse.admit_request(
        operation="upload",
        signals=_signals(2, 2),
        proof_header=None,
        now_value=1_900_000_001,
    )
    blocked = abuse.admit_request(
        operation="upload",
        signals=_signals(3, 3),
        proof_header=None,
        now_value=1_900_000_001,
    )
    assert first.allowed and second.allowed
    assert not blocked.allowed
    assert blocked.reason == "concurrency"
    assert blocked.challenge is None

    abuse.release_lease(first.lease_id)
    recovered = abuse.admit_request(
        operation="upload",
        signals=_signals(4, 4),
        proof_header=None,
        now_value=1_900_000_002,
    )
    assert recovered.allowed
    abuse.release_lease(second.lease_id)
    abuse.release_lease(recovered.lease_id)
    assert abuse.operations_snapshot()["state_counts"]["concurrency_leases"] == 0


def test_operational_store_is_bounded_hashed_and_private_snapshot_has_no_raw_ids(
    abuse_store: Path,
):
    ip = "203.0.113.77"
    with _client() as client:
        status = client.get(f"{BASE}/status", headers={"CF-Connecting-IP": ip})
        device = client.cookies.get(abuse.DEVICE_COOKIE_NAME)
        created, session = _create(client, ip=ip, name="privacy-safe-control")
        workspace_id = created["workspace"]["workspace_id"]
        for _ in range(7):
            client.post(
                f"{BASE}/workspaces",
                headers={"CF-Connecting-IP": ip},
                json={"project_name": "bounded-event-sample"},
            )
        ops = client.get("/ops/abuse-control/status")

    assert status.status_code == 200
    assert abuse.DEVICE_RE.fullmatch(device)
    assert ops.status_code == 200
    payload = ops.json()
    assert payload["healthy"] is True
    assert payload["raw_identifiers_stored"] is False
    serialized = ops.text
    assert ip not in serialized
    assert device not in serialized
    assert workspace_id not in serialized
    assert session not in serialized
    control_bytes = b"".join(
        path.read_bytes()
        for path in (abuse_store / "abuse-control").rglob("*")
        if path.is_file()
    )
    for raw in (ip, device, workspace_id, session):
        assert raw.encode() not in control_bytes
    assert payload["state_counts"]["decision_windows"] <= (
        len(abuse.POLICIES) * 8 * abuse.EVENT_BUCKETS
    )


def test_invalid_policy_fails_expensive_actions_closed_but_not_public_browse(
    abuse_store: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    del abuse_store
    monkeypatch.setenv("KMFA_ABUSE_POLICY_MODE", "typo")
    with _client() as client:
        root = client.get("/")
        status = client.get(f"{BASE}/status")
        create = client.post(
            f"{BASE}/workspaces",
            json={"project_name": "must-not-create"},
        )
    assert root.status_code == status.status_code == 200
    assert create.status_code == 503
    assert create.json()["detail"] == "abuse_policy_configuration_invalid"
    assert create.headers["x-kmfa-abuse-decision"] == "fail-closed"


def test_emergency_mode_exempts_only_low_cost_routes_and_ops_remains_private(
    abuse_store: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    ip = "198.51.100.230"
    with _client() as client:
        client.get(f"{BASE}/status", headers={"CF-Connecting-IP": ip})
        created, _ = _create(client, ip=ip, name="emergency-mode")
        workspace_id = created["workspace"]["workspace_id"]
        monkeypatch.setenv("KMFA_ABUSE_POLICY_MODE", "emergency-expensive-only")
        read = client.get(
            f"{BASE}/workspaces/{workspace_id}",
            headers={"CF-Connecting-IP": ip},
        )
        mutation = client.patch(
            f"{BASE}/workspaces/{workspace_id}",
            headers={"CF-Connecting-IP": ip},
            json={"progress": 7},
        )
        upload = client.put(
            f"{BASE}/workspaces/{workspace_id}/artifact",
            headers={
                "CF-Connecting-IP": ip,
                "Content-Type": "application/octet-stream",
                "X-KMFA-Filename": "still-guarded.bin",
            },
            content=b"guarded",
        )
        monkeypatch.setenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", "1")
        private_ops = client.get("/ops/abuse-control/status")

    assert read.status_code == mutation.status_code == upload.status_code == 200
    assert read.headers["x-kmfa-abuse-decision"] == "emergency-low-cost-exempt"
    assert mutation.headers["x-kmfa-abuse-decision"] == (
        "emergency-low-cost-exempt"
    )
    assert upload.headers["x-kmfa-abuse-decision"] == "allowed"
    assert private_ops.status_code == 503
    assert (abuse_store / "objects").is_dir()


def test_release_wiring_runs_and_retains_only_compact_abuse_evidence(
    abuse_store: Path,
):
    del abuse_store
    repo = Path(__file__).resolve().parents[4]
    workflow = (repo / ".github/workflows/app-e2e.yml").read_text(
        encoding="utf-8"
    )
    frontend = (
        repo / "KMFA/app/frontend/src/WalkingSkeleton.jsx"
    ).read_text(encoding="utf-8")
    dockerfile = (repo / "KMFA/app/backend/Dockerfile").read_text(
        encoding="utf-8"
    )
    assert "KMFA/app/e2e/abuse_control_flow.py" in workflow
    assert "abuse-control-e2e/" in workflow
    assert "docker rm -f kmfa-p44-e2e" in workflow
    assert "fetchWithRiskChallenge" in frontend
    assert "X-KMFA-Challenge-Proof" in frontend
    assert "--no-access-log" in dockerfile


def test_core_lifetime_caps_bound_sessions_audit_and_artifact_bytes(
    abuse_store: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(skeleton, "MAX_WORKSPACES_TOTAL", 1)
    monkeypatch.setattr(skeleton, "MAX_ACTIVE_SESSIONS_PER_WORKSPACE", 2)
    monkeypatch.setattr(skeleton, "MAX_AUDIT_EVENTS_PER_WORKSPACE", 5)
    monkeypatch.setattr(skeleton, "MAX_TOTAL_ARTIFACT_BYTES", 4)
    created = skeleton._create_workspace("lifetime-budget")
    with pytest.raises(skeleton.SkeletonError) as workspace_error:
        skeleton._create_workspace("must-not-grow")
    assert workspace_error.value.code == "workspace_capacity_reached"
    workspace_id = created["workspace"]["workspace_id"]
    first_token = created["access_token"]
    skeleton._exchange_workspace_session(
        workspace_id,
        created["recovery_code"],
    )
    latest = skeleton._exchange_workspace_session(
        workspace_id,
        created["recovery_code"],
    )

    connection = sqlite3.connect(abuse_store / "walking_skeleton.sqlite3")
    try:
        active_sessions = connection.execute(
            "SELECT COUNT(*) FROM access_tokens WHERE workspace_id = ?",
            (workspace_id,),
        ).fetchone()[0]
    finally:
        connection.close()
    assert active_sessions == 2
    with skeleton._store() as connection:
        with pytest.raises(skeleton.SkeletonError) as error:
            skeleton._authorize(
                connection,
                workspace_id,
                f"Bearer {first_token}",
            )
    assert error.value.code == "workspace_not_found"
    assert latest["workspace"]["workspace_id"] == workspace_id

    saved = skeleton._update_workspace(
        workspace_id,
        f"Bearer {latest['access_token']}",
        skeleton.UpdateWorkspaceRequest(progress=1),
    )
    assert saved["progress"] == 1
    with pytest.raises(skeleton.SkeletonError) as audit_error:
        skeleton._update_workspace(
            workspace_id,
            f"Bearer {latest['access_token']}",
            skeleton.UpdateWorkspaceRequest(progress=2),
        )
    assert audit_error.value.code == "workspace_audit_capacity_reached"
    assert skeleton._get_workspace(
        workspace_id,
        f"Bearer {latest['access_token']}",
    )["progress"] == 1

    with _client() as client:
        # Use the newest server-issued session as a legacy bearer so the test
        # isolates business capacity from browser cookie rotation.
        upload = client.put(
            f"{BASE}/workspaces/{workspace_id}/artifact",
            headers={
                "Authorization": f"Bearer {latest['access_token']}",
                "Content-Type": "application/octet-stream",
                "X-KMFA-Filename": "too-large-for-total.bin",
                "CF-Connecting-IP": "198.51.100.222",
            },
            content=b"12345",
        )
    assert upload.status_code == 429
    assert upload.json()["detail"] == "artifact_capacity_reached"
    assert not list((abuse_store / "objects").glob("*"))
