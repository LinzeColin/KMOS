from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from daily_funds.log_safety import CRON_EVENT_SCHEMA, cron_event, summarize_coolify_logs


def _run_daily_funds_module():
    spec = importlib.util.spec_from_file_location(
        "daily_funds_cron_entrypoint_test",
        ROOT / "scripts" / "run_daily_funds.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_cron_entrypoint_outputs_only_a_fixed_event_for_a_sensitive_result(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _run_daily_funds_module()

    class FakeState:
        def record_run(self, *_args, **_kwargs) -> None:
            return None

    class FakeRuntime:
        def __init__(self) -> None:
            self.state = FakeState()

        def record_operation_start(self, **_kwargs) -> None:
            return None

        def record_operation_receipt(self, **_kwargs) -> None:
            return None

        def poll(self) -> dict[str, object]:
            return {
                "ok": True,
                "code": "VALID_PUBLISHED",
                "source_message": "敏感资金消息原文",
                "amount_fen": 987654321,
                "publication_id": "a" * 64,
            }

    monkeypatch.setattr(module, "DailyFundsRuntime", FakeRuntime)
    assert module.main(["poll"]) == 0
    output = capsys.readouterr().out.strip()
    assert json.loads(output) == {
        "schema_version": CRON_EVENT_SCHEMA,
        "job": "poll",
        "outcome": "SUCCEEDED",
        "machine_code": "VALID_PUBLISHED",
    }
    assert "敏感资金消息原文" not in output
    assert "987654321" not in output
    assert "a" * 64 not in output


def test_cron_entrypoint_hides_exception_text(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _run_daily_funds_module()

    def explode():
        raise RuntimeError("source-message=不应出现在日志中")

    monkeypatch.setattr(module, "DailyFundsRuntime", explode)
    assert module.main(["poll"]) == 2
    output = capsys.readouterr().out.strip()
    assert json.loads(output) == {
        "schema_version": CRON_EVENT_SCHEMA,
        "job": "poll",
        "outcome": "NEEDS_ATTENTION",
        "machine_code": "UNHANDLED",
    }
    assert "不应出现在日志中" not in output


def test_unknown_machine_code_is_not_copied_to_the_log_event() -> None:
    event = cron_event("poll", "NEEDS_ATTENTION", "PROVIDER_RETURNED_SECRET_VALUE")
    assert event["machine_code"] == "UNCLASSIFIED"


@pytest.mark.parametrize(
    "machine_code",
    (
        "DWS_ATTACHMENT_PERMISSION_DENIED",
        "ATTACHMENT_DOWNLOAD_ARGUMENT_INVALID",
        "ATTACHMENT_DOWNLOAD_TRANSPORT_FAILED",
        "ATTACHMENT_DOWNLOAD_READ_FAILED",
        "ATTACHMENT_DOWNLOAD_AMBIGUOUS",
        "ATTACHMENT_DOWNLOAD_FAILED",
        "GIT_ARCHIVE_PREPARE_FAILED",
        "GIT_ARCHIVE_STAGE_FAILED",
        "GIT_ARCHIVE_COMMIT_FAILED",
        "GIT_ARCHIVE_PUSH_FAILED",
        "GIT_ARCHIVE_REBASE_FAILED",
        "GIT_ARCHIVE_VERIFY_FAILED",
        "GIT_ARCHIVE_READBACK_FAILED",
        "RAW_PATH_HASH_COLLISION",
    ),
)
def test_daily_funds_actionable_backfill_codes_are_admitted_without_raw_detail(machine_code: str) -> None:
    event = cron_event("backfill", "NEEDS_ATTENTION", machine_code)
    assert event["machine_code"] == machine_code


def test_raw_archive_audit_uses_the_same_fixed_values_free_cron_contract() -> None:
    event = cron_event("raw-archive-audit", "SUCCEEDED", "RAW_ARCHIVE_AUDITED")
    assert event == {
        "schema_version": CRON_EVENT_SCHEMA,
        "job": "raw-archive-audit",
        "outcome": "SUCCEEDED",
        "machine_code": "RAW_ARCHIVE_AUDITED",
    }


def test_r2_guard_is_recorded_as_a_fixed_values_free_cron_event(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _run_daily_funds_module()

    class FakeState:
        def record_run(self, *_args, **_kwargs) -> None:
            return None

    class FakeRuntime:
        def __init__(self) -> None:
            self.state = FakeState()

        def record_operation_start(self, **_kwargs) -> None:
            return None

        def record_operation_receipt(self, **_kwargs) -> None:
            return None

        def r2_free_tier_guard(self) -> dict[str, object]:
            return {
                "ok": True,
                "code": "R2_ZERO_CHARGE_GUARD_OK",
                "sensitive_bucket": "must-not-escape",
            }

    monkeypatch.setattr(module, "DailyFundsRuntime", FakeRuntime)
    assert module.main(["r2-guard"]) == 0
    output = capsys.readouterr().out.strip()
    assert json.loads(output) == {
        "schema_version": CRON_EVENT_SCHEMA,
        "job": "r2-guard",
        "outcome": "SUCCEEDED",
        "machine_code": "R2_ZERO_CHARGE_GUARD_OK",
    }
    assert "must-not-escape" not in output


def test_coolify_log_summary_counts_only_exact_fixed_events(tmp_path: Path) -> None:
    secret = "敏感原文-and-a-long-private-token-like-string"
    event = json.dumps(
        {
            "schema_version": CRON_EVENT_SCHEMA,
            "job": "auth-probe",
            "outcome": "SUCCEEDED",
            "machine_code": "AUTH_OK",
        }
    )
    malformed = json.dumps(
        {
            "schema_version": CRON_EVENT_SCHEMA,
            "job": "poll",
            "outcome": "NEEDS_ATTENTION",
            "machine_code": "SOURCE_MATCH_ZERO",
            "leak": secret,
        }
    )
    response = tmp_path / "coolify.json"
    response.write_text(json.dumps({"logs": "\n".join((event, secret, malformed))}), encoding="utf-8")

    summary = summarize_coolify_logs(response, http_status="200", curl_exit=0)
    rendered = json.dumps(summary, ensure_ascii=False)
    assert summary["daily_funds_event_counts"] == {"auth-probe": {"SUCCEEDED": 1}}
    assert summary["daily_funds_machine_code_counts"] == {"AUTH_OK": 1}
    assert summary["unrecognized_line_count"] == 2
    assert secret not in rendered


def test_coolify_workflow_uses_the_values_free_summary() -> None:
    workflow = (ROOT.parents[2] / ".github" / "workflows" / "coolify-ops.yml").read_text(encoding="utf-8")
    assert "summarize_coolify_logs.py" in workflow
    assert "print(t[-6000:])" not in workflow
