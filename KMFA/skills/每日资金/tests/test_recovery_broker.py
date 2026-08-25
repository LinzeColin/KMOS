"""Contracts for the fixed values-free daily-funds recovery broker."""

from __future__ import annotations

import base64
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from daily_funds.config import DailyFundsConfig
import daily_funds.recovery as recovery_module
from daily_funds.recovery import (
    ACTOR,
    REQUEST_FILE,
    REQUEST_SCHEMA,
    SESSION_FILE,
    SESSION_SCHEMA,
    DailyFundsRecoveryBroker,
)
from daily_funds.state import atomic_json_write

UTC = timezone.utc


def _config(tmp_path: Path) -> DailyFundsConfig:
    return DailyFundsConfig.from_env({
        "DAILY_FUNDS_STATE_DIR": str(tmp_path / "state"),
        "DAILY_FUNDS_PUBLICATION_DIR": str(tmp_path / "publication"),
        "DAILY_FUNDS_CONTROL_DIR": str(tmp_path / "control"),
        "DAILY_FUNDS_DWS_CONFIG_DIR": str(tmp_path / "dws-config"),
        "DAILY_FUNDS_DWS_KEYRING_DIR": str(tmp_path / "dws-keyring"),
        "DAILY_FUNDS_GROUP_ID": "group-fixture",
        "DAILY_FUNDS_SENDER_ID": "sender-fixture",
        "DAILY_FUNDS_GIT_SSH_KEY_B64": base64.b64encode(b"-----BEGIN TEST KEY-----").decode("ascii"),
    })


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _request(config: DailyFundsConfig, request_id: str) -> None:
    now = datetime.now(UTC)
    atomic_json_write(config.control_dir / REQUEST_FILE, {
        "schema_version": REQUEST_SCHEMA,
        "request_id": request_id,
        "action": "RECOVER",
        "actor": ACTOR,
        "requested_at": _timestamp(now),
        "expires_at": _timestamp(now + timedelta(minutes=50)),
    })


def test_recovery_runs_only_the_fixed_chain_and_persists_no_raw_result_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)
    calls: list[str] = []

    class FakeRuntime:
        def __init__(self, actual_config: DailyFundsConfig) -> None:
            assert actual_config is config

        def raw_archive_audit(self):
            calls.append("RAW_ARCHIVE_AUDIT")
            return {"ok": True, "code": "RAW_ARCHIVE_AUDITED", "private_raw": "must-not-escape"}

        def raw_coverage_repair(self, *, now: datetime):
            assert now.tzinfo is UTC
            calls.append("RAW_COVERAGE_REPAIR")
            return {"ok": True, "code": "RAW_COVERAGE_VERIFIED", "private_raw": "must-not-escape"}

        def raw_fact_replay(self, *, now: datetime):
            assert now.tzinfo is UTC
            calls.append("RAW_FACT_REPLAY")
            return {"ok": True, "code": "RAW_FACT_REPLAY_PUBLISHED", "private_raw": "must-not-escape"}

    monkeypatch.setattr(recovery_module, "DailyFundsRuntime", FakeRuntime)
    _request(config, "a" * 64)
    DailyFundsRecoveryBroker(config).run_once()

    session = json.loads((config.control_dir / SESSION_FILE).read_text(encoding="utf-8"))
    assert session == {
        "schema_version": SESSION_SCHEMA,
        "request_id": "a" * 64,
        "state": "SUCCEEDED",
        "machine_code": "DAILY_FUNDS_RECOVERY_PUBLISHED",
        "created_at": session["created_at"],
        "updated_at": session["updated_at"],
        "expires_at": session["expires_at"],
        "completed_steps": ["RAW_ARCHIVE_AUDIT", "RAW_COVERAGE_REPAIR", "RAW_FACT_REPLAY"],
        "active_step": "NONE",
    }
    assert calls == ["RAW_ARCHIVE_AUDIT", "RAW_COVERAGE_REPAIR", "RAW_FACT_REPLAY"]
    assert "must-not-escape" not in json.dumps(session)
    assert "group-fixture" not in json.dumps(session)
    assert "sender-fixture" not in json.dumps(session)
    assert not (config.control_dir / REQUEST_FILE).exists()


def test_recovery_waits_for_a_runtime_lock_then_resumes_at_the_same_fixed_step(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)
    calls: list[str] = []
    coverage_attempts = 0

    class FakeRuntime:
        def __init__(self, _actual_config: DailyFundsConfig) -> None:
            return None

        def raw_archive_audit(self):
            calls.append("RAW_ARCHIVE_AUDIT")
            return {"ok": True, "code": "RAW_ARCHIVE_AUDITED"}

        def raw_coverage_repair(self, *, now: datetime):
            nonlocal coverage_attempts
            assert now.tzinfo is UTC
            calls.append("RAW_COVERAGE_REPAIR")
            coverage_attempts += 1
            return (
                {"ok": False, "code": "RAW_COVERAGE_REPAIR_LOCK_HELD"}
                if coverage_attempts == 1
                else {"ok": True, "code": "RAW_COVERAGE_REPAIRED"}
            )

        def raw_fact_replay(self, *, now: datetime):
            assert now.tzinfo is UTC
            calls.append("RAW_FACT_REPLAY")
            return {"ok": True, "code": "RAW_FACT_REPLAY_PUBLISHED_NEEDS_REVIEW"}

    monkeypatch.setattr(recovery_module, "DailyFundsRuntime", FakeRuntime)
    _request(config, "b" * 64)
    broker = DailyFundsRecoveryBroker(config)
    broker.run_once()
    waiting = json.loads((config.control_dir / SESSION_FILE).read_text(encoding="utf-8"))
    assert waiting["state"] == "WAITING"
    assert waiting["machine_code"] == "DAILY_FUNDS_RECOVERY_WAITING_FOR_LOCK"
    assert waiting["completed_steps"] == ["RAW_ARCHIVE_AUDIT"]
    assert waiting["active_step"] == "RAW_COVERAGE_REPAIR"
    assert (config.control_dir / REQUEST_FILE).exists()

    broker.run_once()
    completed = json.loads((config.control_dir / SESSION_FILE).read_text(encoding="utf-8"))
    assert completed["state"] == "SUCCEEDED"
    assert completed["machine_code"] == "DAILY_FUNDS_RECOVERY_PUBLISHED_NEEDS_REVIEW"
    assert calls == ["RAW_ARCHIVE_AUDIT", "RAW_COVERAGE_REPAIR", "RAW_COVERAGE_REPAIR", "RAW_FACT_REPLAY"]


def test_recovery_classifies_no_complete_pair_without_exposing_runtime_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)

    class FakeRuntime:
        def __init__(self, _actual_config: DailyFundsConfig) -> None:
            return None

        def raw_archive_audit(self):
            return {"ok": True, "code": "RAW_ARCHIVE_AUDITED"}

        def raw_coverage_repair(self, *, now: datetime):
            assert now.tzinfo is UTC
            return {"ok": True, "code": "RAW_COVERAGE_VERIFIED"}

        def raw_fact_replay(self, *, now: datetime):
            assert now.tzinfo is UTC
            return {"ok": False, "code": "RAW_FACT_REPLAY_NO_COMPLETE_PAIR", "private_raw": "must-not-escape"}

    monkeypatch.setattr(recovery_module, "DailyFundsRuntime", FakeRuntime)
    _request(config, "c" * 64)
    DailyFundsRecoveryBroker(config).run_once()

    session = json.loads((config.control_dir / SESSION_FILE).read_text(encoding="utf-8"))
    assert session["state"] == "FAILED"
    assert session["machine_code"] == "DAILY_FUNDS_RECOVERY_NO_COMPLETE_PAIR"
    assert session["completed_steps"] == ["RAW_ARCHIVE_AUDIT", "RAW_COVERAGE_REPAIR"]
    assert session["active_step"] == "RAW_FACT_REPLAY"
    assert "must-not-escape" not in json.dumps(session)
    assert not (config.control_dir / REQUEST_FILE).exists()


def test_recovery_preserves_the_runtime_configuration_classification(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _config(tmp_path)

    class FakeRuntime:
        def __init__(self, _actual_config: DailyFundsConfig) -> None:
            return None

        def raw_archive_audit(self):
            return {"human_status": "需处理", "machine_code": "CONFIG_INVALID", "private_raw": "must-not-escape"}

    monkeypatch.setattr(recovery_module, "DailyFundsRuntime", FakeRuntime)
    _request(config, "d" * 64)
    DailyFundsRecoveryBroker(config).run_once()

    session = json.loads((config.control_dir / SESSION_FILE).read_text(encoding="utf-8"))
    assert session["state"] == "FAILED"
    assert session["machine_code"] == "DAILY_FUNDS_RECOVERY_CONFIG_INVALID"
    assert session["active_step"] == "RAW_ARCHIVE_AUDIT"
    assert "must-not-escape" not in json.dumps(session)


def test_recovery_rejects_malformed_control_input_before_constructing_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)
    constructed = False

    class UnexpectedRuntime:
        def __init__(self, *_args, **_kwargs) -> None:
            nonlocal constructed
            constructed = True
            raise AssertionError("malformed recovery input must not execute")

    monkeypatch.setattr(recovery_module, "DailyFundsRuntime", UnexpectedRuntime)
    atomic_json_write(config.control_dir / REQUEST_FILE, {"command": "not-a-recovery"})
    DailyFundsRecoveryBroker(config).run_once()

    assert constructed is False
    assert not (config.control_dir / REQUEST_FILE).exists()
    assert not (config.control_dir / SESSION_FILE).exists()


def test_entrypoint_supervises_the_fixed_recovery_broker() -> None:
    entrypoint = (ROOT / "entrypoint.sh").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "run_recovery_broker.py >/dev/null 2>&1" in entrypoint
    assert "RECOVERY_BROKER_PID" in entrypoint
    assert "run_recovery_broker.py" not in (ROOT / "crontab.txt").read_text(encoding="utf-8")
    assert "/opt/daily-funds/scripts/run_recovery_broker.py" in dockerfile
