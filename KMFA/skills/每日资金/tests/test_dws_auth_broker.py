from __future__ import annotations

import json
import io
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from daily_funds.auth_broker import (
    ACTOR,
    REQUEST_FILE,
    REQUEST_SCHEMA,
    SESSION_FILE,
    DailyFundsAuthBroker,
)
from daily_funds.config import DailyFundsConfig
import daily_funds.ingestion as ingestion_module
from daily_funds.ingestion import DwsAuthStatus, DwsDevicePrompt, DwsHistoryClient, IngestionError, _parse_dws_device_prompt
from daily_funds.state import atomic_json_write

UTC = timezone.utc


def test_daily_funds_dws_installer_pins_both_linux_runtime_architectures() -> None:
    installer = (ROOT / "install_dws.sh").read_text(encoding="utf-8")
    lock = (ROOT / "dws.sha256.lock").read_text(encoding="utf-8")
    assert 'Linux-x86_64)              ASSET="dws-linux-amd64.tar.gz" ;;' in installer
    assert 'Linux-aarch64|Linux-arm64) ASSET="dws-linux-arm64.tar.gz" ;;' in installer
    assert "DWS_PLATFORM_UNSUPPORTED" in installer
    assert 'DWS_VERSION="${DWS_VERSION:-v1.0.57}"' in installer
    assert "v1.0.57 dws-linux-amd64.tar.gz f113ce3654f21d1f9ecc7c196f815aeafbca54d377a347b244a15116c5cba698" in lock
    assert "v1.0.57 dws-linux-arm64.tar.gz 0bbe9c233a3ff585077bae1ac5000937c32d967846d14cc44c46f98d49b95ae2" in lock
    assert "v1.0.52 dws-linux-amd64.tar.gz b7dfd9a4b3489211359261747ed0cb9c8c261434bb762ad3f76df33bdbabd5cb" in lock
    assert "v1.0.52 dws-linux-arm64.tar.gz 0d357ef0535f99f2f63b5ecbfdee9c32448be2a2c24f3096c03126b3b7570bc5" in lock


def _config(tmp_path: Path) -> DailyFundsConfig:
    return DailyFundsConfig.from_env({
        "DAILY_FUNDS_STATE_DIR": str(tmp_path / "state"),
        "DAILY_FUNDS_PUBLICATION_DIR": str(tmp_path / "publication"),
        "DAILY_FUNDS_CONTROL_DIR": str(tmp_path / "control"),
        "DAILY_FUNDS_DWS_CONFIG_DIR": str(tmp_path / "dws-config"),
        "DAILY_FUNDS_DWS_KEYRING_DIR": str(tmp_path / "dws-keyring"),
    })


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _request(config: DailyFundsConfig, request_id: str, *, action: str = "START") -> None:
    now = datetime.now(UTC)
    atomic_json_write(config.control_dir / REQUEST_FILE, {
        "schema_version": REQUEST_SCHEMA,
        "request_id": request_id,
        "action": action,
        "actor": ACTOR,
        "requested_at": _timestamp(now),
        "expires_at": _timestamp(now + timedelta(minutes=10)),
    })


def _wait_for_session(config: DailyFundsConfig, state: str) -> dict:
    target = config.control_dir / SESSION_FILE
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if target.exists():
            payload = json.loads(target.read_text(encoding="utf-8"))
            if payload.get("state") == state:
                return payload
        time.sleep(0.02)
    raise AssertionError(f"did not reach auth session state {state}")


def test_device_prompt_parser_accepts_only_the_official_short_lived_fields() -> None:
    prompt = _parse_dws_device_prompt(
        "\x1b[36m链接: https://login.dingtalk.com/device\x1b[0m\n"
        "授权码: \x1b[33mABCD-EFGH\x1b[0m\n"
        "https://login.dingtalk.com/device?userCode=ABCD-EFGH\n"
    )
    assert prompt == DwsDevicePrompt(
        authorization_url="https://login.dingtalk.com/device?userCode=ABCD-EFGH",
        user_code="ABCD-EFGH",
    )
    assert _parse_dws_device_prompt("授权码: ABCD-EFGH\nhttps://example.invalid/verify") is None
    assert _parse_dws_device_prompt("https://login.dingtalk.com/device\n") is None


def test_brokered_dws_login_captures_the_device_prompt_without_a_terminal_stream(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _config(tmp_path)
    client = DwsHistoryClient(config)
    statuses = iter((
        DwsAuthStatus(authenticated=False, refresh_token_valid=False),
        DwsAuthStatus(authenticated=True, refresh_token_valid=True),
    ))
    monkeypatch.setattr(client, "_auth_status", lambda: next(statuses))

    class FakeProcess:
        def __init__(self):
            self.stdout = io.StringIO(
                "链接: https://login.dingtalk.com/device\n授权码: ABCD-EFGH\n"
                "https://login.dingtalk.com/device?userCode=ABCD-EFGH\n"
            )
            self.returncode: int | None = None

        def poll(self):
            if self.returncode is None and self.stdout.tell() == len(self.stdout.getvalue()):
                self.returncode = 0
            return self.returncode

        def communicate(self, timeout):
            self.returncode = 0
            return ("", "")

        def terminate(self):
            self.returncode = -15

        def wait(self, timeout):
            return self.returncode

        def kill(self):
            self.returncode = -9

    commands: list[list[str]] = []

    def fake_popen(command, **kwargs):
        commands.append(command)
        assert kwargs["stdin"] is ingestion_module.subprocess.DEVNULL
        assert kwargs["stdout"] is ingestion_module.subprocess.PIPE
        assert kwargs["stderr"] is ingestion_module.subprocess.STDOUT
        assert "capture_output" not in kwargs
        return FakeProcess()

    monkeypatch.setattr(ingestion_module.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(ingestion_module.select, "select", lambda readers, _write, _error, _timeout: (readers, [], []))
    prompts: list[DwsDevicePrompt] = []
    assert client.bootstrap_device_auth_with_prompt(prompts.append, cancel_requested=lambda: False) == "OK"
    assert commands == [[
        config.dws_bin, "auth", "login", "--device", "--no-browser", "--yes", "--format", "json",
    ]]
    assert prompts == [
        DwsDevicePrompt(
            authorization_url="https://login.dingtalk.com/device",
            user_code="ABCD-EFGH",
        ),
        DwsDevicePrompt(
            authorization_url="https://login.dingtalk.com/device?userCode=ABCD-EFGH",
            user_code="ABCD-EFGH",
        ),
    ]


def test_broker_writes_prompt_only_while_owner_approval_is_pending(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _config(tmp_path)
    broker = DailyFundsAuthBroker(config, poll_seconds=0.01)
    request_id = "a" * 64
    release = threading.Event()

    def fake_device_auth(self, prompt_sink, *, cancel_requested, max_wait_seconds):
        assert max_wait_seconds == 660
        prompt_sink(DwsDevicePrompt("https://login.dingtalk.com/device?userCode=ABCD-EFGH", "ABCD-EFGH"))
        while not release.is_set():
            assert not cancel_requested()
            time.sleep(0.01)
        return "OK"

    monkeypatch.setattr(DwsHistoryClient, "bootstrap_device_auth_with_prompt", fake_device_auth)
    _request(config, request_id)
    broker.run_once()
    waiting = _wait_for_session(config, "AWAITING_APPROVAL")
    assert waiting["authorization_url"].startswith("https://login.dingtalk.com/")
    assert waiting["user_code"] == "ABCD-EFGH"
    assert "device_code" not in json.dumps(waiting)

    release.set()
    completed = _wait_for_session(config, "SUCCEEDED")
    assert completed["authorization_url"] is None
    assert completed["user_code"] is None
    assert not (config.control_dir / REQUEST_FILE).exists()


def test_broker_cancellation_wipes_the_prompt_and_never_executes_input_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _config(tmp_path)
    broker = DailyFundsAuthBroker(config, poll_seconds=0.01)
    request_id = "b" * 64

    def fake_device_auth(self, prompt_sink, *, cancel_requested, max_wait_seconds):
        prompt_sink(DwsDevicePrompt("https://login.dingtalk.com/device?userCode=WXYZ-1234", "WXYZ-1234"))
        while not cancel_requested():
            time.sleep(0.01)
        raise IngestionError("DWS_AUTH_BOOTSTRAP_CANCELLED")

    monkeypatch.setattr(DwsHistoryClient, "bootstrap_device_auth_with_prompt", fake_device_auth)
    _request(config, request_id)
    broker.run_once()
    _wait_for_session(config, "AWAITING_APPROVAL")
    _request(config, request_id, action="CANCEL")
    broker.run_once()
    cancelled = _wait_for_session(config, "CANCELLED")
    assert cancelled["authorization_url"] is None
    assert cancelled["user_code"] is None

    atomic_json_write(config.control_dir / REQUEST_FILE, {"command": "never-accepted"})
    broker.run_once()
    assert not (config.control_dir / REQUEST_FILE).exists()
