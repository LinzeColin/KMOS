"""Private daily-funds projection API: no raw source crosses the app boundary."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app import main as main_module
from app.main import app


client = TestClient(app)


def _same_origin_headers() -> dict[str, str]:
    return {"Origin": "http://testserver", "Host": "testserver"}


def _write_projection(root: Path) -> None:
    root.mkdir(parents=True)
    current = {
        "schema_version": "kmfa.daily_funds.current_projection.v1",
        "publication": {
            "publication_id": "c" * 64,
            "business_date": "2026-07-30",
            "status": "VALID",
            "source_versions": [{"source_version": "a" * 64}, {"source_version": "b" * 64}],
            "reconciliation_difference_fen": 0,
            "threshold_snapshot": {
                "fixed": {"hard_fen": 60_000_000, "soft_fen": 120_000_000},
                "floating": [{
                    "name": "three_month", "active": True, "threshold_fen": 100_000_000,
                    "start": "2026-04-01", "end": "2026-06-30", "days": 91,
                    "coverage": "1", "direct_observations": 90, "covered_days": 91,
                    "carried_forward_days": 1, "reason": None,
                }],
                "currency": "CNY",
                "fixed_risk": "正常",
                "dynamic_flag": None,
            },
            "created_at": "2026-07-30T12:00:00Z",
            "git_commit_sha": "d" * 40,
            "d1_projection_version": "kmfa.daily_funds.d1.v1",
            "r2_manifest_sha256": "e" * 64,
            "oci_backup_state": "PENDING",
        },
        "summary": {
            "total_available_fen": 157_000_000,
            "risk_label": "正常",
            "dynamic_flag": None,
            "by_company_ending_fen": {"公司A": 157_000_000},
            "by_bank_ending_fen": {"银行A": 157_000_000},
            "account_ending_by_hash": {"f" * 64: 157_000_000},
        },
        "daily_balances": [
            {"business_date": "2026-07-28", "ending_available_fen": 150_000_000, "direct_observation": False, "coverage_gap": True, "carried_forward": False},
            {"business_date": "2026-07-29", "ending_available_fen": 150_000_000, "direct_observation": True, "coverage_gap": False, "carried_forward": False},
            {"business_date": "2026-07-30", "ending_available_fen": 157_000_000, "direct_observation": True, "coverage_gap": False, "carried_forward": False},
        ],
        "transactions": [
            {
                "transaction_key_hash": "f" * 64,
                "business_date": "2026-07-30",
                "inflow_fen": 25_000_000,
                "outflow_fen": 0,
                "adjustment_fen": 0,
                "internal_transfer": False,
                "source_version": "a" * 64,
                "message_id_hash": "b" * 64,
            },
            {
                "transaction_key_hash": "9" * 64,
                "business_date": "2026-07-30",
                "inflow_fen": 0,
                "outflow_fen": 18_000_000,
                "adjustment_fen": 0,
                "internal_transfer": False,
                "source_version": "a" * 64,
                "message_id_hash": "a" * 64,
            },
        ],
        "runtime": {
            "oci_backup_state": "OK",
            "git_publication_commit_sha": "f" * 40,
            "oci_restore_manifest_sha": "e" * 64,
        },
    }
    status = {
        "schema_version": "kmfa.daily_funds.status.v1",
        "human_status": "已更新",
        "machine_code": "VALID_PUBLISHED",
        "effective_business_date": "2026-07-30",
        "last_verified_at": "2026-07-30T12:00:00Z",
        "publication_id": "c" * 64,
        "updated_at": "2026-07-30T12:00:00Z",
        "schedules": {
            "history_poll": "*/15 * * * * Asia/Shanghai",
            "auth_probe": "* * * * * Asia/Shanghai",
            "keepalive": "0 * * * * Asia/Shanghai",
            "backfill": "5,20,35,50 * * * * Asia/Shanghai",
            "observer": "30 3 * * * Asia/Shanghai",
            "r2_guard": "0 */6 * * * Asia/Shanghai",
            "cold_backup": "10 4 * * * Asia/Shanghai",
            "raw_archive_audit": "20 5 * * * Asia/Shanghai",
            "runtime_audit": "45 5 * * * Asia/Shanghai",
            "restore_drill": "0 5 1 * * Asia/Shanghai",
        },
        "backup_state": "OK",
    }
    flow_state = {
        "schema_version": "kmfa.daily_funds.flow_state.v1",
        "updated_at": "2026-07-30T12:05:00Z",
        "deployment": {
            "runtime_state": "RUNTIME_AUDITED",
            "instance_state": "OBSERVED",
            "identity_state": "UNKNOWN",
            "runtime_audit_at": "2026-07-30T12:04:00Z",
        },
        "schedules": {"observer": "30 3 * * * Asia/Shanghai"},
        "business_flow": {
            "stage": "POST_DEPLOY_OBSERVING",
            "human_status": "已更新",
            "machine_code": "VALID_PUBLISHED",
            "effective_business_date": "2026-07-30",
            "last_verified_at": "2026-07-30T12:05:00Z",
            "last_status_at": "2026-07-30T12:05:00Z",
            "publication_present": True,
        },
        "source_discovery": {
            "state": "COMPLETE_PAIR_READY",
            "raw_fixture_should_not_escape": "message-fixture",
        },
        "operations": {
            "poll": {
                "state": "SUCCEEDED",
                "code": "VALID_PUBLISHED",
                "finished_at": "2026-07-30T12:05:00Z",
                "raw_fixture_should_not_escape": "message-fixture",
            },
            "auth-probe": {
                "state": "SUCCEEDED",
                "code": "AUTH_OK",
                "finished_at": "2026-07-30T12:05:30Z",
            },
            "backfill": {
                "state": "SUCCEEDED",
                "code": "BACKFILL_EMPTY_WINDOW",
                "finished_at": "2026-07-30T12:06:30Z",
                "raw_fixture_should_not_escape": "backfill-fixture",
            },
            "r2-guard": {
                "state": "SUCCEEDED",
                "code": "R2_ZERO_CHARGE_GUARD_OK",
                "finished_at": "2026-07-30T12:06:00Z",
            },
        },
        "attachment_capabilities": [
            {
                "family": "资金账户明细表",
                "suffix": ".csv",
                "declared_mime": "text/csv",
                "magic": "TEXT",
                "parser_version": "kmfa.daily_funds.parser.v3",
                "outcome": "SUPPORTED",
                "code": "PARSER_OPEN_OK",
                "count": 1,
                "last_observed_at": "2026-07-30T12:04:00Z",
            },
            {
                "family": "资金账户明细表",
                "suffix": ".png",
                "declared_mime": "image/png",
                "magic": "PNG",
                "parser_version": "kmfa.daily_funds.parser.v3",
                "outcome": "NEEDS_REVIEW",
                "code": "UNSUPPORTED_ATTACHMENT",
                "count": 2,
                "last_observed_at": "2026-07-30T12:05:00Z",
                # Another untrusted extension must not cross the app boundary.
                "raw_fixture_should_not_escape": "attachment-fixture",
            },
        ],
        "self_healing": {
            "state": "JOURNAL_READY",
            "restart_recovery": "CURSOR_INBOX_LEASES",
            "restore_drill": "NOT_YET_RUN",
            "restore_drill_at": None,
        },
        "post_deploy_observer": {
            "schedule": "30 3 * * * Asia/Shanghai",
            "state": "OBSERVING",
            "last_comparison": "D1_AND_POINTER_VERIFIED",
            "required_business_days": 5,
            "completed_business_days": 1,
            "baseline_business_date": "2026-07-29",
            "started_at": "2026-07-29T12:00:00Z",
            "last_observed_at": "2026-07-30T12:05:00Z",
            "comparisons": [{
                "business_date": "2026-07-30",
                "observed_at": "2026-07-30T12:05:00Z",
                "comparison_state": "D1_AND_POINTER_VERIFIED",
                "coverage_state": "DIRECT_OBSERVATION",
                "amount_state": "ZERO_FEN",
                "threshold_state": "VALID",
                "retrieval_state": "COMPLETE_PAIR",
                "duplicate_state": "SOURCE_VERSION_UNIQUE",
                "backup_state": "OK",
                "restore_state": "NOT_YET_RUN",
                "latency_minutes": 5,
                # A malicious extension must never cross the existing status
                # API boundary merely because the worker volume is shared.
                "raw_fixture_should_not_escape": "group-fixture",
            }],
        },
    }
    (root / "current.json").write_text(json.dumps(current), encoding="utf-8")
    (root / "status.json").write_text(json.dumps(status), encoding="utf-8")
    (root / "flow_state.json").write_text(json.dumps(flow_state), encoding="utf-8")
    cashflow_observation = {
        "schema_version": "kmfa.daily_funds.cashflow_observation.v2",
        "generated_at": "2026-07-30T12:05:00Z",
        "parser_version": "kmfa.daily_funds.cashflow_observation.v9",
        "source_coverage": {
            "eligible_documents": 2,
            "parsed_documents": 2,
            "rejected_documents": 0,
            "distinct_business_days": 2,
        },
        "rejection_categories": {},
        "evidence_version": "a" * 12,
        "status": "VERIFIED",
        "machine_code": "CASHFLOW_OBSERVATION_VERIFIED",
        "points": [
            {
                "business_date": "2026-07-29",
                "inflow_fen": 1_000,
                "outflow_fen": 400,
                "net_change_fen": 600,
            },
            {
                "business_date": "2026-07-30",
                "inflow_fen": 800,
                "outflow_fen": 1_200,
                "net_change_fen": -400,
            },
        ],
    }
    (root / "cashflow_observation.json").write_text(json.dumps(cashflow_observation), encoding="utf-8")


def test_cashflow_observation_is_read_only_footer_reconciled_and_not_a_balance_fallback(tmp_path, monkeypatch):
    publication = tmp_path / "publication"
    _write_projection(publication)
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)

    response = client.get("/ops/api/daily-funds/cashflow-observations?range=30d")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "VERIFIED"
    assert body["message"].startswith("已按截图逐行与合计复核")
    assert body["points"] == [
        {"business_date": "2026-07-29", "inflow_fen": 1_000, "outflow_fen": 400, "net_change_fen": 600},
        {"business_date": "2026-07-30", "inflow_fen": 800, "outflow_fen": 1_200, "net_change_fen": -400},
    ]
    assert "machine_code" not in body
    assert "parser_version" not in body
    assert body["rejection_categories"] == {}

    observation_path = publication / "cashflow_observation.json"
    needs_review = json.loads(observation_path.read_text(encoding="utf-8"))
    needs_review.update({
        "status": "NEEDS_REVIEW",
        "machine_code": "CASHFLOW_OBSERVATION_PARSE_NEEDS_REVIEW",
        "points": [],
        "source_coverage": {
            "eligible_documents": 2,
            "parsed_documents": 0,
            "rejected_documents": 2,
            "distinct_business_days": 0,
        },
        "rejection_categories": {"FOOTER_RECONCILIATION": 2},
    })
    observation_path.write_text(json.dumps(needs_review), encoding="utf-8")
    review = client.get("/ops/api/daily-funds/cashflow-observations?range=30d")
    assert review.status_code == 200
    assert review.json()["rejection_categories"] == {"合计勾稽": 2}
    assert "FOOTER_RECONCILIATION" not in review.text

    stale = json.loads(observation_path.read_text(encoding="utf-8"))
    stale["parser_version"] = "kmfa.daily_funds.cashflow_observation.v4"
    observation_path.write_text(json.dumps(stale), encoding="utf-8")
    stale_response = client.get("/ops/api/daily-funds/cashflow-observations?range=30d")
    assert stale_response.status_code == 200
    assert stale_response.json()["status"] == "NEEDS_REVIEW"
    assert stale_response.json()["points"] == []

    malformed = json.loads(observation_path.read_text(encoding="utf-8"))
    malformed["parser_version"] = main_module.DAILY_FUNDS_CASHFLOW_OBSERVATION_PARSER_VERSION
    malformed["raw_fixture_should_not_escape"] = "cashflow-raw-fixture"
    observation_path.write_text(json.dumps(malformed), encoding="utf-8")
    blocked = client.get("/ops/api/daily-funds/cashflow-observations?range=30d")
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "NEEDS_REVIEW"
    assert blocked.json()["points"] == []
    assert "cashflow-raw-fixture" not in blocked.text


def test_daily_funds_auth_session_is_access_api_only_and_never_enters_source_projection(tmp_path, monkeypatch):
    publication = tmp_path / "publication"
    control = tmp_path / "control"
    _write_projection(publication)
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)
    monkeypatch.setattr(main_module, "DAILY_FUNDS_CONTROL_DIR", control)

    initial = client.get("/ops/api/daily-funds/auth-session")
    assert initial.status_code == 200
    assert initial.json()["state"] == "NOT_REQUESTED"
    assert initial.headers["cache-control"] == "private, no-store"
    assert client.post("/ops/api/daily-funds/auth-session").status_code == 403

    started = client.post("/ops/api/daily-funds/auth-session", headers=_same_origin_headers())
    assert started.status_code == 202
    assert started.json() == {
        "state": "REQUESTED",
        "machine_code": "DWS_AUTH_BOOTSTRAP_STARTING",
        "updated_at": started.json()["updated_at"],
        "expires_at": started.json()["expires_at"],
        "authorization_url": None,
        "user_code": None,
    }
    request = json.loads((control / "dws_auth_request.json").read_text(encoding="utf-8"))
    assert set(request) == {"schema_version", "request_id", "action", "actor", "requested_at", "expires_at"}
    assert request["action"] == "START"
    assert "token" not in json.dumps(request).lower()

    now = datetime.now(timezone.utc)
    (control / "dws_auth_session.json").write_text(json.dumps({
        "schema_version": "kmfa.daily_funds.dws_auth_session.v1",
        "request_id": request["request_id"],
        "state": "AWAITING_APPROVAL",
        "machine_code": "DWS_AUTH_WAITING_OWNER",
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "updated_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
        "authorization_url": "https://login.dingtalk.com/device?userCode=ABCD-EFGH",
        "user_code": "ABCD-EFGH",
    }), encoding="utf-8")
    waiting = client.get("/ops/api/daily-funds/auth-session")
    assert waiting.status_code == 200
    assert waiting.json()["state"] == "AWAITING_APPROVAL"
    assert waiting.json()["user_code"] == "ABCD-EFGH"
    assert waiting.headers["cache-control"] == "private, no-store"
    source_health = client.get("/ops/api/daily-funds/source-health")
    assert "ABCD-EFGH" not in source_health.text

    cancelled = client.delete("/ops/api/daily-funds/auth-session", headers=_same_origin_headers())
    assert cancelled.status_code == 202
    assert cancelled.json()["state"] == "CANCELLING"
    assert cancelled.json()["user_code"] is None
    cancel_request = json.loads((control / "dws_auth_request.json").read_text(encoding="utf-8"))
    assert cancel_request["action"] == "CANCEL"
    assert cancel_request["request_id"] == request["request_id"]
    assert client.get("/ops/api/daily-funds/auth-session").json()["state"] == "CANCELLING"


def test_daily_funds_history_probe_is_a_fixed_access_api_and_never_enters_source_projection(tmp_path, monkeypatch):
    publication = tmp_path / "publication"
    control = tmp_path / "control"
    _write_projection(publication)
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)
    monkeypatch.setattr(main_module, "DAILY_FUNDS_CONTROL_DIR", control)

    initial = client.get("/ops/api/daily-funds/history-probe")
    assert initial.status_code == 200
    assert initial.json()["state"] == "NOT_REQUESTED"
    assert initial.headers["cache-control"] == "private, no-store"
    assert initial.headers["x-kmfa-daily-funds-probe"] == "v1"
    origin_denied = client.post("/ops/api/daily-funds/history-probe")
    assert origin_denied.status_code == 403
    assert origin_denied.headers["x-kmfa-daily-funds-probe"] == "v1"
    body_rejected = client.post(
        "/ops/api/daily-funds/history-probe",
        headers=_same_origin_headers(),
        json={"command": "must-not-cross-the-control-volume"},
    )
    assert body_rejected.status_code == 422
    assert body_rejected.headers["x-kmfa-daily-funds-probe"] == "v1"
    assert not (control / "dws_history_probe_request.json").exists()

    started = client.post("/ops/api/daily-funds/history-probe", headers=_same_origin_headers())
    assert started.status_code == 202
    assert started.headers["x-kmfa-daily-funds-probe"] == "v1"
    assert started.json() == {
        "state": "REQUESTED",
        "machine_code": "DWS_HISTORY_PROBE_QUEUED",
        "updated_at": started.json()["updated_at"],
        "expires_at": started.json()["expires_at"],
        "continuation_state": "NOT_STARTED",
        "cursor_transcript": "NOT_STARTED",
        "record_list_shape": "NOT_OBSERVED",
    }
    request = json.loads((control / "dws_history_probe_request.json").read_text(encoding="utf-8"))
    assert set(request) == {"schema_version", "request_id", "action", "actor", "requested_at", "expires_at"}
    assert request["schema_version"] == "kmfa.daily_funds.dws_history_probe_request.v1"
    assert request["action"] == "PROBE"
    assert not {"command", "group", "sender", "cursor", "amount"}.intersection(request)

    now = datetime.now(timezone.utc)
    raw_sentinel = "history-probe-source-value-must-not-escape"
    (control / "dws_history_probe_session.json").write_text(json.dumps({
        "schema_version": "kmfa.daily_funds.dws_history_probe_session.v2",
        "request_id": request["request_id"],
        "state": "COMPLETED",
        "machine_code": "DWS_HISTORY_PROBE_COMPLETED",
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "updated_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
        "continuation_state": "SECOND_PAGE_TERMINAL",
        "cursor_transcript": "OPAQUE_CURSOR_REUSED_SECOND_PAGE_TERMINAL",
        "record_list_shape": "NOT_OBSERVED",
        "raw_source_value": raw_sentinel,
    }), encoding="utf-8")
    malformed = client.get("/ops/api/daily-funds/history-probe")
    assert malformed.status_code == 200
    assert malformed.json()["state"] == "REQUESTED"
    assert raw_sentinel not in malformed.text
    assert raw_sentinel not in client.get("/ops/api/daily-funds/source-health").text

    cursor_sentinel = "opaque-provider-cursor-must-not-escape"
    (control / "dws_history_probe_session.json").write_text(json.dumps({
        "schema_version": "kmfa.daily_funds.dws_history_probe_session.v1",
        "request_id": request["request_id"],
        "state": "COMPLETED",
        "machine_code": "DWS_HISTORY_PROBE_COMPLETED",
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "updated_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
        "continuation_state": "SECOND_PAGE_TERMINAL",
        "cursor_transcript": cursor_sentinel,
    }), encoding="utf-8")
    invalid_cursor = client.get("/ops/api/daily-funds/history-probe")
    assert invalid_cursor.status_code == 200
    assert invalid_cursor.json()["state"] == "REQUESTED"
    assert cursor_sentinel not in invalid_cursor.text

    (control / "dws_history_probe_session.json").write_text(json.dumps({
        "schema_version": "kmfa.daily_funds.dws_history_probe_session.v1",
        "request_id": request["request_id"],
        "state": "COMPLETED",
        "machine_code": "DWS_HISTORY_PROBE_COMPLETED",
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "updated_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
        "continuation_state": "SECOND_PAGE_TERMINAL",
        "cursor_transcript": "OPAQUE_CURSOR_REUSED_SECOND_PAGE_TERMINAL",
    }), encoding="utf-8")
    completed = client.get("/ops/api/daily-funds/history-probe")
    assert completed.status_code == 200
    assert completed.headers["x-kmfa-daily-funds-probe"] == "v1"
    assert completed.json() == {
        "state": "COMPLETED",
        "machine_code": "DWS_HISTORY_PROBE_COMPLETED",
        "updated_at": completed.json()["updated_at"],
        "expires_at": completed.json()["expires_at"],
        "continuation_state": "SECOND_PAGE_TERMINAL",
        "cursor_transcript": "OPAQUE_CURSOR_REUSED_SECOND_PAGE_TERMINAL",
        "record_list_shape": "NOT_OBSERVED",
    }

    (control / "dws_history_probe_session.json").write_text(json.dumps({
        "schema_version": "kmfa.daily_funds.dws_history_probe_session.v2",
        "request_id": request["request_id"],
        "state": "COMPLETED",
        "machine_code": "DWS_GROUP_HISTORY_PROBE_COMPLETED",
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "updated_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
        "continuation_state": "GROUP_HISTORY_V2_SECOND_PAGE_TERMINAL",
        "cursor_transcript": "GROUP_HISTORY_V2_PROVIDER_MILLISECOND_CURSOR_REUSED_SECOND_PAGE_TERMINAL",
        "record_list_shape": "NOT_OBSERVED",
    }), encoding="utf-8")
    group_history_completed = client.get("/ops/api/daily-funds/history-probe")
    assert group_history_completed.status_code == 200
    assert group_history_completed.json() == {
        "state": "COMPLETED",
        "machine_code": "DWS_GROUP_HISTORY_PROBE_COMPLETED",
        "updated_at": group_history_completed.json()["updated_at"],
        "expires_at": group_history_completed.json()["expires_at"],
        "continuation_state": "GROUP_HISTORY_V2_SECOND_PAGE_TERMINAL",
        "cursor_transcript": "GROUP_HISTORY_V2_PROVIDER_MILLISECOND_CURSOR_REUSED_SECOND_PAGE_TERMINAL",
        "record_list_shape": "NOT_OBSERVED",
    }

    (control / "dws_history_probe_session.json").write_text(json.dumps({
        "schema_version": "kmfa.daily_funds.dws_history_probe_session.v2",
        "request_id": request["request_id"],
        "state": "FAILED",
        "machine_code": "DWS_PAGE_RECORDS_MISSING",
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "updated_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
        "continuation_state": "NOT_STARTED",
        "cursor_transcript": "NOT_STARTED",
        "record_list_shape": "NO_DIRECT_LIST",
    }), encoding="utf-8")
    classified = client.get("/ops/api/daily-funds/history-probe")
    assert classified.status_code == 200
    assert classified.json() == {
        "state": "FAILED",
        "machine_code": "DWS_PAGE_RECORDS_MISSING",
        "updated_at": classified.json()["updated_at"],
        "expires_at": classified.json()["expires_at"],
        "continuation_state": "NOT_STARTED",
        "cursor_transcript": "NOT_STARTED",
        "record_list_shape": "NO_DIRECT_LIST",
    }


def test_daily_funds_history_probe_marks_a_real_control_volume_failure(tmp_path, monkeypatch):
    publication = tmp_path / "publication"
    control_file = tmp_path / "control-file"
    _write_projection(publication)
    control_file.write_text("not-a-directory\n", encoding="utf-8")
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)
    monkeypatch.setattr(main_module, "DAILY_FUNDS_CONTROL_DIR", control_file)

    response = client.post("/ops/api/daily-funds/history-probe", headers=_same_origin_headers())

    assert response.status_code == 503
    assert response.headers["x-kmfa-daily-funds-probe"] == "v1"
    assert response.json() == {"detail": "daily_funds_history_probe_control_unavailable"}


def test_private_daily_funds_projection_range_and_no_raw_leak(tmp_path, monkeypatch):
    publication = tmp_path / "publication"
    control = tmp_path / "control"
    _write_projection(publication)
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)
    monkeypatch.setattr(main_module, "DAILY_FUNDS_CONTROL_DIR", control)

    response = client.get("/ops/api/daily-funds/summary", params={"range": "custom", "from": "2026-07-24", "to": "2026-07-30"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["range"] == "custom"
    assert payload["total_available_fen"] == 157_000_000
    assert len(payload["points"]) == 3
    assert payload["range_health"] == {
        "expected_days": 7,
        "published_days": 3,
        "expected_dates": ["2026-07-24", "2026-07-25", "2026-07-26", "2026-07-27", "2026-07-28", "2026-07-29", "2026-07-30"],
        "missing_dates": ["2026-07-24", "2026-07-25", "2026-07-26", "2026-07-27"],
        "coverage_gap_dates": ["2026-07-28"],
    }
    assert payload["today"] == {
        "inflow_fen": 25_000_000,
        "outflow_fen": 18_000_000,
        "adjustment_fen": 0,
        "internal_transfer_count": 0,
        "net_change_fen": 7_000_000,
    }
    assert payload["account_breakdown"] == [{"account_alias": "••••ffff", "ending_available_fen": 157_000_000}]
    source_health = client.get("/ops/api/daily-funds/source-health").json()
    assert source_health["backup_state"] == "OK"
    assert source_health["has_trusted_publication"] is True
    assert source_health["source_families"] == {"required": 2, "published": 2}
    assert source_health["source_discovery"] == {
        "状态": "COMPLETE_PAIR_READY",
        "说明": "账户与流水已成对，等待后续勾稽与发布",
    }
    assert "machine_code" not in source_health and "publication_id" not in source_health
    body = response.text.lower()
    assert "attachment" not in body and "openmessage" not in body and "raw/messages" not in body

    data = client.get("/ops/api/daily-funds/transactions").json()
    assert data["pagination"]["total"] == 2
    assert {item["transaction_ref"] for item in data["items"]} == {"99999999", "ffffffff"}
    assert all("source_version" not in item and "message_id_hash" not in item for item in data["items"])
    anchored = client.get("/ops/api/daily-funds/summary", params={"range": "30d"}).json()
    assert anchored["from"] == "2026-07-01" and anchored["to"] == "2026-07-30"
    assert client.get("/api/daily-funds/summary", params={"range": "custom", "from": "2026-07-30", "to": "2026-07-30"}).status_code == 422


def test_unpublished_daily_funds_projection_is_values_free_but_usable(tmp_path, monkeypatch):
    publication = tmp_path / "publication"
    publication.mkdir()
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)

    summary = client.get("/ops/api/daily-funds/summary", params={"range": "30d"})
    timeseries = client.get("/ops/api/daily-funds/timeseries", params={"range": "30d"})

    assert summary.status_code == 200
    assert summary.json() == {
        "data_available": False,
        "range": "30d",
        "from": None,
        "to": None,
        "scope": "global",
        "granularity": "daily",
        "range_health": {
            "expected_days": 0,
            "published_days": 0,
            "expected_dates": [],
            "missing_dates": [],
            "coverage_gap_dates": [],
        },
        "publication": None,
        "total_available_fen": None,
        "risk_label": None,
        "dynamic_flag": None,
        "by_company_ending_fen": [],
        "by_bank_ending_fen": [],
        "account_breakdown": [],
        "today": {},
        "top_inflows": [],
        "top_outflows": [],
        "points": [],
    }
    assert timeseries.status_code == 200
    time_payload = timeseries.json()
    assert time_payload["data_available"] is False
    assert time_payload["points"] == []
    assert time_payload["range_health"]["expected_days"] == 0
    assert time_payload["thresholds"]["fixed"]["hard_fen"] == 60_000_000
    assert time_payload["thresholds"]["fixed"]["soft_fen"] == 120_000_000
    assert all(item["active"] is False for item in time_payload["thresholds"]["floating"])
    assert client.get("/ops/api/daily-funds/summary", params={"range": "unknown"}).status_code == 422
    assert client.get(
        "/ops/api/daily-funds/timeseries",
        params={"range": "custom", "from": "2026-07-30", "to": "2026-07-30"},
    ).status_code == 422


def test_daily_funds_projection_rejects_source_pair_and_runtime_contract_drift(tmp_path, monkeypatch):
    def load_current(root: Path) -> dict:
        return json.loads((root / "current.json").read_text(encoding="utf-8"))

    def write_current(root: Path, payload: dict) -> None:
        (root / "current.json").write_text(json.dumps(payload), encoding="utf-8")

    mutations = (
        lambda current: current["publication"]["source_versions"].append({"source_version": "c" * 64}),
        lambda current: current["transactions"].__setitem__(1, {
            **current["transactions"][1], "source_version": "b" * 64,
        }),
        lambda current: current["transactions"].__setitem__(0, {
            **current["transactions"][0], "source_version": "c" * 64,
        }),
        lambda current: current.__setitem__("untrusted_raw_extension", "must-not-be-ignored"),
        lambda current: current.__setitem__("runtime", {"oci_backup_state": "OK"}),
        lambda current: current.__setitem__("runtime", {
            "oci_backup_state": "OK", "git_publication_commit_sha": "f" * 40,
        }),
        lambda current: current["publication"]["threshold_snapshot"].__setitem__("untrusted_extension", "must-not-pass"),
        lambda current: current["publication"]["threshold_snapshot"]["floating"][0].__setitem__("coverage", "0.99"),
        lambda current: current["publication"]["threshold_snapshot"].__setitem__("fixed_risk", "关注"),
        lambda current: current["summary"].__setitem__("risk_label", "关注"),
    )
    for index, mutate in enumerate(mutations):
        publication = tmp_path / f"publication-{index}"
        _write_projection(publication)
        current = load_current(publication)
        mutate(current)
        write_current(publication, current)
        monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)
        response = client.get("/ops/api/daily-funds/summary")
        assert response.status_code == 503


def test_daily_funds_projection_accepts_pending_and_restored_worker_shapes(tmp_path, monkeypatch):
    publication = tmp_path / "publication"
    _write_projection(publication)
    current = json.loads((publication / "current.json").read_text(encoding="utf-8"))
    del current["runtime"]
    (publication / "current.json").write_text(json.dumps(current), encoding="utf-8")
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)
    assert client.get("/ops/api/daily-funds/summary").json()["publication"]["oci_backup_state"] == "PENDING"

    current["runtime"] = {"oci_backup_state": "OK", "restored_at": "2026-07-30T12:06:00Z"}
    (publication / "current.json").write_text(json.dumps(current), encoding="utf-8")
    assert client.get("/ops/api/daily-funds/summary").json()["publication"]["oci_backup_state"] == "OK"

    current["runtime"] = {"oci_backup_state": "LAG", "git_publication_commit_sha": "f" * 40}
    (publication / "current.json").write_text(json.dumps(current), encoding="utf-8")
    assert client.get("/ops/api/daily-funds/summary").json()["publication"]["oci_backup_state"] == "LAG"


def test_daily_funds_projection_paths_require_access_in_production(tmp_path, monkeypatch):
    publication = tmp_path / "publication"
    _write_projection(publication)
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)
    monkeypatch.setenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", "1")
    monkeypatch.setenv("KMFA_CLOUDFLARE_ACCESS_TEAM_DOMAIN", "test-team.cloudflareaccess.com")
    monkeypatch.setenv("KMFA_CLOUDFLARE_ACCESS_AUD", "daily-funds-test-aud")

    assert client.get("/api/daily-funds/summary").status_code == 403
    assert client.get("/ops/api/daily-funds/summary").status_code == 403
    assert client.get("/ops/api/daily-funds/cashflow-observations").status_code == 403
    assert client.get("/ops/daily-funds").status_code == 403


def test_daily_funds_projection_paths_are_available_under_owner_public_override(tmp_path, monkeypatch):
    publication = tmp_path / "publication"
    _write_projection(publication)
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)
    monkeypatch.setenv("KMFA_PRIVATE_OPS_REQUIRE_ACCESS", "0")

    assert client.get("/api/daily-funds/summary").status_code == 200
    assert client.get("/ops/api/daily-funds/summary").status_code == 200
    assert client.get("/ops/api/daily-funds/cashflow-observations").status_code == 200
    assert client.get("/ops/daily-funds").status_code == 200


def test_daily_funds_status_is_visible_in_existing_schedule_center(tmp_path, monkeypatch):
    publication = tmp_path / "publication"
    _write_projection(publication)
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)
    monkeypatch.setattr(main_module, "SKILL_LEDGER_PATH", tmp_path / "missing-ledger.jsonl")
    response = client.get("/api/排程健康")
    assert response.status_code == 200
    daily = next(row for row in response.json()["逐项"] if row["技能"] == "daily-funds")
    assert daily["跑过"] is True
    assert daily["成功"] is True
    assert daily["失败码"] is None
    assert daily["投递开关"] is None
    assert daily["每日资金状态"]["状态"] == "已更新"
    assert daily["每日资金状态"]["有效业务日期"] == "2026-07-30"
    assert daily["每日资金状态"]["排程"] == main_module.DAILY_FUNDS_STATUS_SCHEDULES
    flow = daily["每日资金状态"]["业务流"]
    assert flow["部署"] == {
        "运行": "RUNTIME_AUDITED",
        "实例": "OBSERVED",
        "身份": "UNKNOWN",
        "最近运行审计": "2026-07-30T12:04:00Z",
    }
    assert flow["上线后观察"]["状态"] == "OBSERVING"
    assert flow["上线后观察"]["已完成业务日"] == 1
    assert flow["上线后观察"]["每日对照"] == [{
        "业务日期": "2026-07-30",
        "观察时间": "2026-07-30T12:05:00Z",
        "对照": "D1_AND_POINTER_VERIFIED",
        "覆盖": "DIRECT_OBSERVATION",
        "金额": "ZERO_FEN",
        "阈值": "VALID",
        "取数": "COMPLETE_PAIR",
        "重复": "SOURCE_VERSION_UNIQUE",
        "备份": "OK",
        "恢复": "NOT_YET_RUN",
        "延迟分钟": 5,
    }]
    assert flow["运行回执"]["历史轮询"] == {
        "状态": "成功",
        "结果": "VALID_PUBLISHED",
        "最近一次": "2026-07-30T12:05:00Z",
    }
    assert flow["运行回执"]["认证探测"] == {
        "状态": "成功",
        "结果": "AUTH_OK",
        "最近一次": "2026-07-30T12:05:30Z",
    }
    assert flow["运行回执"]["R2 零费用守卫"] == {
        "状态": "成功",
        "结果": "R2_ZERO_CHARGE_GUARD_OK",
        "最近一次": "2026-07-30T12:06:00Z",
    }
    assert flow["来源诊断"] == {
        "状态": "COMPLETE_PAIR_READY",
        "说明": "账户与流水已成对，等待后续勾稽与发布",
    }
    assert flow["附件能力"] == {
        "状态": "待复核",
        "已支持附件数": 1,
        "待复核附件数": 2,
        "正式候选待复核附件数": 2,
        "归档待分类附件数": 0,
        "待复核原因": [{"类别": "文件格式或表格结构未通过确定性校验", "数量": 2}],
        "最近观测": "2026-07-30T12:05:00Z",
    }
    assert "group-fixture" not in response.text and "attachment-fixture" not in response.text
    assert "message-fixture" not in response.text
    assert response.json()["每日资金"]["业务流"]["部署"]["身份"] == "UNKNOWN"

    # The public health endpoint cannot read the shared skills ledger as a
    # proxy for this isolated worker.  It may expose only the safe latest
    # history-poll and historical-backfill receipts, never the projection,
    # raw source, account data or private operation history.
    public = client.get("/public-api/技能健康")
    assert public.status_code == 200
    public_daily = next(row for row in public.json()["技能"] if row["技能"] == "daily-funds")
    assert isinstance(public_daily["距今小时"], float)
    assert {key: value for key, value in public_daily.items() if key != "距今小时"} == {
        "技能": "daily-funds",
        "最近一次": "2026-07-30T12:05:00Z",
        "退出码": 0,
        "成功": True,
        "运行次数": 1,
        "运行计数口径": "仅保留最近一次历史轮询回执，非累计历史次数",
        "失败码": None,
        "本次状态": "VALID_PUBLISHED",
        "运行中": False,
        "历史回填": {
            "最近一次": "2026-07-30T12:06:30Z",
            "退出码": 0,
            "成功": True,
            "运行次数": 1,
            "运行计数口径": "仅保留最近一次历史回填回执，非累计历史次数",
            "失败码": None,
            "本次状态": "BACKFILL_EMPTY_WINDOW",
            "运行中": False,
        },
    }
    assert "group-fixture" not in public.text
    assert "attachment-fixture" not in public.text
    assert "message-fixture" not in public.text
    assert "backfill-fixture" not in public.text


def test_daily_funds_embedded_source_identity_is_partial_and_fails_closed(tmp_path, monkeypatch):
    publication = tmp_path / "publication"
    _write_projection(publication)
    source_commit = "1" * 40
    marker = tmp_path / "app-source-commit"
    marker.write_text(source_commit + "\n", encoding="ascii")
    worker_fingerprint = hashlib.sha256(source_commit.encode("ascii")).hexdigest()
    flow_path = publication / "flow_state.json"
    flow = json.loads(flow_path.read_text(encoding="utf-8"))
    flow["deployment"].update({
        "identity_state": "BUILD_SOURCE_COMMIT_EMBEDDED",
        "source_commit_fingerprint": worker_fingerprint,
    })
    flow_path.write_text(json.dumps(flow), encoding="utf-8")
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)
    monkeypatch.setattr(main_module, "DAILY_FUNDS_APP_BUILD_SOURCE_COMMIT_FILE", marker)
    monkeypatch.setattr(main_module, "SKILL_LEDGER_PATH", tmp_path / "missing-ledger.jsonl")

    response = client.get("/api/排程健康")
    assert response.status_code == 200
    deployment = response.json()["每日资金"]["业务流"]["部署"]
    assert deployment["身份"] == "SOURCE_COMMIT_MATCHED_IMAGE_DIGEST_UNKNOWN"
    assert source_commit not in response.text
    assert worker_fingerprint not in response.text

    flow["deployment"]["source_commit_fingerprint"] = hashlib.sha256(("2" * 40).encode("ascii")).hexdigest()
    flow_path.write_text(json.dumps(flow), encoding="utf-8")
    assert main_module._daily_funds_flow_state()["部署"]["身份"] == "SOURCE_COMMIT_FINGERPRINT_MISMATCH"

    marker.write_text("UNKNOWN\n", encoding="ascii")
    assert main_module._daily_funds_flow_state()["部署"]["身份"] == "UNKNOWN"


def test_daily_funds_status_keeps_weekend_observer_out_of_workday_progress(tmp_path, monkeypatch):
    publication = tmp_path / "publication"
    _write_projection(publication)
    flow_path = publication / "flow_state.json"
    flow = json.loads(flow_path.read_text(encoding="utf-8"))
    flow["post_deploy_observer"].update({
        "state": "WAITING_FOR_NEXT_BUSINESS_DATE",
        "last_comparison": "NON_WORKING_DAY",
        "completed_business_days": 0,
        "comparisons": [],
    })
    flow_path.write_text(json.dumps(flow), encoding="utf-8")
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)
    monkeypatch.setattr(main_module, "SKILL_LEDGER_PATH", tmp_path / "missing-ledger.jsonl")

    response = client.get("/api/排程健康")
    daily = next(row for row in response.json()["逐项"] if row["技能"] == "daily-funds")
    observer = daily["每日资金状态"]["业务流"]["上线后观察"]
    assert observer["状态"] == "WAITING_FOR_NEXT_BUSINESS_DATE"
    assert observer["最近对照"] == "NON_WORKING_DAY"
    assert observer["已完成业务日"] == 0


def test_daily_funds_status_schema_or_schedule_drift_fails_closed(tmp_path, monkeypatch):
    mutations = (
        lambda status: status.__setitem__("untrusted_raw_extension", "group-fixture"),
        lambda status: status["schedules"].__setitem__("untrusted_schedule", "sender-fixture"),
    )
    for index, mutate in enumerate(mutations):
        publication = tmp_path / f"publication-{index}"
        _write_projection(publication)
        status_path = publication / "status.json"
        status = json.loads(status_path.read_text(encoding="utf-8"))
        mutate(status)
        status_path.write_text(json.dumps(status), encoding="utf-8")
        monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)
        monkeypatch.setattr(main_module, "SKILL_LEDGER_PATH", tmp_path / "missing-ledger.jsonl")

        response = client.get("/api/排程健康")
        daily = next(row for row in response.json()["逐项"] if row["技能"] == "daily-funds")
        status_view = daily["每日资金状态"]
        assert status_view["状态"] == "需处理"
        assert status_view["有效业务日期"] is None
        assert status_view["最近验证"] is None
        assert status_view["备份"] == "UNKNOWN"
        assert status_view["排程"] == {}
        assert status_view["业务流"]["业务流"]["状态"] == "需处理"
        assert response.json()["每日资金"]["machine_code"] == "STATUS_INVALID"
        assert "group-fixture" not in response.text and "sender-fixture" not in response.text


def test_daily_funds_schedule_does_not_treat_auth_success_as_source_poll_success(tmp_path, monkeypatch):
    """The source-poll receipt remains the primary scheduler row."""

    publication = tmp_path / "publication"
    _write_projection(publication)
    (publication / "current.json").unlink()
    status_path = publication / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status.update({"human_status": "需处理", "machine_code": "AUTH_OK", "updated_at": "2026-08-02T10:02:00Z"})
    status_path.write_text(json.dumps(status), encoding="utf-8")
    flow_path = publication / "flow_state.json"
    flow = json.loads(flow_path.read_text(encoding="utf-8"))
    flow["business_flow"].update({"stage": "POLL_NEEDS_ATTENTION", "machine_code": "SOURCE_MATCH_ZERO", "publication_present": False})
    flow["operations"]["poll"] = {
        "state": "FAILED", "code": "SOURCE_MATCH_ZERO", "finished_at": "2026-08-02T10:00:00Z",
    }
    flow["operations"]["auth-probe"] = {
        "state": "SUCCEEDED", "code": "AUTH_OK", "finished_at": "2026-08-02T10:02:00Z",
    }
    flow_path.write_text(json.dumps(flow), encoding="utf-8")
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)
    monkeypatch.setattr(main_module, "SKILL_LEDGER_PATH", tmp_path / "missing-ledger.jsonl")

    response = client.get("/api/排程健康")
    daily = next(row for row in response.json()["逐项"] if row["技能"] == "daily-funds")

    assert daily["成功"] is False
    assert daily["失败码"] == "SOURCE_MATCH_ZERO"
    assert daily["每日资金状态"]["状态"] == "需处理"
    assert daily["每日资金状态"]["业务流"]["运行回执"]["认证探测"]["状态"] == "成功"


def test_daily_funds_schedule_exposes_an_inflight_poll_without_guessing_success(tmp_path, monkeypatch):
    publication = tmp_path / "publication"
    _write_projection(publication)
    flow_path = publication / "flow_state.json"
    flow = json.loads(flow_path.read_text(encoding="utf-8"))
    flow["operations"]["poll"] = {
        "state": "RUNNING", "code": "POLL_RUNNING", "started_at": "2026-08-02T11:15:00Z",
    }
    flow_path.write_text(json.dumps(flow), encoding="utf-8")
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)
    monkeypatch.setattr(main_module, "SKILL_LEDGER_PATH", tmp_path / "missing-ledger.jsonl")

    response = client.get("/api/排程健康")
    daily = next(row for row in response.json()["逐项"] if row["技能"] == "daily-funds")

    assert daily["跑过"] is True
    assert daily["成功"] is None
    assert daily["运行中"] is True
    assert daily["失败码"] is None
    assert daily["最近一次"] == "2026-08-02T11:15:00Z"
    assert daily["每日资金状态"]["业务流"]["运行回执"]["历史轮询"] == {
        "状态": "处理中",
        "结果": "POLL_RUNNING",
        "最近一次": "2026-08-02T11:15:00Z",
    }


def test_daily_funds_attachment_capability_summary_fails_closed_on_malformed_row(tmp_path, monkeypatch):
    publication = tmp_path / "publication"
    _write_projection(publication)
    flow_path = publication / "flow_state.json"
    flow = json.loads(flow_path.read_text(encoding="utf-8"))
    flow["attachment_capabilities"][0]["count"] = "1"
    flow["business_flow"]["stage"] = "PARSER_NEEDS_REVIEW"
    flow["source_discovery"] = {"state": "untrusted-source-state"}
    flow_path.write_text(json.dumps(flow), encoding="utf-8")
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)

    source_health = client.get("/ops/api/daily-funds/source-health").json()
    assert source_health["parser_capability"] == {
        "状态": "UNKNOWN",
        "已支持附件数": 0,
        "待复核附件数": 0,
        "正式候选待复核附件数": 0,
        "归档待分类附件数": 0,
        "待复核原因": [],
        "最近观测": None,
    }
    assert source_health["source_discovery"] == {"状态": "UNKNOWN", "说明": "未验证"}
    status_center = client.get("/api/排程健康").json()
    daily = next(row for row in status_center["逐项"] if row["技能"] == "daily-funds")
    assert daily["每日资金状态"]["业务流"]["业务流"]["阶段"] == "PARSER_NEEDS_REVIEW"


def test_daily_funds_source_health_exposes_values_free_historical_backfill_coverage(tmp_path, monkeypatch):
    publication = tmp_path / "publication"
    _write_projection(publication)
    flow_path = publication / "flow_state.json"
    flow = json.loads(flow_path.read_text(encoding="utf-8"))
    flow["historical_backfill"] = {
        "state": "IN_PROGRESS",
        "window_days": 360,
        "completed_days": 196,
        "remaining_days": 164,
        "private_cursor_must_not_escape": "cursor-fixture",
    }
    flow["operations"]["backfill"] = {
        "state": "FAILED",
        "code": "DWS_AUTH_REQUIRED",
        "finished_at": "2026-08-02T10:05:00Z",
        "private_detail_must_not_escape": "backfill-fixture",
    }
    flow_path.write_text(json.dumps(flow), encoding="utf-8")
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)

    response = client.get("/ops/api/daily-funds/source-health")

    assert response.status_code == 200
    assert response.json()["historical_backfill"] == {
        "状态": "进行中",
        "窗口天数": 360,
        "已覆盖天数": 196,
        "待覆盖天数": 164,
        "最近作业": {
            "状态": "失败",
            "结果": "DWS_AUTH_REQUIRED",
            "最近一次": "2026-08-02T10:05:00Z",
        },
    }
    assert "cursor-fixture" not in response.text
    assert "backfill-fixture" not in response.text


def test_daily_funds_source_discovery_distinguishes_missing_fact_gates(tmp_path, monkeypatch):
    publication = tmp_path / "publication"
    _write_projection(publication)
    flow_path = publication / "flow_state.json"
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)

    expected = {
        "ACCOUNT_SNAPSHOT_MISSING": "附件已取得，缺少账户余额事实",
        "TRANSACTION_FACT_MISSING": "附件已取得，缺少资金流水事实",
        "SOURCE_FACT_DATE_MISMATCH": "附件已取得，但账户与流水业务日期未成对",
        "GENERIC_DOCUMENT_UNRESOLVED": "已归档候选附件，尚未确定为资金账户或流水",
    }
    for state, label in expected.items():
        flow = json.loads(flow_path.read_text(encoding="utf-8"))
        flow["source_discovery"] = {"state": state}
        flow_path.write_text(json.dumps(flow), encoding="utf-8")
        source_health = client.get("/ops/api/daily-funds/source-health").json()
        assert source_health["source_discovery"] == {"状态": state, "说明": label}


def test_attachment_capability_exposes_fixed_ocr_category_not_parser_code(tmp_path, monkeypatch):
    publication = tmp_path / "publication"
    _write_projection(publication)
    flow_path = publication / "flow_state.json"
    flow = json.loads(flow_path.read_text(encoding="utf-8"))
    flow["attachment_capabilities"][1].update({
        "family": "资金明细",
        "code": "OCR_GENERIC_HEADER_SCHEMA_MISSING",
    })
    flow_path.write_text(json.dumps(flow), encoding="utf-8")
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)

    response = client.get("/ops/api/daily-funds/source-health")
    assert response.status_code == 200
    capability = response.json()["parser_capability"]
    assert capability["待复核原因"] == [{"类别": "图片表头未形成余额或流水完整结构", "数量": 2}]
    assert "OCR_GENERIC_HEADER_SCHEMA_MISSING" not in response.text


def test_generic_attachment_capability_stays_archived_until_a_fact_schema_is_proven(tmp_path, monkeypatch):
    """A generic label is a private archive class, never a cashflow claim."""

    publication = tmp_path / "publication"
    _write_projection(publication)
    (publication / "current.json").unlink()
    flow_path = publication / "flow_state.json"
    flow = json.loads(flow_path.read_text(encoding="utf-8"))
    flow["attachment_capabilities"][1].update({
        "family": "资金明细",
        "code": "GENERIC_SOURCE_SCHEMA_UNRESOLVED",
    })
    flow["source_discovery"] = {"state": "GENERIC_DOCUMENT_UNRESOLVED"}
    flow_path.write_text(json.dumps(flow), encoding="utf-8")
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)

    response = client.get("/ops/api/daily-funds/source-health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["parser_capability"] == {
        "状态": "归档待分类",
        "已支持附件数": 1,
        "待复核附件数": 2,
        "正式候选待复核附件数": 0,
        "归档待分类附件数": 2,
        "待复核原因": [{"类别": "通用表格未形成余额或流水完整结构", "数量": 2}],
        "最近观测": "2026-07-30T12:05:00Z",
    }
    assert payload["source_discovery"] == {
        "状态": "GENERIC_DOCUMENT_UNRESOLVED",
        "说明": "已归档候选附件，尚未确定为资金账户或流水",
    }
    assert "不写入收支图表" in payload["message"]
    assert "GENERIC_SOURCE_SCHEMA_UNRESOLVED" not in response.text


def test_archived_needs_review_is_visible_without_trusted_money(tmp_path, monkeypatch):
    """A verified raw PNG must stay actionable, rather than degrading to UNKNOWN."""

    publication = tmp_path / "publication"
    _write_projection(publication)
    (publication / "current.json").unlink()
    flow_path = publication / "flow_state.json"
    flow = json.loads(flow_path.read_text(encoding="utf-8"))
    flow["business_flow"]["stage"] = "BACKFILL_ARCHIVED_NEEDS_REVIEW"
    flow_path.write_text(json.dumps(flow), encoding="utf-8")
    status_path = publication / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["human_status"] = "需处理"
    status["machine_code"] = "UNSUPPORTED_ATTACHMENT"
    status_path.write_text(json.dumps(status), encoding="utf-8")
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)
    monkeypatch.setattr(main_module, "SKILL_LEDGER_PATH", tmp_path / "missing-ledger.jsonl")

    source_health = client.get("/ops/api/daily-funds/source-health").json()
    assert source_health["has_trusted_publication"] is False
    assert source_health["human_status"] == "需处理"
    assert source_health["parser_capability"] == {
        "状态": "待复核",
        "已支持附件数": 1,
        "待复核附件数": 2,
        "正式候选待复核附件数": 2,
        "归档待分类附件数": 0,
        "待复核原因": [{"类别": "文件格式或表格结构未通过确定性校验", "数量": 2}],
        "最近观测": "2026-07-30T12:05:00Z",
    }
    assert "待确定性解析复核" in source_health["message"]
    assert "UNSUPPORTED_ATTACHMENT" not in json.dumps(source_health)
    assert "文件格式或表格结构未通过确定性校验" in json.dumps(source_health, ensure_ascii=False)
    thresholds = client.get("/ops/api/daily-funds/thresholds")
    assert thresholds.status_code == 200
    threshold_payload = thresholds.json()
    assert threshold_payload["data_available"] is False
    assert threshold_payload["active"]["fixed"] == {
        "hard_fen": main_module.DAILY_FUNDS_HARD_THRESHOLD_FEN,
        "soft_fen": main_module.DAILY_FUNDS_SOFT_THRESHOLD_FEN,
    }
    assert all(
        line["active"] is False
        and line["threshold_fen"] is None
        and line["reason"] == "尚无足够已验证日余额"
        for line in threshold_payload["active"]["floating"]
    )
    assert "ending_available_fen" not in thresholds.text
    status_center = client.get("/api/排程健康").json()
    daily = next(row for row in status_center["逐项"] if row["技能"] == "daily-funds")
    assert daily["每日资金状态"]["业务流"]["业务流"]["阶段"] == "BACKFILL_ARCHIVED_NEEDS_REVIEW"


def test_daily_funds_flow_remains_in_the_same_status_center_when_ledger_exists(tmp_path, monkeypatch):
    publication = tmp_path / "publication"
    ledger = tmp_path / "skill-ledger.jsonl"
    _write_projection(publication)
    ledger.write_text(json.dumps({
        "skill": "daily-routine-check", "ts": "2026-07-30T12:00:00+08:00", "rc": 0,
    }) + "\n", encoding="utf-8")
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)
    monkeypatch.setattr(main_module, "SKILL_LEDGER_PATH", ledger)
    response = client.get("/api/排程健康")
    assert response.status_code == 200
    assert response.json()["每日资金"]["业务流"]["上线后观察"]["已完成业务日"] == 1
    assert response.json()["每日资金"]["业务流"]["业务流"]["状态"] == "已更新"


def test_private_threshold_request_uses_optimistic_revision(tmp_path, monkeypatch):
    publication = tmp_path / "publication"
    control = tmp_path / "control"
    _write_projection(publication)
    control.mkdir()
    (control / "active_threshold.json").write_text(json.dumps({"revision": "old"}), encoding="utf-8")
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)
    monkeypatch.setattr(main_module, "DAILY_FUNDS_CONTROL_DIR", control)
    body = {"mode": "numeric", "amount_fen": 90_000_000, "reason": "fixture", "expected_revision": "old"}
    accepted = client.put("/api/daily-funds/thresholds", json=body)
    assert accepted.status_code == 200 and accepted.json()["accepted"] is True
    assert (control / "threshold_request.json").is_file()
    request = json.loads((control / "threshold_request.json").read_text(encoding="utf-8"))
    assert request["actor"] == "kmfa_private_owner_ui"
    assert request["reason"] == "fixture"
    conflict = client.put("/api/daily-funds/thresholds", json={**body, "expected_revision": "wrong"})
    assert conflict.status_code == 409


def test_threshold_read_model_exposes_versioned_redacted_audit(tmp_path, monkeypatch):
    publication = tmp_path / "publication"
    control = tmp_path / "control"
    _write_projection(publication)
    control.mkdir()
    old = {
        "schema_version": "kmfa.daily_funds.threshold_control.v1",
        "mode": "disabled",
        "revision": "1" * 64,
        "applied_at": "2026-07-29T12:00:00Z",
        "actor": "kmfa_private_owner_ui",
        "reason": "旧配置",
    }
    active = {
        "schema_version": "kmfa.daily_funds.threshold_control.v1",
        "mode": "numeric",
        "revision": "2" * 64,
        "applied_at": "2026-07-30T12:00:00Z",
        "actor": "kmfa_private_owner_ui",
        "reason": "提高观察线",
        "amount_fen": 90_000_000,
    }
    (control / "active_threshold.json").write_text(json.dumps(active), encoding="utf-8")
    audit = {
        "schema_version": "kmfa.daily_funds.threshold_audit.v1",
        "revision": active["revision"],
        "actor": "kmfa_private_owner_ui",
        "changed_at": active["applied_at"],
        "old_value": old,
        "new_value": active,
        "reason": active["reason"],
        "rollback_version": old["revision"],
    }
    (control / "threshold_audit.jsonl").write_text(json.dumps(audit) + "\n", encoding="utf-8")
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)
    monkeypatch.setattr(main_module, "DAILY_FUNDS_CONTROL_DIR", control)

    response = client.get("/ops/api/daily-funds/thresholds")
    assert response.status_code == 200
    payload = response.json()
    assert payload["data_available"] is True
    assert payload["control"] == {
        "mode": "numeric",
        "revision": "2" * 64,
        "applied_at": "2026-07-30T12:00:00Z",
        "actor": "kmfa_private_owner_ui",
        "reason": "提高观察线",
        "amount_fen": 90_000_000,
    }
    assert payload["control_audit"]["available"] is True
    assert payload["control_audit"]["entries"][0]["old_value"]["mode"] == "disabled"
    assert payload["control_audit"]["entries"][0]["rollback_version"] == "1" * 64
    assert "schema_version" not in response.text


def test_invalid_projection_is_not_rendered_as_trusted_money(tmp_path, monkeypatch):
    publication = tmp_path / "publication"
    _write_projection(publication)
    current_path = publication / "current.json"
    current = json.loads(current_path.read_text(encoding="utf-8"))
    current["daily_balances"][-1]["ending_available_fen"] = True
    current_path.write_text(json.dumps(current), encoding="utf-8")
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)

    response = client.get("/ops/api/daily-funds/summary")
    assert response.status_code == 503
    source_health = client.get("/ops/api/daily-funds/source-health").json()
    assert source_health["has_trusted_publication"] is False
    assert source_health["human_status"] == "需处理"
    assert source_health["backup_state"] == "UNKNOWN"
