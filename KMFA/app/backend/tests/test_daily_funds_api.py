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
                "source_version": "b" * 64,
                "message_id_hash": "a" * 64,
            },
        ],
        "runtime": {"oci_backup_state": "OK"},
    }
    status = {
        "human_status": "已更新",
        "machine_code": "VALID_PUBLISHED",
        "effective_business_date": "2026-07-30",
        "last_verified_at": "2026-07-30T12:00:00Z",
        "publication_id": "c" * 64,
        "updated_at": "2026-07-30T12:00:00Z",
        "schedules": {"history_poll": "*/15 * * * * Asia/Shanghai"},
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
            "effective_business_date": "2026-07-30",
            "last_verified_at": "2026-07-30T12:05:00Z",
            "last_status_at": "2026-07-30T12:05:00Z",
            "publication_present": True,
        },
        "attachment_capabilities": [
            {
                "family": "资金账户明细表",
                "suffix": ".csv",
                "declared_mime": "text/csv",
                "magic": "TEXT",
                "parser_version": "kmfa.daily_funds.parser.v2",
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
                "parser_version": "kmfa.daily_funds.parser.v2",
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
    assert flow["附件能力"] == {
        "状态": "待复核",
        "已支持附件数": 1,
        "待复核附件数": 2,
        "最近观测": "2026-07-30T12:05:00Z",
    }
    assert "group-fixture" not in response.text and "attachment-fixture" not in response.text
    assert response.json()["每日资金"]["业务流"]["部署"]["身份"] == "UNKNOWN"


def test_daily_funds_attachment_capability_summary_fails_closed_on_malformed_row(tmp_path, monkeypatch):
    publication = tmp_path / "publication"
    _write_projection(publication)
    flow_path = publication / "flow_state.json"
    flow = json.loads(flow_path.read_text(encoding="utf-8"))
    flow["attachment_capabilities"][0]["count"] = "1"
    flow["business_flow"]["stage"] = "PARSER_NEEDS_REVIEW"
    flow_path.write_text(json.dumps(flow), encoding="utf-8")
    monkeypatch.setattr(main_module, "DAILY_FUNDS_PUBLICATION_DIR", publication)

    source_health = client.get("/ops/api/daily-funds/source-health").json()
    assert source_health["parser_capability"] == {
        "状态": "UNKNOWN",
        "已支持附件数": 0,
        "待复核附件数": 0,
        "最近观测": None,
    }
    status_center = client.get("/api/排程健康").json()
    daily = next(row for row in status_center["逐项"] if row["技能"] == "daily-funds")
    assert daily["每日资金状态"]["业务流"]["业务流"]["阶段"] == "PARSER_NEEDS_REVIEW"


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
        "最近观测": "2026-07-30T12:05:00Z",
    }
    assert "待确定性解析复核" in source_health["message"]
    assert "UNSUPPORTED_ATTACHMENT" not in json.dumps(source_health)
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
