"""Contract tests for the fixed values-free cloud history probe broker."""

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
import daily_funds.history_probe as history_probe_module
from daily_funds.history_probe import (
    ACTOR,
    REQUEST_FILE,
    REQUEST_SCHEMA,
    SESSION_FILE,
    SESSION_SCHEMA,
    DailyFundsHistoryProbeBroker,
)
from daily_funds.ingestion import DwsPage, IngestionError
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
        "action": "PROBE",
        "actor": ACTOR,
        "requested_at": _timestamp(now),
        "expires_at": _timestamp(now + timedelta(minutes=10)),
    })


def test_history_probe_reuses_the_opaque_cursor_without_retaining_source_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)
    calls: list[tuple[datetime, datetime, str | None]] = []
    events: list[tuple[str, str, str]] = []

    class FakeClient:
        def __init__(self, actual_config, *, event_sink):
            assert actual_config is config
            assert callable(event_sink)

        def search(self, start: datetime, end: datetime, cursor: str | None) -> DwsPage:
            calls.append((start, end, cursor))
            self.event_sink("DWS", "HISTORY_SEARCH_ADVANCED", "OK")
            if cursor is None:
                return DwsPage(messages=(), next_cursor="opaque-page-2-cursor", has_more=True)
            assert cursor == "opaque-page-2-cursor"
            return DwsPage(messages=(), next_cursor=None, has_more=False)

    original_init = FakeClient.__init__

    def capture_init(self, actual_config, *, event_sink):
        original_init(self, actual_config, event_sink=event_sink)
        self.event_sink = event_sink

    monkeypatch.setattr(FakeClient, "__init__", capture_init)
    monkeypatch.setattr(history_probe_module, "DwsHistoryClient", FakeClient)
    _request(config, "a" * 64)
    broker = DailyFundsHistoryProbeBroker(config)
    monkeypatch.setattr(broker.state, "record_network_event", lambda *event: events.append(event))
    broker.run_once()

    session = json.loads((config.control_dir / SESSION_FILE).read_text(encoding="utf-8"))
    assert set(session) == {
        "schema_version", "request_id", "state", "machine_code", "created_at",
        "updated_at", "expires_at", "continuation_state", "cursor_transcript",
    }
    assert session == {
        "schema_version": SESSION_SCHEMA,
        "request_id": "a" * 64,
        "state": "COMPLETED",
        "machine_code": "DWS_HISTORY_PROBE_COMPLETED",
        "created_at": session["created_at"],
        "updated_at": session["updated_at"],
        "expires_at": session["expires_at"],
        "continuation_state": "SECOND_PAGE_TERMINAL",
        "cursor_transcript": "OPAQUE_CURSOR_REUSED_SECOND_PAGE_TERMINAL",
    }
    assert [call[2] for call in calls] == [None, "opaque-page-2-cursor"]
    assert all((end - start) == timedelta(hours=24) for start, end, _cursor in calls)
    assert events == [
        ("DWS_HISTORY_PROBE", "HISTORY_SEARCH_ADVANCED", "OK"),
        ("DWS_HISTORY_PROBE", "HISTORY_SEARCH_ADVANCED", "OK"),
    ]
    serialized = json.dumps(session)
    assert "group-fixture" not in serialized
    assert "sender-fixture" not in serialized
    assert "opaque-page-2-cursor" not in serialized
    assert not (config.control_dir / REQUEST_FILE).exists()


def test_history_probe_reports_a_bounded_second_page_without_claiming_terminal_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)

    class FakeClient:
        def __init__(self, _config, *, event_sink):
            assert callable(event_sink)

        def search(self, _start: datetime, _end: datetime, cursor: str | None) -> DwsPage:
            return DwsPage(messages=(), next_cursor="opaque-next" if cursor is None else "opaque-later", has_more=True)

    monkeypatch.setattr(history_probe_module, "DwsHistoryClient", FakeClient)
    _request(config, "b" * 64)
    DailyFundsHistoryProbeBroker(config).run_once()

    session = json.loads((config.control_dir / SESSION_FILE).read_text(encoding="utf-8"))
    assert session["state"] == "COMPLETED"
    assert session["continuation_state"] == "SECOND_PAGE_CONTINUES"
    assert session["cursor_transcript"] == "OPAQUE_CURSOR_REUSED_SECOND_PAGE_CONTINUES"
    assert session["machine_code"] == "DWS_HISTORY_PROBE_COMPLETED"


def test_history_probe_rejects_malformed_control_volume_input_without_constructing_a_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)
    constructed = False

    class UnexpectedClient:
        def __init__(self, *_args, **_kwargs):
            nonlocal constructed
            constructed = True
            raise AssertionError("malformed input must not reach DWS")

    monkeypatch.setattr(history_probe_module, "DwsHistoryClient", UnexpectedClient)
    atomic_json_write(config.control_dir / REQUEST_FILE, {"command": "never-accepted", "group": "not-accepted"})
    DailyFundsHistoryProbeBroker(config).run_once()

    assert constructed is False
    assert not (config.control_dir / REQUEST_FILE).exists()
    assert not (config.control_dir / SESSION_FILE).exists()


def test_history_probe_failure_is_sanitized_and_never_reflects_source_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)

    class FakeClient:
        def __init__(self, _config, *, event_sink):
            assert callable(event_sink)

        def search(self, _start: datetime, _end: datetime, _cursor: str | None) -> DwsPage:
            raise IngestionError("DWS_HISTORY_PERMISSION_DENIED")

    monkeypatch.setattr(history_probe_module, "DwsHistoryClient", FakeClient)
    _request(config, "c" * 64)
    DailyFundsHistoryProbeBroker(config).run_once()

    session = json.loads((config.control_dir / SESSION_FILE).read_text(encoding="utf-8"))
    assert session["state"] == "FAILED"
    assert session["machine_code"] == "DWS_HISTORY_PERMISSION_DENIED"
    assert session["continuation_state"] == "NOT_STARTED"
    assert session["cursor_transcript"] == "NOT_STARTED"
    assert "group-fixture" not in json.dumps(session)
    assert not (config.control_dir / REQUEST_FILE).exists()


def test_history_probe_configuration_failure_is_not_misreported_as_completion(tmp_path: Path) -> None:
    config = DailyFundsConfig.from_env({
        "DAILY_FUNDS_STATE_DIR": str(tmp_path / "state"),
        "DAILY_FUNDS_PUBLICATION_DIR": str(tmp_path / "publication"),
        "DAILY_FUNDS_CONTROL_DIR": str(tmp_path / "control"),
        "DAILY_FUNDS_DWS_CONFIG_DIR": str(tmp_path / "dws-config"),
        "DAILY_FUNDS_DWS_KEYRING_DIR": str(tmp_path / "dws-keyring"),
    })
    _request(config, "d" * 64)
    DailyFundsHistoryProbeBroker(config).run_once()

    session = json.loads((config.control_dir / SESSION_FILE).read_text(encoding="utf-8"))
    assert session["state"] == "FAILED"
    assert session["machine_code"] == "CONFIG_INVALID"
    assert session["continuation_state"] == "NOT_STARTED"
    assert session["cursor_transcript"] == "NOT_STARTED"


def test_entrypoint_supervises_the_fixed_history_probe_broker() -> None:
    entrypoint = (ROOT / "entrypoint.sh").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "run_history_probe_broker.py >/dev/null 2>&1" in entrypoint
    assert "HISTORY_PROBE_BROKER_PID" in entrypoint
    assert "run_history_probe_broker.py" not in (ROOT / "crontab.txt").read_text(encoding="utf-8")
    assert "/opt/daily-funds/scripts/run_history_probe_broker.py" in dockerfile
