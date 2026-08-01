"""Private daily-funds projection API: no raw source crosses the app boundary."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app import main as main_module
from app.main import app


client = TestClient(app)


def _write_projection(root: Path) -> None:
    root.mkdir(parents=True)
    current = {
        "schema_version": "kmfa.daily_funds.current_projection.v1",
        "publication": {
            "publication_id": "p" * 64,
            "business_date": "2026-07-30",
            "status": "VALID",
            "source_versions": [{"source_version": "a" * 64}, {"source_version": "b" * 64}],
            "reconciliation_difference_fen": 0,
            "threshold_snapshot": {
                "fixed": {"hard_fen": 60_000_000, "soft_fen": 120_000_000},
                "floating": [{"name": "three_month", "active": True, "threshold_fen": 100_000_000, "start": "2026-04-01", "end": "2026-06-30", "coverage": "1", "direct_observations": 90, "carried_forward_days": 0}],
            },
            "created_at": "2026-07-30T12:00:00Z",
            "git_commit_sha": "c" * 40,
            "d1_projection_version": "kmfa.daily_funds.d1.v1",
            "r2_manifest_sha256": "r" * 64,
            "oci_backup_state": "OK",
        },
        "summary": {
            "total_available_fen": 157_000_000,
            "risk_label": "正常",
            "dynamic_flag": None,
            "by_company_ending_fen": {"公司A": 157_000_000},
            "by_bank_ending_fen": {"银行A": 157_000_000},
            "account_ending_by_hash": {"h" * 64: 157_000_000},
        },
        "daily_balances": [
            {"business_date": "2026-07-29", "ending_available_fen": 150_000_000, "direct_observation": True, "coverage_gap": False},
            {"business_date": "2026-07-30", "ending_available_fen": 157_000_000, "direct_observation": True, "coverage_gap": False},
        ],
        "transactions": [{"transaction_key_hash": "t" * 64, "business_date": "2026-07-30", "inflow_fen": 25_000_000, "outflow_fen": 18_000_000, "adjustment_fen": 0, "internal_transfer": False}],
    }
    status = {
        "human_status": "已更新",
        "machine_code": "VALID_PUBLISHED",
        "effective_business_date": "2026-07-30",
        "last_verified_at": "2026-07-30T12:00:00Z",
        "publication_id": "p" * 64,
        "updated_at": "2026-07-30T12:00:00Z",
        "schedules": {"history_poll": "*/15 * * * * Asia/Shanghai"},
        "backup_state": "OK",
    }
    (root / "current.json").write_text(json.dumps(current), encoding="utf-8")
    (root / "status.json").write_text(json.dumps(status), encoding="utf-8")


def test_private_daily_funds_projection_range_and_no_raw_leak(tmp_path, monkeypatch):
    publication = tmp_path / "publication"
    control = tmp_path / "control"
    _write_projection(publication)
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)
    monkeypatch.setattr(main_module, "DAILY_FUNDS_CONTROL_DIR", control)

    response = client.get("/api/daily-funds/summary", params={"range": "custom", "from": "2026-07-24", "to": "2026-07-30"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["range"] == "custom"
    assert payload["total_available_fen"] == 157_000_000
    assert len(payload["points"]) == 2
    assert client.get("/api/daily-funds/source-health").json()["backup_state"] == "OK"
    body = response.text.lower()
    assert "attachment" not in body and "openmessage" not in body and "raw/messages" not in body

    data = client.get("/ops/api/daily-funds/transactions").json()
    assert data["pagination"]["total"] == 1
    assert data["items"][0]["transaction_key_hash"] == "t" * 64
    assert client.get("/api/daily-funds/summary", params={"range": "custom", "from": "2026-07-30", "to": "2026-07-30"}).status_code == 422


def test_daily_funds_status_is_visible_in_existing_schedule_center(tmp_path, monkeypatch):
    publication = tmp_path / "publication"
    _write_projection(publication)
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)
    monkeypatch.setattr(main_module, "SKILL_LEDGER_PATH", tmp_path / "missing-ledger.jsonl")
    response = client.get("/api/排程健康")
    assert response.status_code == 200
    daily = next(row for row in response.json()["逐项"] if row["技能"] == "daily-funds")
    assert daily["每日资金状态"]["状态"] == "已更新"
    assert daily["每日资金状态"]["有效业务日期"] == "2026-07-30"


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
