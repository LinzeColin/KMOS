from __future__ import annotations

import base64
import importlib.util
import json
import subprocess
import sys
import urllib.error
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from daily_funds.config import ConfigError, DailyFundsConfig
from daily_funds.control import ControlError, ThresholdControl
from daily_funds.contracts import (
    ContractError,
    DailyBalance,
    HARD_THRESHOLD_FEN,
    HUMAN_STATUSES,
    RISK_LABELS,
    SOFT_THRESHOLD_FEN,
    complete_calendar_month_window,
    dynamic_flag,
    effective_risk,
    fen_average,
    fixed_risk,
    floating_month_lines,
    parse_amount_to_fen,
    custom_date_line,
)
from daily_funds.ingestion import (
    CHUNK_BYTES,
    DIRECT_BLOB_MAX_BYTES,
    DownloadedAttachment,
    DwsPage,
    DwsHistoryClient,
    GitCommit,
    GitSparseWriter,
    HistoryPoller,
    IngestionError,
    RawMaterializer,
    SPARSE_PATH,
)
from daily_funds.models import SourceRef
from daily_funds.parsing import ACCOUNT_FAMILY, PARSER_VERSION, ParseError, parse_attachment
from daily_funds.publication import D1Projection, OciColdBackup, OciParStore, PublicationCoordinator, PublicationError, R2Mirror, RestoreCoordinator, RestoreOracle
from daily_funds.reconcile import AccountReconciliation, ReconciliationError, ReconciliationReport, account_key_hash, reconcile
from daily_funds.runtime import DailyFundsRuntime, TimedFacts
from daily_funds.state import RuntimeState, StatusWriter

UTC = timezone.utc


def _config(tmp_path: Path) -> DailyFundsConfig:
    # Build a structurally valid *synthetic* PEM marker without placing a
    # private-key-looking literal in the public repository or secret scans.
    pem = base64.b64encode(
        b"-----BEGIN " + b"PRIVATE KEY-----\nfixture\n-----END " + b"PRIVATE KEY-----\n"
    ).decode()
    values = {
        "DAILY_FUNDS_STATE_DIR": str(tmp_path / "state"),
        "DAILY_FUNDS_PUBLICATION_DIR": str(tmp_path / "publication"),
        "DAILY_FUNDS_CONTROL_DIR": str(tmp_path / "control"),
        "DAILY_FUNDS_DWS_CONFIG_DIR": str(tmp_path / "dws-config"),
        "DAILY_FUNDS_DWS_KEYRING_DIR": str(tmp_path / "dws-keyring"),
        "DAILY_FUNDS_GROUP_ID": "group-fixture",
        "DAILY_FUNDS_SENDER_ID": "sender-fixture",
        "DAILY_FUNDS_DWS_CLIENT_ID": "client-fixture",
        "DAILY_FUNDS_DWS_AUTH_BUNDLE_B64": base64.b64encode(b"fixture-dws-auth-bundle").decode(),
        "DAILY_FUNDS_GIT_SSH_KEY_B64": pem,
        "DAILY_FUNDS_CLOUDFLARE_API_TOKEN": "cf-fixture",
        "DAILY_FUNDS_CF_ACCOUNT_ID": "account-fixture",
        "DAILY_FUNDS_D1_DATABASE_ID": "d1-fixture",
        "DAILY_FUNDS_RESTORE_DRILL_D1_DATABASE_ID": "d1-restore-fixture",
        "DAILY_FUNDS_R2_ENDPOINT_URL": "https://r2.invalid",
        "DAILY_FUNDS_R2_BUCKET": "r2-fixture",
        "DAILY_FUNDS_R2_ACCESS_KEY_ID": "r2-key",
        "DAILY_FUNDS_R2_SECRET_ACCESS_KEY": "r2-secret",
        "DAILY_FUNDS_OCI_ENDPOINT_URL": "https://oci.invalid",
        "DAILY_FUNDS_OCI_BUCKET": "oci-fixture",
        "DAILY_FUNDS_OCI_ACCESS_KEY_ID": "oci-key",
        "DAILY_FUNDS_OCI_SECRET_ACCESS_KEY": "oci-secret",
    }
    return DailyFundsConfig.from_env(values)


def _source(payload: bytes, *, message_id_hash: str = "b" * 64, index: int = 0) -> SourceRef:
    version = sha256(payload).hexdigest()
    return SourceRef(
        version,
        message_id_hash,
        f"Private-KMDatabase/KMFA/daily_funds/raw/occurrences/2026/07/30/{message_id_hash}/{index}.json",
        version,
    )


def test_integer_fen_and_frozen_fixed_boundaries() -> None:
    assert parse_amount_to_fen("599999.99") == HARD_THRESHOLD_FEN - 1
    assert parse_amount_to_fen("600000.00") == HARD_THRESHOLD_FEN
    assert parse_amount_to_fen("1200000.00") == SOFT_THRESHOLD_FEN
    assert fixed_risk(HARD_THRESHOLD_FEN - 1) == "高风险"
    assert fixed_risk(HARD_THRESHOLD_FEN) == "高风险"
    assert fixed_risk(HARD_THRESHOLD_FEN + 1) == "关注"
    assert fixed_risk(SOFT_THRESHOLD_FEN) == "关注"
    assert fixed_risk(SOFT_THRESHOLD_FEN + 1) == "正常"
    with pytest.raises(ValueError):
        parse_amount_to_fen(1.5)
    with pytest.raises(ValueError):
        parse_amount_to_fen("0.001")
    assert fen_average((1, 2)) == 2
    assert "动态明显偏低" in RISK_LABELS
    assert effective_risk(HARD_THRESHOLD_FEN - 1, (HARD_THRESHOLD_FEN + 1,)) == ("高风险", "动态明显偏低")
    with pytest.raises(ContractError, match="CURRENT_AMOUNT_NOT_INTEGER_FEN"):
        dynamic_flag(1.5, (1,))


def test_config_allows_only_the_daily_funds_private_repository(tmp_path: Path) -> None:
    config = _config(tmp_path)
    config.validate()
    with pytest.raises(ConfigError, match="PRIVATE_REPOSITORY_NOT_ALLOWED"):
        replace(config, private_repo="git@github.com:example/Private-Database.git").validate()
    with pytest.raises(ConfigError, match="PRIVATE_REPOSITORY_NOT_ALLOWED"):
        replace(config, private_repo="https://github.com/LinzeColin/Private-Database.git").validate()
    with pytest.raises(ConfigError, match="DAILY_FUNDS_RESTORE_DRILL_D1_DATABASE_ID"):
        replace(config, restore_drill_d1_database_id="").validate()
    with pytest.raises(ConfigError, match="RESTORE_DRILL_D1_MUST_DIFFER"):
        replace(config, restore_drill_d1_database_id=config.d1_database_id).validate()


def test_three_and_six_month_lines_require_contract_coverage() -> None:
    as_of = date(2026, 8, 1)
    start, end = complete_calendar_month_window(as_of, 6)
    balances = []
    day = start
    while day <= end:
        balances.append(DailyBalance(day, 100_000_000, True, False))
        day += timedelta(days=1)
    three, six = floating_month_lines(as_of, balances)
    assert three.active and three.threshold_fen == 100_000_000
    assert six.active and six.threshold_fen == 100_000_000
    missing = [row for row in balances if row.business_day <= end - timedelta(days=10)]
    _, six_missing = floating_month_lines(as_of, missing)
    assert not six_missing.active
    assert six_missing.reason == "COVERAGE_INSUFFICIENT"


def test_custom_range_does_not_invent_a_direct_observation_requirement() -> None:
    start = date(2026, 7, 1)
    balances = tuple(
        DailyBalance(start + timedelta(days=index), 100_000_000, False, False, True)
        for index in range(7)
    )
    line = custom_date_line(start, start + timedelta(days=6), balances)
    assert line.active is True
    assert line.direct_observations == 0


def test_dynamic_lines_reject_duplicate_or_unclassified_daily_balance_grain() -> None:
    start = date(2026, 7, 1)
    with pytest.raises(ContractError, match="DAILY_BALANCE_DUPLICATE"):
        custom_date_line(
            start,
            start + timedelta(days=6),
            (
                DailyBalance(start, 100, True),
                DailyBalance(start, 100, True),
            ),
        )
    with pytest.raises(ContractError, match="DAILY_BALANCE_CLASSIFICATION_INVALID"):
        custom_date_line(
            start,
            start + timedelta(days=6),
            tuple(
                DailyBalance(start + timedelta(days=index), 100, False, False, False)
                for index in range(7)
            ),
        )
    with pytest.raises(ContractError, match="DAILY_BALANCE_NOT_INTEGER_FEN"):
        custom_date_line(
            start,
            start + timedelta(days=6),
            (DailyBalance(start, True, True),),
        )


def test_dynamic_threshold_activation_respects_exact_coverage_boundaries() -> None:
    as_of = date(2026, 8, 1)
    six_start, six_end = complete_calendar_month_window(as_of, 6)
    all_days = tuple(
        DailyBalance(six_start + timedelta(days=index), 100, True)
        for index in range((six_end - six_start).days + 1)
    )
    # Feb--Jul 2026 has 181 days: 172/181 is above 95%, 171/181 is below.
    _, six_at_gate = floating_month_lines(as_of, all_days[9:])
    _, six_below_gate = floating_month_lines(as_of, all_days[10:])
    assert six_at_gate.active and six_at_gate.covered_days == 172
    assert not six_below_gate.active and six_below_gate.reason == "COVERAGE_INSUFFICIENT"

    custom_start = date(2026, 7, 1)
    six_of_seven = tuple(
        DailyBalance(custom_start + timedelta(days=index), 100, index < 6, index == 6)
        for index in range(7)
    )
    five_of_seven = tuple(
        DailyBalance(custom_start + timedelta(days=index), 100, index < 5, index >= 5)
        for index in range(7)
    )
    assert custom_date_line(custom_start, custom_start + timedelta(days=6), six_of_seven).active
    assert not custom_date_line(custom_start, custom_start + timedelta(days=6), five_of_seven).active


def test_daily_balance_calendar_carries_only_non_reporting_days_and_flags_weekday_gaps(tmp_path: Path) -> None:
    runtime = DailyFundsRuntime(_config(tmp_path))
    runtime._history_path.parent.mkdir(parents=True, exist_ok=True)
    runtime._history_path.write_text(json.dumps({
        "schema_version": "kmfa.daily_funds.history.v1",
        "days": {
            "2026-07-31": {
                "ending_available_fen": 100,
                "direct_observation": True,
                "coverage_gap": False,
                "carried_forward": False,
                "account_ending_by_hash": {},
            },
        },
    }), encoding="utf-8")
    # A newer live pointer must never leak future data into an old/backfill
    # publication's threshold window.
    (runtime.config.publication_dir / "current.json").write_text(json.dumps({
        "publication": {"status": "VALID"},
        "daily_balances": [{
            "business_date": "2026-08-07", "ending_available_fen": 999,
            "direct_observation": True, "coverage_gap": False,
        }],
    }), encoding="utf-8")
    report = SimpleNamespace(business_date=date(2026, 8, 6), total_ending_fen=120)
    rows = {row.business_day: row for row in runtime._daily_balances(report)}
    assert date(2026, 8, 7) not in rows
    assert rows[date(2026, 8, 1)].carried_forward and not rows[date(2026, 8, 1)].coverage_gap
    assert rows[date(2026, 8, 2)].carried_forward and not rows[date(2026, 8, 2)].coverage_gap
    assert rows[date(2026, 8, 3)].coverage_gap and not rows[date(2026, 8, 3)].carried_forward
    assert rows[date(2026, 8, 4)].coverage_gap and not rows[date(2026, 8, 4)].carried_forward
    assert rows[date(2026, 8, 6)].direct_observation and rows[date(2026, 8, 6)].ending_available_fen == 120
    assert not custom_date_line(date(2026, 7, 31), date(2026, 8, 6), rows.values()).active


def test_threshold_control_keeps_a_versioned_owner_audit(tmp_path: Path) -> None:
    control = ThresholdControl(tmp_path / "control")
    control.root.mkdir(parents=True)
    control.request_path.write_text(json.dumps({
        "mode": "numeric",
        "amount_fen": 90_000_000,
        "revision": "a" * 64,
        "actor": "kmfa_private_owner_ui",
        "reason": "fixture evidence",
    }), encoding="utf-8")
    active = control.apply_pending()
    assert active and active["amount_fen"] == 90_000_000
    audit = json.loads(control.audit_path.read_text(encoding="utf-8").strip())
    assert audit["actor"] == "kmfa_private_owner_ui"
    assert audit["reason"] == "fixture evidence"
    assert set(("old_value", "new_value", "changed_at", "rollback_version")) <= set(audit)


def test_threshold_control_rejects_invalid_active_revision_and_revision_collision(tmp_path: Path) -> None:
    control = ThresholdControl(tmp_path / "control")
    control.root.mkdir(parents=True)
    control.active_path.write_text(json.dumps({
        "mode": "numeric",
        "amount_fen": 90_000_000,
        "revision": "r" * 64,
    }), encoding="utf-8")
    with pytest.raises(ControlError, match="THRESHOLD_ACTIVE_INVALID"):
        control.line((), date(2026, 8, 1))

    control.active_path.unlink()
    control.request_path.write_text(json.dumps({
        "mode": "numeric",
        "amount_fen": 90_000_000,
        "revision": "b" * 64,
    }), encoding="utf-8")
    assert control.apply_pending()["amount_fen"] == 90_000_000
    control.request_path.write_text(json.dumps({
        "mode": "numeric",
        "amount_fen": 90_000_001,
        "revision": "b" * 64,
    }), encoding="utf-8")
    with pytest.raises(ControlError, match="THRESHOLD_REVISION_COLLISION"):
        control.apply_pending()


def test_threshold_control_surfaces_balance_quality_errors_instead_of_coverage(tmp_path: Path) -> None:
    control = ThresholdControl(tmp_path / "control")
    control.root.mkdir(parents=True)
    control.request_path.write_text(json.dumps({
        "mode": "date_range",
        "from": "2026-07-01",
        "to": "2026-07-07",
        "revision": "c" * 64,
    }), encoding="utf-8")
    with pytest.raises(ControlError, match="THRESHOLD_BALANCE_QUALITY_INVALID"):
        control.line(
            (DailyBalance(date(2026, 7, 1), 100, False, False, False),),
            date(2026, 8, 1),
        )


def test_monthly_restore_drill_rejects_missing_or_live_d1_target(tmp_path: Path) -> None:
    config = _config(tmp_path)
    runtime = DailyFundsRuntime(replace(config, restore_drill_d1_database_id=""))
    assert runtime.restore_drill()["machine_code"] == "RESTORE_DRILL_CONFIG_INVALID"
    receipt = json.loads((config.publication_dir / "restore_drill.json").read_text(encoding="utf-8"))
    assert receipt["result"] == "NEEDS_ATTENTION"
    flow = json.loads((config.publication_dir / "flow_state.json").read_text(encoding="utf-8"))
    assert flow["self_healing"]["restore_drill"] == "NEEDS_ATTENTION"
    invalid_live = DailyFundsRuntime(replace(config, restore_drill_d1_database_id=config.d1_database_id))
    assert invalid_live.restore_drill()["machine_code"] == "RESTORE_DRILL_CONFIG_INVALID"


def test_two_fact_families_never_merge_and_reconcile_to_zero() -> None:
    account_payload = (
        "业务日期,公司,开户行,账号,期初余额,期末余额,币种\n"
        "2026-07-30,甲公司,甲银行,001,1500000.00,1570000.00,CNY\n"
    ).encode()
    accounts = parse_attachment(
        family=ACCOUNT_FAMILY,
        filename="资金账户明细表_20260730.csv",
        payload=account_payload,
        source=_source(account_payload, message_id_hash="a" * 64),
    )
    transaction_payload = (
        "业务日期,公司,开户行,账号,流水号,流入,流出\n"
        "2026-07-30,甲公司,甲银行,001,in,250000.00,\n"
        "2026-07-30,甲公司,甲银行,001,out,,180000.00\n"
    ).encode()
    transactions = parse_attachment(
        family="资金流水明细",
        filename="资金流水明细_20260730.csv",
        payload=transaction_payload,
        source=_source(transaction_payload, message_id_hash="b" * 64),
    )
    assert accounts.accounts and not accounts.transactions
    assert transactions.transactions and not transactions.accounts
    report = reconcile((accounts, transactions))
    assert report.valid
    assert report.difference_fen == 0


def test_reconciliation_rejects_cross_source_duplicate_transactions() -> None:
    account_payload = (
        "业务日期,公司,开户行,账号,期初余额,期末余额\n"
        "2026-07-30,甲,乙,001,100.00,110.00\n"
    ).encode()
    accounts = parse_attachment(
        family=ACCOUNT_FAMILY,
        filename="资金账户明细表_20260730.csv",
        payload=account_payload,
        source=_source(account_payload, message_id_hash="a" * 64),
    )
    transaction_payload = (
        "业务日期,公司,开户行,账号,流水号,流入,流出\n"
        "2026-07-30,甲,乙,001,t-1,10.00,\n"
    ).encode()
    first = parse_attachment(
        family="资金流水明细",
        filename="资金流水明细_20260730.csv",
        payload=transaction_payload,
        source=_source(transaction_payload, message_id_hash="b" * 64),
    )
    repeated = parse_attachment(
        family="资金流水明细",
        filename="资金流水明细_20260730_v2.csv",
        payload=transaction_payload,
        source=_source(transaction_payload, message_id_hash="c" * 64),
    )
    with pytest.raises(ReconciliationError, match="DUPLICATE_TRANSACTION"):
        reconcile((accounts, first, repeated))


def test_reconciliation_rejects_distinct_extra_fact_source_before_blending() -> None:
    account_payload = (
        "业务日期,公司,开户行,账号,期初余额,期末余额\n"
        "2026-07-30,甲,乙,001,100.00,110.00\n"
    ).encode()
    accounts = parse_attachment(
        family=ACCOUNT_FAMILY,
        filename="资金账户明细表_20260730.csv",
        payload=account_payload,
        source=_source(account_payload, message_id_hash="a" * 64),
    )
    first_payload = (
        "业务日期,公司,开户行,账号,流水号,流入,流出\n"
        "2026-07-30,甲,乙,001,t-1,10.00,\n"
    ).encode()
    second_payload = (
        "业务日期,公司,开户行,账号,流水号,流入,流出\n"
        "2026-07-30,甲,乙,001,t-2,,\n"
    ).encode()
    first = parse_attachment(
        family="资金流水明细",
        filename="资金流水明细_20260730.csv",
        payload=first_payload,
        source=_source(first_payload, message_id_hash="b" * 64),
    )
    second = parse_attachment(
        family="资金流水明细",
        filename="资金流水明细_20260730_v2.csv",
        payload=second_payload,
        source=_source(second_payload, message_id_hash="c" * 64),
    )
    with pytest.raises(ReconciliationError, match="SOURCE_FACT_PAIR_AMBIGUOUS"):
        reconcile((accounts, first, second))


def test_reconciliation_counts_internal_transfer_adjustments_in_integer_fen() -> None:
    account_payload = (
        "业务日期,公司,开户行,账号,期初余额,期末余额\n"
        "2026-07-30,甲,乙,001,100.00,195.00\n"
        "2026-07-30,甲,乙,002,200.00,100.00\n"
    ).encode()
    accounts = parse_attachment(
        family=ACCOUNT_FAMILY,
        filename="资金账户明细表_20260730.csv",
        payload=account_payload,
        source=_source(account_payload, message_id_hash="a" * 64),
    )
    transaction_payload = (
        "业务日期,公司,开户行,账号,流水号,流入,流出,调整金额,是否内部调拨,调拨编号\n"
        "2026-07-30,甲,乙,001,t-in,100.00,,-5.00,是,move-1\n"
        "2026-07-30,甲,乙,002,t-out,,100.00,,是,move-1\n"
    ).encode()
    transactions = parse_attachment(
        family="资金流水明细",
        filename="资金流水明细_20260730.csv",
        payload=transaction_payload,
        source=_source(transaction_payload, message_id_hash="b" * 64),
    )
    report = reconcile((accounts, transactions))
    assert report.valid
    assert report.total_adjustment_fen == -500
    assert report.total_ending_fen == 29_500


def test_reconciliation_requires_each_account_even_when_global_difference_cancels() -> None:
    account_payload = (
        "业务日期,公司,开户行,账号,期初余额,期末余额\n"
        "2026-07-30,甲,乙,001,100.00,110.00\n"
        "2026-07-30,甲,乙,002,100.00,90.00\n"
    ).encode()
    accounts = parse_attachment(
        family=ACCOUNT_FAMILY,
        filename="资金账户明细表_20260730.csv",
        payload=account_payload,
        source=_source(account_payload, message_id_hash="a" * 64),
    )
    transaction_payload = (
        "业务日期,公司,开户行,账号,流水号,流入,流出\n"
        "2026-07-30,甲,乙,001,t-in,11.00,\n"
        "2026-07-30,甲,乙,002,t-out,,11.00\n"
    ).encode()
    transactions = parse_attachment(
        family="资金流水明细",
        filename="资金流水明细_20260730.csv",
        payload=transaction_payload,
        source=_source(transaction_payload, message_id_hash="b" * 64),
    )
    report = reconcile((accounts, transactions))
    assert report.difference_fen == 0
    assert sorted(row.difference_fen for row in report.account_reports) == [-100, 100]
    assert report.by_company_difference_fen == {"甲": 0}
    assert report.by_bank_difference_fen == {"乙": 0}
    assert not report.valid


def test_prior_balance_never_time_travels_from_a_newer_current_pointer(tmp_path: Path) -> None:
    runtime = DailyFundsRuntime(_config(tmp_path))
    key = "a" * 64
    current = {
        "publication": {
            "status": "VALID",
            "publication_id": "b" * 64,
            "business_date": "2026-08-10",
            "reconciliation_difference_fen": 0,
        },
        "summary": {"account_ending_by_hash": {key: 100}},
    }
    (runtime.config.publication_dir / "current.json").write_text(json.dumps(current), encoding="utf-8")
    assert runtime._prior_account_balances(date(2026, 8, 6)) == {}

    current["publication"]["business_date"] = "2026-08-05"
    (runtime.config.publication_dir / "current.json").write_text(json.dumps(current), encoding="utf-8")
    assert runtime._prior_account_balances(date(2026, 8, 6)) == {key: 100}

    current["summary"]["account_ending_by_hash"][key] = True
    (runtime.config.publication_dir / "current.json").write_text(json.dumps(current), encoding="utf-8")
    with pytest.raises(ReconciliationError, match="PRIOR_BALANCE_NOT_INTEGER_FEN"):
        runtime._prior_account_balances(date(2026, 8, 6))


def test_prior_balance_rejects_unverified_history_and_nonzero_current_pointer(tmp_path: Path) -> None:
    runtime = DailyFundsRuntime(_config(tmp_path))
    key = "a" * 64
    runtime._history_path.parent.mkdir(parents=True, exist_ok=True)
    runtime._history_path.write_text(json.dumps({
        "schema_version": "kmfa.daily_funds.history.v1",
        "days": {
            "2026-08-05": {
                "status": "VALID",
                "publication_id": "b" * 64,
                "direct_observation": True,
                "coverage_gap": False,
                "carried_forward": True,
                "account_ending_by_hash": {key: 100},
            },
        },
    }), encoding="utf-8")
    with pytest.raises(ReconciliationError, match="PRIOR_HISTORY_NOT_VALID"):
        runtime._prior_account_balances(date(2026, 8, 6))

    runtime._history_path.write_text(json.dumps({
        "schema_version": "kmfa.daily_funds.history.v1", "days": {},
    }), encoding="utf-8")
    current = {
        "publication": {
            "status": "VALID",
            "publication_id": "b" * 64,
            "business_date": "2026-08-05",
            "reconciliation_difference_fen": 1,
        },
        "summary": {"account_ending_by_hash": {key: 100}},
    }
    (runtime.config.publication_dir / "current.json").write_text(json.dumps(current), encoding="utf-8")
    with pytest.raises(ReconciliationError, match="PRIOR_PUBLICATION_INVALID"):
        runtime._prior_account_balances(date(2026, 8, 6))


def test_reconciliation_rejects_non_integer_prior_balance_before_zero_difference() -> None:
    account_payload = (
        "业务日期,公司,开户行,账号,期末余额\n"
        "2026-07-30,甲,乙,001,100.00\n"
    ).encode()
    accounts = parse_attachment(
        family=ACCOUNT_FAMILY,
        filename="资金账户明细表_20260730.csv",
        payload=account_payload,
        source=_source(account_payload, message_id_hash="a" * 64),
    )
    transaction_payload = (
        "业务日期,公司,开户行,账号,流水号,流入,流出\n"
        "2026-07-30,甲,乙,001,t-1,,\n"
    ).encode()
    transactions = parse_attachment(
        family="资金流水明细",
        filename="资金流水明细_20260730.csv",
        payload=transaction_payload,
        source=_source(transaction_payload, message_id_hash="b" * 64),
    )
    with pytest.raises(ReconciliationError, match="PRIOR_BALANCE_NOT_INTEGER_FEN"):
        reconcile(
            (accounts, transactions),
            previous_ending_by_account={("甲", "乙", "001"): 10_000.0},
        )


def test_reconciliation_rejects_conflicting_hashed_and_clear_prior_balances() -> None:
    account_payload = (
        "业务日期,公司,开户行,账号,期末余额\n"
        "2026-07-30,甲,乙,001,100.00\n"
    ).encode()
    accounts = parse_attachment(
        family=ACCOUNT_FAMILY,
        filename="资金账户明细表_20260730.csv",
        payload=account_payload,
        source=_source(account_payload, message_id_hash="a" * 64),
    )
    transaction_payload = (
        "业务日期,公司,开户行,账号,流水号,流入,流出\n"
        "2026-07-30,甲,乙,001,t-1,,\n"
    ).encode()
    transactions = parse_attachment(
        family="资金流水明细",
        filename="资金流水明细_20260730.csv",
        payload=transaction_payload,
        source=_source(transaction_payload, message_id_hash="b" * 64),
    )
    clear_key = ("甲", "乙", "001")
    with pytest.raises(ReconciliationError, match="PRIOR_BALANCE_CONFLICT"):
        reconcile(
            (accounts, transactions),
            previous_ending_by_account={clear_key: 10_000, account_key_hash(clear_key): 9_999},
        )


def test_parser_rejects_ambiguous_headers_filename_date_conflict_and_forged_lineage() -> None:
    duplicate_headers = (
        "业务日期,公司,开户行,账号,账号,期末余额\n"
        "2026-07-30,甲,乙,001,001,1.00\n"
    ).encode()
    with pytest.raises(ParseError, match="COLUMN_HEADER_DUPLICATE"):
        parse_attachment(
            family=ACCOUNT_FAMILY,
            filename="资金账户明细表_20260730.csv",
            payload=duplicate_headers,
            source=_source(duplicate_headers),
        )

    ambiguous_ending = (
        "业务日期,公司,开户行,账号,期末余额,余额\n"
        "2026-07-30,甲,乙,001,1.00,1.00\n"
    ).encode()
    with pytest.raises(ParseError, match="COLUMN_MAPPING_AMBIGUOUS_ENDING"):
        parse_attachment(
            family=ACCOUNT_FAMILY,
            filename="资金账户明细表_20260730.csv",
            payload=ambiguous_ending,
            source=_source(ambiguous_ending),
        )

    date_conflict = (
        "业务日期,公司,开户行,账号,期末余额\n"
        "2026-07-30,甲,乙,001,1.00\n"
    ).encode()
    with pytest.raises(ParseError, match="BUSINESS_DATE_FILENAME_MISMATCH"):
        parse_attachment(
            family=ACCOUNT_FAMILY,
            filename="资金账户明细表_20260731.csv",
            payload=date_conflict,
            source=_source(date_conflict),
        )

    valid = _source(date_conflict)
    with pytest.raises(ParseError, match="SOURCE_VERSION_MISMATCH"):
        parse_attachment(
            family=ACCOUNT_FAMILY,
            filename="资金账户明细表_20260730.csv",
            payload=date_conflict,
            source=replace(valid, source_version="a" * 64),
        )
    with pytest.raises(ParseError, match="SOURCE_LINEAGE_INVALID"):
        parse_attachment(
            family=ACCOUNT_FAMILY,
            filename="资金账户明细表_20260730.csv",
            payload=date_conflict,
            source=replace(valid, occurrence_path="Private-KMDatabase/KMFA/daily_funds/raw/occurrences/2026/07/30/a.json"),
        )
    with pytest.raises(ParseError, match="SOURCE_PAYLOAD_HASH_MISMATCH"):
        parse_attachment(
            family=ACCOUNT_FAMILY,
            filename="资金账户明细表_20260730.csv",
            payload=date_conflict,
            source=replace(valid, attachment_sha256="a" * 64, source_version="a" * 64),
        )


def test_parser_rejects_bad_magic_mime_and_duplicate_facts() -> None:
    account_payload = (
        "业务日期,公司,开户行,账号,期末余额\n"
        "2026-07-30,甲,乙,001,1.00\n"
    ).encode()
    with pytest.raises(ParseError, match="MIME_SUFFIX_MISMATCH"):
        parse_attachment(
            family=ACCOUNT_FAMILY,
            filename="资金账户明细表_20260730.csv",
            payload=account_payload,
            source=_source(account_payload),
            mime="application/pdf",
        )
    with pytest.raises(ParseError, match="FORMAT_MAGIC_MISMATCH"):
        parse_attachment(
            family=ACCOUNT_FAMILY,
            filename="资金账户明细表_20260730.xlsx",
            payload=account_payload,
            source=_source(account_payload),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    duplicate_accounts = (
        "业务日期,公司,开户行,账号,期末余额\n"
        "2026-07-30,甲,乙,001,1.00\n"
        "2026-07-30,甲,乙,001,1.00\n"
    ).encode()
    with pytest.raises(ParseError, match="ACCOUNT_SNAPSHOT_DUPLICATE"):
        parse_attachment(
            family=ACCOUNT_FAMILY,
            filename="资金账户明细表_20260730.csv",
            payload=duplicate_accounts,
            source=_source(duplicate_accounts),
        )

    duplicate_transactions = (
        "业务日期,公司,开户行,账号,流水号,流入,流出\n"
        "2026-07-30,甲,乙,001,t-1,1.00,\n"
        "2026-07-30,甲,乙,001,t-1,1.00,\n"
    ).encode()
    with pytest.raises(ParseError, match="TRANSACTION_DUPLICATE"):
        parse_attachment(
            family="资金流水明细",
            filename="资金流水明细_20260730.csv",
            payload=duplicate_transactions,
            source=_source(duplicate_transactions),
        )


def test_parser_rejects_competing_transaction_amount_encodings() -> None:
    payload = (
        "业务日期,公司,开户行,账号,流水号,流入,流出,金额,收支方向\n"
        "2026-07-30,甲,乙,001,t-1,1.00,,2.00,流入\n"
    ).encode()
    with pytest.raises(ParseError, match="TRANSACTION_AMOUNT_MAPPING_AMBIGUOUS"):
        parse_attachment(
            family="资金流水明细",
            filename="资金流水明细_20260730.csv",
            payload=payload,
            source=_source(payload),
        )


def test_parser_accepts_gb18030_tab_delimited_text_with_exact_fen() -> None:
    payload = (
        "业务日期\t公司\t开户行\t账号\t期末余额\n"
        "2026-07-30\t甲\t乙\t001\t1.23\n"
    ).encode("gb18030")
    facts = parse_attachment(
        family=ACCOUNT_FAMILY,
        filename="资金账户明细表_20260730.txt",
        payload=payload,
        source=_source(payload),
        mime="text/plain; charset=gb18030",
    )
    assert facts.accounts[0].ending_available_fen == 123
    assert facts.parser_evidence.format == "CSV"
    assert facts.parser_evidence.suffix == ".txt"


def test_xlsx_parser_uses_integer_fen_and_rejects_formulas_or_numeric_identifiers() -> None:
    openpyxl = pytest.importorskip("openpyxl")

    def workbook_payload(account: object, ending: object, *, extra_sheet: bool = False) -> bytes:
        book = openpyxl.Workbook()
        sheet = book.active
        sheet.append(["业务日期", "公司", "开户行", "账号", "期初余额", "期末余额", "币种"])
        sheet.append([date(2026, 7, 30), "甲", "乙", account, 1000.01, ending, "CNY"])
        if extra_sheet:
            # A future real-sample template may name and validate multiple
            # sheets explicitly.  Until then, parsing only the active sheet
            # would silently omit this content and must fail closed.
            review = book.create_sheet("待确认")
            review.append(["业务日期", "公司", "开户行", "账号", "期末余额"])
            review.append([date(2026, 7, 30), "甲", "乙", "00999", 1.00])
        output = BytesIO()
        book.save(output)
        return output.getvalue()

    valid_payload = workbook_payload("00123", 1000.11)
    facts = parse_attachment(
        family=ACCOUNT_FAMILY,
        filename="资金账户明细表_20260730.xlsx",
        payload=valid_payload,
        source=_source(valid_payload),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert facts.accounts[0].account == "00123"
    assert facts.accounts[0].ending_available_fen == 100011
    assert facts.parser_evidence.format == "XLSX"
    assert facts.parser_evidence.magic == "ZIP"

    numeric_identifier_payload = workbook_payload(123, 1000.11)
    with pytest.raises(ParseError, match="ACCOUNT_NUMBER_NON_TEXT"):
        parse_attachment(
            family=ACCOUNT_FAMILY,
            filename="资金账户明细表_20260730.xlsx",
            payload=numeric_identifier_payload,
            source=_source(numeric_identifier_payload),
        )

    formula_payload = workbook_payload("00123", "=1000+0.11")
    with pytest.raises(ParseError, match="XLSX_FORMULA_UNSUPPORTED"):
        parse_attachment(
            family=ACCOUNT_FAMILY,
            filename="资金账户明细表_20260730.xlsx",
            payload=formula_payload,
            source=_source(formula_payload),
        )

    multi_sheet_payload = workbook_payload("00123", 1000.11, extra_sheet=True)
    with pytest.raises(ParseError, match="XLSX_WORKSHEET_AMBIGUOUS"):
        parse_attachment(
            family=ACCOUNT_FAMILY,
            filename="资金账户明细表_20260730.xlsx",
            payload=multi_sheet_payload,
            source=_source(multi_sheet_payload),
        )


def test_runtime_records_parser_evidence_only_after_successful_parse(tmp_path: Path) -> None:
    payload = (
        "业务日期,公司,开户行,账号,期末余额\n"
        "2026-07-30,甲,乙,001,1.00\n"
    ).encode()
    attachment = DownloadedAttachment(
        message={},
        message_id="fixture-message",
        message_id_hash="d" * 64,
        message_at=datetime(2026, 7, 30, tzinfo=UTC),
        index=0,
        filename="资金账户明细表_20260730.csv",
        family=ACCOUNT_FAMILY,
        payload=payload,
        sha256=sha256(payload).hexdigest(),
        mime="text/csv",
    )
    runtime = DailyFundsRuntime(_config(tmp_path))
    with pytest.raises(ParseError, match="MIME_SUFFIX_MISMATCH"):
        runtime._parse((replace(attachment, mime="application/pdf"),))
    with runtime.state.connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM parser_evidence").fetchone()[0] == 0

    parsed = runtime._parse((attachment,))
    assert len(parsed) == 1
    with runtime.state.connection() as connection:
        row = connection.execute(
            "SELECT attachment_sha256,family,suffix,declared_mime,magic,parser_version FROM parser_evidence"
        ).fetchone()
    assert tuple(row) == (
        attachment.sha256,
        ACCOUNT_FAMILY,
        ".csv",
        "text/csv",
        "TEXT",
        PARSER_VERSION,
    )


def test_runtime_capability_matrix_records_supported_and_needs_review_types(tmp_path: Path) -> None:
    supported_payload = (
        "业务日期,公司,开户行,账号,期末余额\n"
        "2026-07-30,甲,乙,001,1.00\n"
    ).encode()
    unsupported_payload = b"\x89PNG\r\n\x1a\nfixture-image-bytes"
    moment = datetime(2026, 7, 30, tzinfo=UTC)
    supported = DownloadedAttachment(
        message={},
        message_id="supported-message",
        message_id_hash="e" * 64,
        message_at=moment,
        index=0,
        filename="资金账户明细表_20260730.csv",
        family=ACCOUNT_FAMILY,
        payload=supported_payload,
        sha256=sha256(supported_payload).hexdigest(),
        mime="text/csv",
    )
    unsupported = DownloadedAttachment(
        message={},
        message_id="unsupported-message",
        message_id_hash="f" * 64,
        message_at=moment,
        index=0,
        filename="资金账户明细表_20260730.png",
        family=ACCOUNT_FAMILY,
        payload=unsupported_payload,
        sha256=sha256(unsupported_payload).hexdigest(),
        mime="image/png",
    )
    runtime = DailyFundsRuntime(_config(tmp_path))
    with pytest.raises(ParseError, match="UNSUPPORTED_ATTACHMENT"):
        runtime._parse((supported, unsupported))

    with runtime.state.connection() as connection:
        parser_count = connection.execute("SELECT COUNT(*) FROM parser_evidence").fetchone()[0]
        capability_rows = connection.execute(
            """SELECT family,suffix,declared_mime,magic,outcome,code
               FROM capability_evidence ORDER BY suffix"""
        ).fetchall()
    assert parser_count == 1
    assert [tuple(row) for row in capability_rows] == [
        (ACCOUNT_FAMILY, ".csv", "text/csv", "TEXT", "SUPPORTED", "PARSER_OPEN_OK"),
        (ACCOUNT_FAMILY, ".png", "image/png", "PNG", "NEEDS_REVIEW", "UNSUPPORTED_ATTACHMENT"),
    ]

    status = runtime.status.write("需处理", "UNSUPPORTED_ATTACHMENT")
    flow = runtime._write_flow_state(stage="PARSER_NEEDS_REVIEW", status=status)
    assert flow["business_flow"]["machine_code"] == "UNSUPPORTED_ATTACHMENT"
    assert flow["attachment_capabilities"] == [
        {
            "family": ACCOUNT_FAMILY,
            "suffix": ".csv",
            "declared_mime": "text/csv",
            "magic": "TEXT",
            "parser_version": PARSER_VERSION,
            "outcome": "SUPPORTED",
            "code": "PARSER_OPEN_OK",
            "count": 1,
            "last_observed_at": flow["attachment_capabilities"][0]["last_observed_at"],
        },
        {
            "family": ACCOUNT_FAMILY,
            "suffix": ".png",
            "declared_mime": "image/png",
            "magic": "PNG",
            "parser_version": PARSER_VERSION,
            "outcome": "NEEDS_REVIEW",
            "code": "UNSUPPORTED_ATTACHMENT",
            "count": 1,
            "last_observed_at": flow["attachment_capabilities"][1]["last_observed_at"],
        },
    ]
    flow_text = (runtime.config.publication_dir / "flow_state.json").read_text(encoding="utf-8")
    assert supported.sha256 not in flow_text
    assert unsupported.sha256 not in flow_text


def test_capability_projection_excludes_stale_parser_rules(tmp_path: Path) -> None:
    runtime = DailyFundsRuntime(_config(tmp_path))
    state = runtime.state
    digest = "a" * 64
    state.record_capability_evidence(
        attachment_sha256=digest,
        family=ACCOUNT_FAMILY,
        suffix=".xlsx",
        declared_mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        magic="ZIP",
        parser_version="kmfa.daily_funds.parser.v2",
        outcome="SUPPORTED",
        code="PARSER_OPEN_OK",
    )
    state.record_capability_evidence(
        attachment_sha256=digest,
        family=ACCOUNT_FAMILY,
        suffix=".xlsx",
        declared_mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        magic="ZIP",
        parser_version=PARSER_VERSION,
        outcome="NEEDS_REVIEW",
        code="XLSX_WORKSHEET_AMBIGUOUS",
    )
    current = state.capability_matrix(parser_version=PARSER_VERSION)
    assert len(current) == 1
    assert current[0]["parser_version"] == PARSER_VERSION
    assert current[0]["outcome"] == "NEEDS_REVIEW"
    # The old receipt remains auditable, but no current status projection may
    # interpret it as support under changed parser rules.
    assert len(state.capability_matrix()) == 2
    flow = runtime._write_flow_state(stage="PARSER_NEEDS_REVIEW")
    assert len(flow["attachment_capabilities"]) == 1
    assert flow["attachment_capabilities"][0]["parser_version"] == PARSER_VERSION


def test_page_two_failure_never_advances_cursor(tmp_path: Path) -> None:
    config = _config(tmp_path)
    state = RuntimeState(config.state_dir)
    state.commit_cursor("2026-08-01 20:00:00")
    responses = [
        {
            "success": True,
            "result": {
                "hasMore": True,
                "messages": [{
                    "openMessageId": "page-1",
                    "openConversationId": config.group_id,
                    "senderOpenDingTalkId": config.sender_id,
                    "createTime": "2026-08-01 19:59:00",
                }],
            },
        },
        {"success": True, "result": {"hasMore": False, "messages": []}},
    ]

    auth_calls = 0

    def runner(command, **kwargs):
        nonlocal auth_calls
        if command[1:3] == ["auth", "status"]:
            auth_calls += 1
            return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": True, "refresh_token_valid": True}), "")
        if command[1:4] == ["chat", "message", "list"]:
            assert command[command.index("--group") + 1] == config.group_id
            assert command[command.index("--direction") + 1] == "older"
            return subprocess.CompletedProcess(command, 0, json.dumps(responses.pop(0)), "")
        raise AssertionError(f"unexpected DWS command: {command}")

    client = DwsHistoryClient(config, runner=runner)
    poller = HistoryPoller(state, client)
    calls = 0

    def persist(_page):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise IngestionError("PAGE_TWO_INJECTED_FAILURE")

    with pytest.raises(IngestionError):
        poller.poll(now=datetime(2026, 8, 1, 12, tzinfo=UTC), persist_page=persist, holder="fixture")
    assert auth_calls == 1
    assert state.get_cursor() == "2026-08-01 20:00:00"
    assert state.get("history_high_water_at") is None


def test_terminal_cursor_is_not_reused_for_the_next_overlap_window(tmp_path: Path) -> None:
    config = _config(tmp_path)
    state = RuntimeState(config.state_dir)
    state.commit_cursor("2026-08-01 08:00:00")
    times: list[str] = []
    responses = [
        {"success": True, "result": {"hasMore": False, "messages": []}},
        {"success": True, "result": {"hasMore": False, "messages": []}},
    ]

    def runner(command, **kwargs):
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": True, "refresh_token_valid": True}), "")
        if command[1:4] == ["chat", "message", "list"]:
            times.append(command[command.index("--time") + 1])
            return subprocess.CompletedProcess(command, 0, json.dumps(responses.pop(0)), "")
        raise AssertionError(f"unexpected DWS command: {command}")

    poller = HistoryPoller(state, DwsHistoryClient(config, runner=runner))
    first_now = datetime(2026, 8, 1, 0, 0, tzinfo=UTC)
    poller.poll(now=first_now, persist_page=lambda _page: None, holder="fixture-1")
    poller.poll(now=datetime(2026, 8, 1, 1, 0, tzinfo=UTC), persist_page=lambda _page: None, holder="fixture-2")

    assert times == ["2026-08-01 08:00:00", "2026-08-01 09:00:00"]
    assert state.get_cursor() is None


def test_backfill_empty_window_advances_only_the_historical_planner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = DailyFundsRuntime(_config(tmp_path))
    observed: list[dict[str, object]] = []

    def empty_poll(**kwargs):
        observed.append(kwargs)
        return {"ok": True, "pages": 1, "attachments": 0, "empty_window": True}

    monkeypatch.setattr(runtime, "poll", empty_poll)
    result = runtime.backfill(now=datetime(2026, 8, 1, 4, tzinfo=UTC), max_days=2)

    assert result["ok"] is True
    assert result["completed_days"] == ["2025-08-06", "2025-08-07"]
    assert result["empty_days"] == result["completed_days"]
    assert result["code"] == "BACKFILLING"
    assert runtime.state.get("backfill_next_business_date") == "2025-08-08"
    assert all(
        row["advance_pointer"] is False
        and row["allow_empty_window"] is True
        and row["archive_only"] is True
        for row in observed
    )


def test_backfill_advances_after_a_verified_needs_review_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = DailyFundsRuntime(_config(tmp_path))
    observed: list[dict[str, object]] = []

    def archived_poll(**kwargs):
        observed.append(kwargs)
        return {
            "ok": True,
            "pages": 1,
            "attachments": 1,
            "archive_only": True,
            "capability_supported": 0,
            "capability_needs_review": 1,
        }

    monkeypatch.setattr(runtime, "poll", archived_poll)
    result = runtime.backfill(now=datetime(2026, 8, 1, 4, tzinfo=UTC), max_days=1)

    assert result["ok"] is True
    assert result["completed_days"] == ["2025-08-06"]
    assert result["needs_review_days"] == result["completed_days"]
    assert result["needs_review_attachments"] == 1
    assert result["code"] == "BACKFILLING_NEEDS_REVIEW"
    assert observed[0]["archive_only"] is True


def test_archive_only_backfill_persists_readback_and_records_unsupported_format_without_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A historical image is evidence, not a false publication or a dead end."""

    import daily_funds.runtime as runtime_module

    config = replace(
        _config(tmp_path),
        cf_api_token="",
        cf_account_id="",
        d1_database_id="",
        restore_drill_d1_database_id="",
        r2_endpoint_url="",
        r2_bucket="",
        r2_access_key_id="",
        r2_secret_access_key="",
        oci_endpoint_url="",
        oci_bucket="",
        oci_access_key_id="",
        oci_secret_access_key="",
    )
    payload = b"\x89PNG\r\n\x1a\nsynthetic-historical-image"
    moment = datetime(2026, 7, 30, 8, tzinfo=UTC)
    attachment = DownloadedAttachment(
        message={},
        message_id="synthetic-unsupported-message",
        message_id_hash="1" * 64,
        message_at=moment,
        index=0,
        filename="资金明细_20260730.png",
        family="资金明细",
        payload=payload,
        sha256=sha256(payload).hexdigest(),
        mime="image/png",
    )
    message = {"fixture": "historical"}

    class ArchiveClient:
        @staticmethod
        def search(_start, _end, _cursor):
            return DwsPage(messages=(message,), next_cursor=None, has_more=False)

        @staticmethod
        def selected_messages(_page):
            return (message,)

        @staticmethod
        def attachment_count(_message):
            return 1

        @staticmethod
        def download(_message, _index):
            return attachment

    persisted: list[tuple[DownloadedAttachment, ...]] = []

    class ReadbackWriter:
        def __init__(self, _config):
            pass

        def persist(self, attachments):
            reopened = tuple(attachments)
            persisted.append(reopened)
            return GitCommit("a" * 40, SimpleNamespace(), reopened)

    runtime = DailyFundsRuntime(config)
    monkeypatch.setattr(runtime, "_dws_client", lambda: ArchiveClient())
    monkeypatch.setattr(runtime_module, "GitSparseWriter", ReadbackWriter)
    monkeypatch.setattr(runtime, "_coordinator", lambda: pytest.fail("archive-only must not construct a publication coordinator"))

    result = runtime.poll(
        now=datetime(2026, 8, 1, tzinfo=UTC),
        start_override=datetime(2026, 7, 30, tzinfo=UTC),
        advance_pointer=False,
        allow_empty_window=True,
        archive_only=True,
    )

    assert result == {
        "ok": True,
        "pages": 1,
        "attachments": 1,
        "archive_only": True,
        "capability_supported": 0,
        "capability_needs_review": 1,
    }
    assert persisted == [(attachment,)]
    assert not (config.publication_dir / "current.json").exists()
    with runtime.state.connection() as connection:
        inbox = connection.execute("SELECT state FROM inbox").fetchone()
        capability = connection.execute("SELECT outcome,code FROM capability_evidence").fetchone()
    assert tuple(inbox) == ("ARCHIVED_CAPABILITY_RECORDED",)
    assert tuple(capability) == ("NEEDS_REVIEW", "UNSUPPORTED_ATTACHMENT")
    flow = json.loads((config.publication_dir / "flow_state.json").read_text(encoding="utf-8"))
    assert flow["business_flow"]["stage"] == "BACKFILL_ARCHIVED_NEEDS_REVIEW"
    assert flow["attachment_capabilities"][0]["outcome"] == "NEEDS_REVIEW"


def test_archive_only_never_permits_a_live_pointer_advance(tmp_path: Path) -> None:
    runtime = DailyFundsRuntime(_config(tmp_path))
    result = runtime.poll(archive_only=True)
    assert result == {"ok": False, "code": "ARCHIVE_ONLY_POINTER_FORBIDDEN"}
    assert runtime.status.read()["machine_code"] == "ARCHIVE_ONLY_POINTER_FORBIDDEN"


def test_empty_live_poll_remains_fail_closed_but_backfill_can_record_a_complete_empty_scan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class EmptyClient:
        def search(self, _start, _end, _cursor):
            return DwsPage(messages=(), next_cursor="terminal-page", has_more=False)

        @staticmethod
        def selected_messages(_page):
            return ()

    runtime = DailyFundsRuntime(_config(tmp_path))
    monkeypatch.setattr(runtime, "_dws_client", lambda: EmptyClient())
    historical = runtime.poll(
        now=datetime(2026, 8, 1, tzinfo=UTC),
        start_override=datetime(2026, 7, 31, tzinfo=UTC),
        advance_pointer=False,
        allow_empty_window=True,
    )
    assert historical == {"ok": True, "pages": 1, "attachments": 0, "empty_window": True}

    live = DailyFundsRuntime(_config(tmp_path / "live"))
    monkeypatch.setattr(live, "_dws_client", lambda: EmptyClient())
    assert live.poll(now=datetime(2026, 8, 1, tzinfo=UTC))["code"] == "SOURCE_MATCH_ZERO"
    flow_text = (live.config.publication_dir / "flow_state.json").read_text(encoding="utf-8")
    assert json.loads(flow_text)["source_discovery"] == {"state": "HISTORY_EMPTY"}
    assert "group-fixture" not in flow_text


def test_live_poll_exposes_a_values_free_target_document_gate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class NonTargetClient:
        def search(self, _start, _end, _cursor):
            return DwsPage(messages=({"opaque": "message-fixture"},), next_cursor=None, has_more=False)

        @staticmethod
        def selected_messages(_page):
            return ()

    runtime = DailyFundsRuntime(_config(tmp_path))
    monkeypatch.setattr(runtime, "_dws_client", lambda: NonTargetClient())

    assert runtime.poll(now=datetime(2026, 8, 1, tzinfo=UTC))["code"] == "SOURCE_MATCH_ZERO"
    flow_text = (runtime.config.publication_dir / "flow_state.json").read_text(encoding="utf-8")
    assert json.loads(flow_text)["source_discovery"] == {"state": "TARGET_DOCUMENT_NOT_FOUND"}
    assert "message-fixture" not in flow_text


def test_auth_and_keepalive_locks_are_non_destructive(tmp_path: Path) -> None:
    runtime = DailyFundsRuntime(_config(tmp_path))
    for job, lease, code in (
        (runtime.auth_probe, "auth_probe_lock", "AUTH_PROBE_LOCK_HELD"),
        (runtime.keepalive, "keepalive_lock", "KEEPALIVE_LOCK_HELD"),
    ):
        assert runtime.state.acquire_lease(lease, "other-holder", ttl_seconds=60)
        status = job()
        assert status["human_status"] == "处理中"
        assert status["machine_code"] == code
        runtime.state.release_lease(lease, "other-holder")


def test_auth_incident_dedup_honors_the_frozen_six_hour_cooldown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import daily_funds.state as state_module

    state = RuntimeState(_config(tmp_path).state_dir)
    first = datetime(2026, 8, 1, tzinfo=UTC)
    monkeypatch.setattr(state_module, "utc_now", lambda: first)
    assert state.queue_incident("DWS_AUTH_REQUIRED") is True
    assert state.queue_incident("DWS_AUTH_REQUIRED") is False
    monkeypatch.setattr(state_module, "utc_now", lambda: first + timedelta(minutes=361))
    assert state.queue_incident("DWS_AUTH_REQUIRED") is True


def test_cloud_scheduler_uses_the_bundled_entrypoint_and_frozen_cadence() -> None:
    """Cron must use the isolated, owner-only Coolify env snapshot."""

    command = "/opt/daily-funds/scripts/run_daily_funds.py"
    wrapper = "/opt/daily-funds/scripts/run_cron_job.sh"
    cron = (ROOT / "crontab.txt").read_text(encoding="utf-8")
    assert f"*/15 * * * * root {wrapper} poll" in cron
    assert f"* * * * * root {wrapper} auth-probe" in cron
    assert f"0 * * * * root {wrapper} keepalive" in cron
    assert f"15 2 * * * root {wrapper} backfill --max-days 7" in cron
    assert f"30 3 * * * root {wrapper} observer" in cron
    assert f"10 4 * * * root {wrapper} cold-backup" in cron
    assert f"45 5 * * * root {wrapper} runtime-audit" in cron
    assert f"0 5 1 * * root {wrapper} restore-drill" in cron
    entrypoint = (ROOT / "entrypoint.sh").read_text(encoding="utf-8")
    assert "CRON_ENV_FILE=\"$STATE_DIR/cron.env\"" in entrypoint
    assert "chmod 0600 \"$CRON_ENV_FILE\"" in entrypoint
    assert "run_auth_broker.py >/dev/null 2>&1" in entrypoint
    assert "AUTH_BROKER_PID" in entrypoint
    assert "run_auth_broker.py" not in cron
    wrapper_text = (ROOT / "scripts" / "run_cron_job.sh").read_text(encoding="utf-8")
    assert command in wrapper_text
    assert '. "$CRON_ENV_FILE"' in wrapper_text
    healthcheck = (ROOT / "healthcheck.sh").read_text(encoding="utf-8")
    assert command in healthcheck
    assert "pgrep -x cron" not in healthcheck
    assert 'CRON_PID_FILE="/run/daily-funds-cron.pid"' in healthcheck
    assert '"/proc/$CRON_PID/comm"' in healthcheck
    assert 'CRON_PID_FILE="/run/daily-funds-cron.pid"' in entrypoint


@pytest.mark.parametrize("job,code", (("auth-probe", "AUTH_OK"), ("keepalive", "KEEPALIVE_OK")))
def test_successful_maintenance_probe_is_not_failed_before_first_publication(
    job: str,
    code: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Cron success tracks the maintenance operation, not publication state."""

    script = ROOT / "scripts" / "run_daily_funds.py"
    spec = importlib.util.spec_from_file_location("daily_funds_runner_test", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    calls: list[tuple[str, str, str, bool]] = []
    receipts: list[tuple[str, bool, str]] = []
    starts: list[tuple[str, str]] = []

    class FakeState:
        def record_run(self, _run_id: str, kind: str, state: str, received_code: str, *, finished: bool = False) -> None:
            calls.append((kind, state, received_code, finished))

    class FakeRuntime:
        def __init__(self) -> None:
            self.state = FakeState()

        def record_operation_receipt(self, *, job: str, succeeded: bool, code: str):
            receipts.append((job, succeeded, code))

        def record_operation_start(self, *, job: str, code: str):
            starts.append((job, code))

        def auth_probe(self):
            return {"human_status": "需处理", "machine_code": "AUTH_OK"}

        def keepalive(self):
            return {"human_status": "需处理", "machine_code": "KEEPALIVE_OK"}

    monkeypatch.setattr(module, "DailyFundsRuntime", FakeRuntime)
    assert module.main([job]) == 0
    assert calls[-1] == (job, "SUCCEEDED", code, True)
    assert starts == [(job, f"{job.upper().replace('-', '_')}_RUNNING")]
    assert receipts == [(job, True, code)]
    assert json.loads(capsys.readouterr().out)["machine_code"] == code


@pytest.mark.parametrize("job,method,code", (
    ("auth-probe", "auth_probe", "AUTH_PROBE_LOCK_HELD"),
    ("observer", "observer", "OBSERVER_LOCK_HELD"),
    ("cold-backup", "cold_backup", "PUBLISHER_LOCK_HELD"),
))
def test_runner_keeps_any_lock_held_operation_inflight(
    job: str,
    method: str,
    code: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A competing holder cannot be recorded as this invocation's success."""

    script = ROOT / "scripts" / "run_daily_funds.py"
    spec = importlib.util.spec_from_file_location("daily_funds_runner_lock_test", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    runs: list[tuple[str, str, str, bool]] = []
    starts: list[tuple[str, str]] = []
    receipts: list[tuple[str, bool, str]] = []

    class FakeState:
        def record_run(self, _run_id: str, kind: str, state: str, received_code: str, *, finished: bool = False) -> None:
            runs.append((kind, state, received_code, finished))

    class FakeRuntime:
        def __init__(self) -> None:
            self.state = FakeState()

        def record_operation_start(self, *, job: str, code: str) -> None:
            starts.append((job, code))

        def record_operation_receipt(self, *, job: str, succeeded: bool, code: str) -> None:
            receipts.append((job, succeeded, code))

        def __getattr__(self, name: str):
            if name == method:
                return lambda: {"human_status": "处理中", "machine_code": code}
            raise AttributeError(name)

    monkeypatch.setattr(module, "DailyFundsRuntime", FakeRuntime)
    assert module.main([job]) == 75
    assert starts == [(job, f"{job.upper().replace('-', '_')}_RUNNING")]
    assert receipts == []
    assert runs[-1] == (job, "SKIPPED", code, True)
    assert json.loads(capsys.readouterr().out)["machine_code"] == code


def test_operation_receipt_preserves_source_poll_truth_when_auth_probe_succeeds(tmp_path: Path) -> None:
    """DWS auth evidence cannot overwrite a prior no-source poll outcome."""

    runtime = DailyFundsRuntime(_config(tmp_path))
    poll_status = runtime.status.write("需处理", "SOURCE_MATCH_ZERO")
    runtime._write_flow_state(stage="POLL_NEEDS_ATTENTION", status=poll_status)
    runtime.status.write("需处理", "AUTH_OK")

    runtime.record_operation_receipt(job="auth-probe", succeeded=True, code="AUTH_OK")

    flow_path = runtime.config.publication_dir / "flow_state.json"
    flow_text = flow_path.read_text(encoding="utf-8")
    flow = json.loads(flow_text)
    assert flow["business_flow"]["stage"] == "POLL_NEEDS_ATTENTION"
    assert flow["business_flow"]["machine_code"] == "SOURCE_MATCH_ZERO"
    assert flow["operations"]["auth-probe"]["state"] == "SUCCEEDED"
    assert flow["operations"]["auth-probe"]["code"] == "AUTH_OK"
    assert "sender-fixture" not in flow_text


def test_operation_start_is_values_free_and_preserves_prior_poll_truth(tmp_path: Path) -> None:
    runtime = DailyFundsRuntime(_config(tmp_path))
    poll_status = runtime.status.write("需处理", "SOURCE_MATCH_ZERO")
    runtime._write_flow_state(stage="POLL_NEEDS_ATTENTION", status=poll_status)

    runtime.record_operation_start(job="poll", code="POLL_RUNNING")

    flow_path = runtime.config.publication_dir / "flow_state.json"
    flow_text = flow_path.read_text(encoding="utf-8")
    flow = json.loads(flow_text)
    assert flow["business_flow"]["stage"] == "POLL_NEEDS_ATTENTION"
    assert flow["operations"]["poll"]["state"] == "RUNNING"
    assert flow["operations"]["poll"]["code"] == "POLL_RUNNING"
    assert flow["operations"]["poll"]["started_at"].endswith("Z")
    assert "sender-fixture" not in flow_text


def test_live_poll_lock_keeps_the_business_flow_in_progress(tmp_path: Path) -> None:
    runtime = DailyFundsRuntime(_config(tmp_path))
    assert runtime.state.acquire_lease("poll_lock", "other-holder", ttl_seconds=60)
    try:
        result = runtime.poll()
    finally:
        runtime.state.release_lease("poll_lock", "other-holder")
    assert result == {"ok": False, "code": "POLL_LOCK_HELD"}
    flow = json.loads((runtime.config.publication_dir / "flow_state.json").read_text(encoding="utf-8"))
    assert flow["business_flow"]["stage"] == "POLLING"
    assert flow["business_flow"]["human_status"] == "处理中"


def test_raw_writer_preserves_direct_and_oversize_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import daily_funds.ingestion as ingestion

    monkeypatch.setattr(ingestion, "DIRECT_BLOB_MAX_BYTES", 10)
    monkeypatch.setattr(ingestion, "CHUNK_BYTES", 4)
    moment = datetime(2026, 7, 30, 8, tzinfo=UTC)
    message = {"openConversationId": "group-fixture", "senderId": "sender-fixture", "openMessageId": "msg-1", "createTime": moment.isoformat()}
    direct_payload = b"123"
    direct = DownloadedAttachment(message, "msg-1", "a" * 64, moment, 0, "a.csv", ACCOUNT_FAMILY, direct_payload, __import__("hashlib").sha256(direct_payload).hexdigest(), "text/csv")
    payload = b"0123456789abcdef"
    oversized = DownloadedAttachment(message, "msg-1", "a" * 64, moment, 1, "b.xlsx", "资金流水明细", payload, __import__("hashlib").sha256(payload).hexdigest(), None)
    staged = RawMaterializer().stage(tmp_path, (direct, oversized))
    assert staged.occurrences == 2
    assert RawMaterializer.reassemble(tmp_path, oversized.sha256) == payload
    assert RawMaterializer.readback_attachment(tmp_path, direct).payload == direct_payload
    assert RawMaterializer.readback_attachment(tmp_path, oversized).payload == payload
    RawMaterializer.readback_batch(tmp_path, (direct, oversized), staged)
    # The 30-minute overlap must produce neither a collision nor a fresh
    # batch/object version for the same source occurrence.
    repeated = RawMaterializer().stage(tmp_path, (direct, oversized))
    assert repeated.batch_id == staged.batch_id


def test_raw_materializer_canonicalizes_duplicate_overlap_and_rejects_tampered_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import daily_funds.ingestion as ingestion

    monkeypatch.setattr(ingestion, "DIRECT_BLOB_MAX_BYTES", 10)
    monkeypatch.setattr(ingestion, "CHUNK_BYTES", 4)
    moment = datetime(2026, 7, 30, 8, tzinfo=UTC)
    direct_payload = b"abc"
    direct = DownloadedAttachment(
        {"openMessageId": "msg-direct", "nested": {"a": 1}}, "msg-direct", "a" * 64, moment,
        0, "same-name.csv", ACCOUNT_FAMILY, direct_payload, __import__("hashlib").sha256(direct_payload).hexdigest(), "text/csv",
    )
    changed_payload = b"def"
    same_name_different_bytes = DownloadedAttachment(
        {"openMessageId": "msg-different"}, "msg-different", "b" * 64, moment,
        0, "same-name.csv", ACCOUNT_FAMILY, changed_payload, __import__("hashlib").sha256(changed_payload).hexdigest(), "text/csv",
    )
    oversize_payload = b"0123456789abcdef"
    oversize = DownloadedAttachment(
        {"openMessageId": "msg-oversize"}, "msg-oversize", "c" * 64, moment,
        1, "oversize.xlsx", "资金流水明细", oversize_payload, __import__("hashlib").sha256(oversize_payload).hexdigest(), None,
    )
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first = RawMaterializer().stage(first_root, (oversize, direct, direct, same_name_different_bytes))
    second = RawMaterializer().stage(second_root, (same_name_different_bytes, direct, oversize))
    assert first.occurrences == 3
    assert first.batch_id == second.batch_id
    assert len(first.attachment_hashes) == 3
    assert RawMaterializer.readback_attachment(first_root, direct).payload == direct_payload
    assert RawMaterializer.readback_attachment(first_root, same_name_different_bytes).payload == changed_payload
    assert RawMaterializer.readback_attachment(first_root, oversize).payload == oversize_payload
    RawMaterializer.readback_batch(first_root, (oversize, direct, same_name_different_bytes), first)
    message_path = second_root / "raw/messages/2026/07/30" / f"{direct.message_id_hash}.json"
    message_path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(IngestionError, match="GIT_READBACK_FAILED"):
        RawMaterializer.readback_attachment(second_root, direct)
    manifest_path = first_root / "raw/chunks/sha256" / oversize.sha256 / "reassembly.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["chunk_size_bytes"] = 999
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(IngestionError, match="GIT_READBACK_FAILED"):
        RawMaterializer.readback_attachment(first_root, oversize)
    direct_path = first_root / "raw/blobs/sha256" / direct.sha256[:2] / f"{direct.sha256}.csv"
    direct_path.write_bytes(b"truncated")
    with pytest.raises(IngestionError, match="GIT_READBACK_FAILED"):
        RawMaterializer.readback_attachment(first_root, direct)
    batch_path = first_root / "raw/batches" / f"{first.batch_id}.json"
    batch_path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(IngestionError, match="GIT_READBACK_FAILED"):
        RawMaterializer.readback_batch(first_root, (oversize, direct, same_name_different_bytes), first)


def test_sparse_writer_uses_exact_path_and_private_local_fixture_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import daily_funds.config as config_module
    import daily_funds.ingestion as ingestion

    def git(cwd: Path | None, *args: str) -> str:
        completed = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
        return completed.stdout.strip()

    origin = tmp_path / "private-origin.git"
    git(None, "init", "--bare", "--quiet", str(origin))
    seed = tmp_path / "private-seed"
    seed.mkdir()
    git(seed, "init", "--quiet")
    git(seed, "checkout", "--quiet", "-b", "main")
    git(seed, "config", "user.name", "fixture")
    git(seed, "config", "user.email", "fixture@example.invalid")
    (seed / "README.md").write_text("outside sparse scope\n", encoding="utf-8")
    (seed / SPARSE_PATH).mkdir(parents=True)
    (seed / SPARSE_PATH / "baseline.txt").write_text("inside sparse scope\n", encoding="utf-8")
    git(seed, "add", ".")
    git(seed, "commit", "--quiet", "-m", "seed")
    git(seed, "remote", "add", "origin", str(origin))
    git(seed, "push", "--quiet", "-u", "origin", "main")

    monkeypatch.setattr(config_module, "ALLOWED_PRIVATE_REPOSITORIES", frozenset({str(origin)}))
    monkeypatch.setattr(ingestion, "DIRECT_BLOB_MAX_BYTES", 10)
    monkeypatch.setattr(ingestion, "CHUNK_BYTES", 4)
    config = replace(_config(tmp_path), private_repo=str(origin))
    writer = GitSparseWriter(config)
    scope_temp = tmp_path / "scope-temp"
    scope_temp.mkdir()
    key_path = writer._write_deploy_key(scope_temp, config.git_ssh_key_b64)
    env = writer._git_environment(scope_temp, key_path)
    writer._clone_sparse(tmp_path / "strict-sparse", env=env, ref="main")
    assert not (tmp_path / "strict-sparse" / "README.md").exists()
    assert (tmp_path / "strict-sparse" / SPARSE_PATH / "baseline.txt").exists()
    assert "SSH_AUTH_SOCK" not in env
    assert env["GIT_CONFIG_GLOBAL"] == "/dev/null"
    assert "BatchMode=yes" in env["GIT_SSH_COMMAND"]

    moment = datetime(2026, 7, 30, 8, tzinfo=UTC)
    direct_payload = b"abc"
    direct = DownloadedAttachment(
        {"openMessageId": "msg-direct"}, "msg-direct", "a" * 64, moment,
        0, "same.csv", ACCOUNT_FAMILY, direct_payload, __import__("hashlib").sha256(direct_payload).hexdigest(), "text/csv",
    )
    changed_payload = b"def"
    same_name_different_bytes = DownloadedAttachment(
        {"openMessageId": "msg-different"}, "msg-different", "b" * 64, moment,
        0, "same.csv", ACCOUNT_FAMILY, changed_payload, __import__("hashlib").sha256(changed_payload).hexdigest(), "text/csv",
    )
    oversize_payload = b"0123456789abcdef"
    oversize = DownloadedAttachment(
        {"openMessageId": "msg-oversize"}, "msg-oversize", "c" * 64, moment,
        1, "oversize.xlsx", "资金流水明细", oversize_payload, __import__("hashlib").sha256(oversize_payload).hexdigest(), None,
    )
    narrow_patterns = writer._attachment_sparse_patterns((oversize, direct, same_name_different_bytes))
    assert f"{SPARSE_PATH.as_posix()}/" not in narrow_patterns
    assert all(pattern.startswith(f"{SPARSE_PATH.as_posix()}/raw/") for pattern in narrow_patterns)
    assert f"{(SPARSE_PATH / 'raw/messages/2026/07/30').as_posix()}/" in narrow_patterns
    assert f"{(SPARSE_PATH / 'raw/blobs/sha256' / direct.sha256[:2]).as_posix()}/" in narrow_patterns
    expected_batch_pattern = (SPARSE_PATH / "raw/batches" / f"{RawMaterializer._batch_details((oversize, direct, same_name_different_bytes))[0]}.json").as_posix()
    assert expected_batch_pattern in narrow_patterns
    writer._clone_sparse(tmp_path / "narrow-sparse", env=env, ref="main", patterns=narrow_patterns)
    assert not (tmp_path / "narrow-sparse" / SPARSE_PATH / "baseline.txt").exists()
    raw_writer_commands: list[tuple[str, ...]] = []
    original_git = writer._git

    def record_git(args, **kwargs):
        raw_writer_commands.append(tuple(args))
        return original_git(args, **kwargs)

    monkeypatch.setattr(writer, "_git", record_git)
    commit = writer.persist((oversize, direct, direct, same_name_different_bytes))
    assert not any(command and command[0] == "bundle" for command in raw_writer_commands)
    assert len(commit.verified_attachments) == 3
    assert {attachment.sha256 for attachment in commit.verified_attachments} == {
        direct.sha256, same_name_different_bytes.sha256, oversize.sha256,
    }
    verification = tmp_path / "verification"
    # A newly-created bare repository can retain a symbolic HEAD pointing at
    # the server default (for example ``master``) even though this fixture
    # intentionally writes only ``main``.  The production writer always
    # selects ``private_branch`` explicitly, so this independent readback must
    # do the same rather than depending on the Git implementation default.
    git(None, "clone", "--quiet", "--branch", "main", str(origin), str(verification))
    changed_paths = git(verification, "diff-tree", "--no-commit-id", "--name-only", "-r", commit.commit_sha).splitlines()
    assert changed_paths and all(path.startswith(f"{SPARSE_PATH.as_posix()}/") for path in changed_paths)
    assert RawMaterializer.readback_attachment(verification / SPARSE_PATH, direct).payload == direct_payload
    assert RawMaterializer.readback_attachment(verification / SPARSE_PATH, same_name_different_bytes).payload == changed_payload
    assert RawMaterializer.readback_attachment(verification / SPARSE_PATH, oversize).payload == oversize_payload


def test_sparse_writer_uses_shallow_clone_for_narrow_raw_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    writer = GitSparseWriter(_config(tmp_path))
    commands: list[list[str]] = []

    def fake_git(args, **_kwargs):
        commands.append(list(args))
        return ""

    monkeypatch.setattr(writer, "_git", fake_git)
    moment = datetime(2026, 7, 31, 8, tzinfo=UTC)
    payload = b"abc"
    attachment = DownloadedAttachment(
        {"openMessageId": "msg-narrow"}, "msg-narrow", "d" * 64, moment,
        0, "funds.csv", ACCOUNT_FAMILY, payload, __import__("hashlib").sha256(payload).hexdigest(), "text/csv",
    )
    patterns = writer._attachment_sparse_patterns((attachment,))
    writer._clone_sparse(tmp_path / "narrow-sparse", env={}, ref="main", patterns=patterns)

    assert commands[0][:7] == [
        "clone", "--branch", "main", "--depth=1", "--filter=blob:none", "--sparse", "--no-checkout",
    ]
    assert commands[1] == ["sparse-checkout", "set", "--no-cone", *patterns]
    assert f"{SPARSE_PATH.as_posix()}/" not in patterns
    assert all(pattern.startswith(f"{SPARSE_PATH.as_posix()}/raw/") for pattern in patterns)
    expected_batch_pattern = (SPARSE_PATH / "raw/batches" / f"{RawMaterializer._batch_details((attachment,))[0]}.json").as_posix()
    assert expected_batch_pattern in patterns
    assert writer._publication_sparse_patterns("2026-07-31") == (
        f"{(SPARSE_PATH / 'publications/2026-07-31').as_posix()}/",
    )


def test_sparse_writer_retries_standard_non_fast_forward_and_rejects_force_push(tmp_path: Path) -> None:
    commands: list[list[str]] = []
    push_attempts = 0

    def runner(command, **kwargs):
        nonlocal push_attempts
        commands.append(command)
        if command[1] == "push":
            push_attempts += 1
            if push_attempts == 1:
                return subprocess.CompletedProcess(command, 1, "", "! [rejected] HEAD -> main (fetch first)")
        return subprocess.CompletedProcess(command, 0, "", "")

    writer = GitSparseWriter(_config(tmp_path), runner=runner)
    writer._push_with_single_rebase(tmp_path, env={"PATH": "/usr/bin"})
    assert [command[1] for command in commands] == ["push", "fetch", "rebase", "push"]
    with pytest.raises(IngestionError, match="GIT_FORCE_PUSH_FORBIDDEN"):
        writer._git(["push", "--force", "origin", "HEAD:main"])


def test_source_gate_is_single_id_and_dws_environment_is_isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _config(tmp_path)
    assert config.validate() is None
    from dataclasses import replace
    from daily_funds.config import ConfigError

    with pytest.raises(ConfigError, match="SOURCE_ID_NOT_UNIQUE"):
        replace(config, group_id="group-a,group-b").validate()
    with pytest.raises(ConfigError, match="CONFIG_INVALID"):
        replace(config, sender_id="").validate()
    monkeypatch.setenv("KMFA_DWS_PROFILE", "must-not-inherit")
    monkeypatch.setenv("DWS_PROFILE", "must-not-inherit")
    env = DwsHistoryClient(config)._environment()
    assert "KMFA_DWS_PROFILE" not in env
    assert "DWS_PROFILE" not in env
    assert env["DWS_CONFIG_DIR"] == str(config.dws_config_dir)
    assert env["DWS_KEYCHAIN_DIR"] == str(config.dws_keyring_dir)
    assert env["DWS_DISABLE_KEYCHAIN"] == "1"
    assert env["DWS_CLIENT_ID"] == config.dws_client_id
    assert "XDG_DATA_HOME" not in env
    assert "DWS_CLIENT_SECRET" not in env
    default_client_config = replace(config, dws_client_id="")
    assert default_client_config.validate() is None
    assert default_client_config.validate_dws_bootstrap() is None
    assert "DWS_CLIENT_ID" not in DwsHistoryClient(default_client_config)._environment()


def test_runtime_audit_redacts_process_data_and_fails_on_coupled_skills(tmp_path: Path) -> None:
    from dataclasses import replace

    original = _config(tmp_path)
    config = replace(original, dws_keyring_dir=original.dws_config_dir.parent / "dws-keyring")
    runtime = DailyFundsRuntime(config)
    proc = tmp_path / "proc"
    (proc / "self").mkdir(parents=True)
    (proc / "101").mkdir()
    expected = {
        "state": config.state_dir,
        "publication": config.publication_dir,
        "control": config.control_dir,
        "dws_config": config.dws_config_dir,
        "dws_keyring": config.dws_keyring_dir,
    }
    mount_roots = (
        config.state_dir,
        config.publication_dir,
        config.control_dir,
        config.dws_config_dir.parent,
    )
    (proc / "self" / "mountinfo").write_text(
        "\n".join(f"1 2 3 4 {path} rw - ext4 none rw" for path in mount_roots),
        encoding="utf-8",
    )
    (proc / "101" / "cmdline").write_bytes(b"python3\x00/opt/daily-funds/scripts/run_daily_funds.py\x00secret-never-persisted")
    runtime.state.record_network_event("DWS", "AUTH_STATUS", "OK")
    result = runtime.runtime_audit(
        proc_root=proc,
        mount_checker=lambda candidate: candidate in {str(path) for path in mount_roots},
        expected_paths=expected,
    )
    assert result == {"ok": True, "code": "RUNTIME_AUDIT_OK"}
    audit_text = (config.publication_dir / "runtime_audit.json").read_text(encoding="utf-8")
    audit = json.loads(audit_text)
    assert audit["result"] == "OK"
    assert audit["dws_volume_shared"] is True
    assert audit["network_ledger"] == [{
        "service": "DWS", "operation": "AUTH_STATUS", "outcome": "OK", "count": 1,
        "last_occurred_at": audit["network_ledger"][0]["last_occurred_at"],
    }]
    assert "secret-never-persisted" not in audit_text
    assert config.group_id not in audit_text
    flow_text = (config.publication_dir / "flow_state.json").read_text(encoding="utf-8")
    flow = json.loads(flow_text)
    assert flow["schema_version"] == "kmfa.daily_funds.flow_state.v1"
    assert flow["deployment"]["runtime_state"] == "RUNTIME_AUDITED"
    assert flow["deployment"]["identity_state"] == "UNKNOWN"
    assert config.group_id not in flow_text
    (proc / "102").mkdir()
    (proc / "102" / "cmdline").write_bytes(b"python3\x00/opt/kmfa/KMOS/KMFA/skills/other/run.py")
    coupled = runtime.runtime_audit(
        proc_root=proc,
        mount_checker=lambda candidate: candidate in {str(path) for path in mount_roots},
        expected_paths=expected,
    )
    assert coupled == {"ok": False, "code": "COUPLED_SKILL_PROCESS"}
    assert "/opt/kmfa/KMOS/KMFA/skills/other" not in (config.publication_dir / "runtime_audit.json").read_text(encoding="utf-8")


def test_dws_auth_imports_only_the_dedicated_bundle_and_removes_temporary_input(tmp_path: Path) -> None:
    config = _config(tmp_path)
    commands: list[list[str]] = []
    events: list[tuple[str, str, str]] = []
    bundle_path: Path | None = None
    statuses = iter((
        {"authenticated": False, "refresh_token_valid": False},
        {"authenticated": True, "refresh_token_valid": True},
    ))

    def runner(command, **kwargs):
        nonlocal bundle_path
        commands.append(command)
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, json.dumps(next(statuses)), "")
        if command[1:3] == ["auth", "import"]:
            assert command[-2:] == ["--base64", "--force"]
            bundle_path = Path(command[command.index("--input") + 1])
            assert bundle_path.read_text(encoding="ascii") == config.dws_auth_bundle_b64
            return subprocess.CompletedProcess(command, 0, "", "")
        raise AssertionError(f"unexpected DWS command: {command}")

    DwsHistoryClient(config, runner=runner, event_sink=lambda *event: events.append(event)).ensure_authenticated()
    assert bundle_path is not None and not bundle_path.exists()
    assert sum(command[1:3] == ["auth", "status"] for command in commands) == 2
    assert sum(command[1:3] == ["auth", "import"] for command in commands) == 1
    assert events == [
        ("DWS", "AUTH_STATUS", "OK"),
        ("DWS", "AUTH_IMPORT", "OK"),
        ("DWS", "AUTH_STATUS", "OK"),
    ]


def test_dws_auth_without_recovery_bundle_requires_explicit_cloud_bootstrap(tmp_path: Path) -> None:
    config = replace(_config(tmp_path), dws_auth_bundle_b64="")
    config.validate()
    assert DailyFundsRuntime(config).preflight()["machine_code"] == "DWS_BOOTSTRAP_REQUIRED"
    commands: list[list[str]] = []
    events: list[tuple[str, str, str]] = []

    def runner(command, **kwargs):
        commands.append(command)
        assert command[1:3] == ["auth", "status"]
        return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": False, "refresh_token_valid": False}), "")

    with pytest.raises(IngestionError, match="DWS_AUTH_REQUIRED"):
        DwsHistoryClient(config, runner=runner, event_sink=lambda *event: events.append(event)).ensure_authenticated()
    assert len(commands) == 1
    assert events == [
        ("DWS", "AUTH_STATUS", "OK"),
        ("DWS", "AUTH_IMPORT", "NOT_CONFIGURED"),
    ]


def test_dws_cloud_device_bootstrap_uses_dws_default_client_and_its_own_volume(tmp_path: Path) -> None:
    config = replace(_config(tmp_path), dws_auth_bundle_b64="", dws_client_id="")
    statuses = iter((
        {"authenticated": False, "refresh_token_valid": False},
        {"authenticated": True, "refresh_token_valid": True},
    ))
    events: list[tuple[str, str, str]] = []
    interactive_commands: list[list[str]] = []

    def runner(command, **kwargs):
        assert command[1:3] == ["auth", "status"]
        return subprocess.CompletedProcess(command, 0, json.dumps(next(statuses)), "")

    def interactive_runner(command, **kwargs):
        interactive_commands.append(command)
        assert command == [config.dws_bin, "auth", "login", "--device", "--no-browser", "--yes"]
        assert "capture_output" not in kwargs
        env = kwargs["env"]
        assert env["DWS_CONFIG_DIR"] == str(config.dws_config_dir)
        assert env["DWS_KEYCHAIN_DIR"] == str(config.dws_keyring_dir)
        assert env["DWS_DISABLE_KEYCHAIN"] == "1"
        assert "DWS_CLIENT_ID" not in env
        return subprocess.CompletedProcess(command, 0, "", "")

    DwsHistoryClient(
        config,
        runner=runner,
        interactive_runner=interactive_runner,
        event_sink=lambda *event: events.append(event),
    ).bootstrap_device_auth()
    assert interactive_commands == [[config.dws_bin, "auth", "login", "--device", "--no-browser", "--yes"]]
    assert events == [
        ("DWS", "AUTH_STATUS", "OK"),
        ("DWS", "AUTH_BOOTSTRAP", "STARTED"),
        ("DWS", "AUTH_STATUS", "OK"),
        ("DWS", "AUTH_BOOTSTRAP", "OK"),
    ]


def test_runtime_bootstrap_writes_only_redacted_cloud_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import daily_funds.runtime as runtime_module

    config = replace(_config(tmp_path), dws_auth_bundle_b64="", dws_client_id="")

    class ReadyDwsClient:
        def __init__(self, received, *, event_sink=None):
            assert received == config
            assert event_sink is not None

        def bootstrap_device_auth(self):
            return None

    monkeypatch.setattr(runtime_module, "DwsHistoryClient", ReadyDwsClient)
    result = DailyFundsRuntime(config).bootstrap_dws_auth()
    receipt_path = config.control_dir / "dws_bootstrap.json"
    receipt_text = receipt_path.read_text(encoding="utf-8")
    receipt = json.loads(receipt_text)
    assert result == {"ok": True, "status": "DWS_BOOTSTRAP_READY", "human_status": "处理中"}
    assert receipt["cloud_volume_only"] is True
    assert receipt["dws_client_mode"] == "official-default"
    assert receipt["configured_client_fingerprint"] != config.dws_client_id
    assert "dws-official-default" not in receipt_text
    assert config.group_id not in receipt_text
    assert config.sender_id not in receipt_text


def test_authenticated_dws_profile_does_not_require_an_invented_app_json(tmp_path: Path) -> None:
    config = _config(tmp_path)

    def runner(command, **kwargs):
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": True, "refresh_token_valid": True}), "")
        raise AssertionError(f"unexpected DWS command: {command}")

    DwsHistoryClient(config, runner=runner).ensure_authenticated()


def test_dws_history_accepts_successful_empty_v1_envelope_and_stable_sender_id(tmp_path: Path) -> None:
    config = _config(tmp_path)

    def runner(command, **kwargs):
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": True, "refresh_token_valid": True}), "")
        if command[1:4] == ["chat", "message", "list"]:
            assert command[command.index("--group") + 1] == config.group_id
            return subprocess.CompletedProcess(command, 0, json.dumps({
                "success": True,
                "result": {"hasMore": False},
            }), "")
        raise AssertionError(f"unexpected DWS command: {command}")

    client = DwsHistoryClient(config, runner=runner)
    page = client.search(datetime(2026, 8, 1, tzinfo=UTC), datetime(2026, 8, 1, 0, 1, tzinfo=UTC), None)
    assert page == DwsPage(messages=(), next_cursor=None, has_more=False)
    message = {
        "openConversationId": config.group_id,
        "sender": "display-name-must-not-be-used-as-id",
        "senderOpenDingTalkId": config.sender_id,
        "content": "资金明细",
    }
    client.assert_exact_source(message)
    assert client.selected_messages(DwsPage(messages=(message,), next_cursor=None, has_more=False)) == (message,)


def test_dws_list_uses_beijing_boundary_and_embedded_media_source(tmp_path: Path) -> None:
    config = _config(tmp_path)
    calls: list[list[str]] = []
    responses = [
        {
            "success": True,
            "result": {
                "hasMore": True,
                "messages": [
                    {
                        "openMessageId": "message-2",
                        "openConversationId": config.group_id,
                        "senderOpenDingTalkId": config.sender_id,
                        "createTime": "2026-08-01 08:04:00",
                        "content": "资金明细 mediaId=media-fixture-2",
                    },
                    {
                        "openMessageId": "message-1",
                        "openConversationId": config.group_id,
                        "senderOpenDingTalkId": config.sender_id,
                        "createTime": "2026-08-01 08:01:00",
                        "content": "资金明细 mediaId=media-fixture-1",
                    },
                ],
            },
        },
        {"success": True, "result": {"hasMore": False, "messages": []}},
    ]

    def runner(command, **kwargs):
        calls.append(command)
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": True, "refresh_token_valid": True}), "")
        if command[1:4] == ["chat", "message", "list"]:
            return subprocess.CompletedProcess(command, 0, json.dumps(responses.pop(0)), "")
        raise AssertionError(f"unexpected DWS command: {command}")

    client = DwsHistoryClient(config, runner=runner)
    start = datetime(2026, 8, 1, tzinfo=UTC)
    first = client.search(start, datetime(2026, 8, 1, 0, 10, tzinfo=UTC), None)
    assert first.next_cursor == "2026-08-01 08:01:00"
    assert first.has_more is True
    assert client.attachment_count(first.messages[0]) == 1
    assert client.selected_messages(first) == first.messages
    second = client.search(start, datetime(2026, 8, 1, 0, 10, tzinfo=UTC), first.next_cursor)
    assert second == DwsPage(messages=(), next_cursor=None, has_more=False)
    history_calls = [call for call in calls if call[1:4] == ["chat", "message", "list"]]
    assert history_calls[0][history_calls[0].index("--time") + 1] == "2026-08-01 08:10:00"
    assert history_calls[1][history_calls[1].index("--time") + 1] == "2026-08-01 08:01:00"
    assert all(call[call.index("--direction") + 1] == "older" for call in history_calls)
    # The DWS contract makes group, user and open-DingTalk-id mutually
    # exclusive conversation selectors.  Sender filtering must stay local
    # and exact rather than turning the production request into an invalid
    # mixed-selector call.
    assert all("--group" in call for call in history_calls)
    assert all("--user" not in call and "--open-dingtalk-id" not in call for call in history_calls)


def test_dws_history_permission_denial_is_not_misreported_as_auth_loss(tmp_path: Path) -> None:
    config = _config(tmp_path)
    events: list[tuple[str, str, str]] = []

    def runner(command, **kwargs):
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": True, "refresh_token_valid": True}), "")
        if command[1:4] == ["chat", "message", "list"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({
                "success": False,
                "errorCode": "PermissionDenied",
                "errorMsg": "redacted",
            }), "")
        raise AssertionError(f"unexpected DWS command: {command}")

    with pytest.raises(IngestionError, match="DWS_HISTORY_PERMISSION_DENIED"):
        DwsHistoryClient(config, runner=runner, event_sink=lambda *event: events.append(event)).search(
            datetime(2026, 8, 1, tzinfo=UTC),
            datetime(2026, 8, 1, 0, 1, tzinfo=UTC),
            None,
        )
    assert events == [
        ("DWS", "AUTH_STATUS", "OK"),
        ("DWS", "HISTORY_LIST", "DWS_HISTORY_PERMISSION_DENIED"),
    ]


def test_dws_history_stderr_permission_denial_is_not_misreported_as_auth_loss(tmp_path: Path) -> None:
    config = _config(tmp_path)

    def runner(command, **kwargs):
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": True, "refresh_token_valid": True}), "")
        if command[1:4] == ["chat", "message", "list"]:
            return subprocess.CompletedProcess(command, 1, "", "API PermissionDenied for current user")
        raise AssertionError(f"unexpected DWS command: {command}")

    with pytest.raises(IngestionError, match="DWS_HISTORY_PERMISSION_DENIED"):
        DwsHistoryClient(config, runner=runner).search(
            datetime(2026, 8, 1, tzinfo=UTC),
            datetime(2026, 8, 1, 0, 1, tzinfo=UTC),
            None,
        )


def test_keepalive_preserves_the_specific_dws_auth_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import daily_funds.runtime as runtime_module

    class FailingDwsClient:
        def __init__(self, config, *, event_sink=None):
            assert config == expected_config
            assert event_sink is not None

        def ensure_authenticated(self):
            raise IngestionError("DWS_AUTH_REQUIRED")

    expected_config = _config(tmp_path)
    monkeypatch.setattr(runtime_module, "DwsHistoryClient", FailingDwsClient)
    status = DailyFundsRuntime(expected_config).keepalive()
    assert status["human_status"] == "需处理"
    assert status["machine_code"] == "DWS_AUTH_REQUIRED"


def test_source_gate_rejects_multiple_candidate_documents() -> None:
    account_payload = "业务日期,公司,开户行,账号,期初余额,期末余额\n2026-07-30,甲,乙,001,1.00,1.00\n".encode()
    accounts = parse_attachment(
        family=ACCOUNT_FAMILY,
        filename="资金账户明细表_20260730.csv",
        payload=account_payload,
        source=_source(account_payload, message_id_hash="a" * 64),
    )
    transaction_payload = "业务日期,公司,开户行,账号,流水号,流入,流出\n2026-07-30,甲,乙,001,t,,\n".encode()
    transactions = parse_attachment(
        family="资金流水明细",
        filename="资金流水明细_20260730.csv",
        payload=transaction_payload,
        source=_source(transaction_payload, message_id_hash="b" * 64),
    )
    moment = datetime(2026, 7, 30, tzinfo=UTC)
    assert DailyFundsRuntime._latest_complete_pair((TimedFacts(accounts, moment), TimedFacts(transactions, moment)))
    duplicate_accounts = parse_attachment(
        family=ACCOUNT_FAMILY,
        filename="资金账户明细表_20260730_v2.csv",
        payload=account_payload,
        source=_source(account_payload, message_id_hash="c" * 64),
    )
    with pytest.raises(Exception, match="SOURCE_MATCH_MULTIPLE"):
        DailyFundsRuntime._latest_complete_pair((
            TimedFacts(accounts, moment), TimedFacts(duplicate_accounts, moment), TimedFacts(transactions, moment),
        ))


def _t06_publication() -> dict[str, object]:
    return {
        "publication_id": "a" * 64,
        "business_date": "2026-07-30",
        "status": "VALID",
        "source_versions": [{"source_version": "c" * 64}, {"source_version": "d" * 64}],
        "reconciliation_difference_fen": 0,
        "threshold_snapshot": {"fixed_risk": "正常", "dynamic_flag": None},
        "created_at": "2026-07-30T12:00:00.000001Z",
        "git_commit_sha": "e" * 40,
        "d1_projection_version": "kmfa.daily_funds.d1.v1",
        "r2_manifest_sha256": "f" * 64,
        "oci_backup_state": "PENDING",
    }


def _observer_projection(business_day: date, publication_id: str) -> dict[str, object]:
    """Minimal canonical pointer + history pair for the T08 shadow observer."""

    publication = _t06_publication()
    publication.update({
        "publication_id": publication_id,
        "business_date": business_day.isoformat(),
        "created_at": f"{business_day.isoformat()}T08:00:00Z",
        "threshold_snapshot": {
            "currency": "CNY",
            "fixed": {"hard_fen": HARD_THRESHOLD_FEN, "soft_fen": SOFT_THRESHOLD_FEN},
            "floating": [],
            "fixed_risk": "正常",
            "dynamic_flag": None,
        },
    })
    return {
        "schema_version": "kmfa.daily_funds.current_projection.v1",
        "publication": publication,
        "summary": {"total_available_fen": 107},
        "daily_balances": [{
            "business_date": business_day.isoformat(),
            "ending_available_fen": 107,
            "direct_observation": True,
            "coverage_gap": False,
            "carried_forward": False,
        }],
        "runtime": {"oci_backup_state": "OK"},
    }


def _write_observer_projection(runtime: DailyFundsRuntime, business_day: date, publication_id: str) -> None:
    pointer = _observer_projection(business_day, publication_id)
    runtime.config.publication_dir.mkdir(parents=True, exist_ok=True)
    (runtime.config.publication_dir / "current.json").write_text(
        json.dumps(pointer, ensure_ascii=False), encoding="utf-8"
    )
    (runtime.config.publication_dir / "history.json").write_text(json.dumps({
        "schema_version": "kmfa.daily_funds.history.v1",
        "days": {
            business_day.isoformat(): {
                "ending_available_fen": 107,
                "direct_observation": True,
                "coverage_gap": False,
                "carried_forward": False,
                "publication_id": publication_id,
            },
        },
    }, ensure_ascii=False), encoding="utf-8")


def _observer_d1(runtime_module, monkeypatch: pytest.MonkeyPatch) -> None:
    class PointerD1:
        def __init__(self, config):
            self.config = config

        def oracle(self, publication_id: str):
            current = json.loads((self.config.publication_dir / "current.json").read_text(encoding="utf-8"))
            publication = current["publication"]
            assert publication["publication_id"] == publication_id
            return {
                "payload_json": json.dumps(
                    publication, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ) + "\n",
            }

    monkeypatch.setattr(runtime_module, "D1Projection", PointerD1)


def test_post_deploy_observer_counts_only_new_verified_business_dates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import daily_funds.runtime as runtime_module

    runtime = DailyFundsRuntime(_config(tmp_path))
    _observer_d1(runtime_module, monkeypatch)
    monkeypatch.setenv("DAILY_FUNDS_DEPLOYMENT_MARKER", "t08-fixture-deployment")
    business_days = (
        date(2026, 8, 3),  # baseline Monday: deliberately not counted
        date(2026, 8, 4),
        date(2026, 8, 5),
        date(2026, 8, 6),
        date(2026, 8, 7),
        date(2026, 8, 10),
    )
    for index, business_day in enumerate(business_days):
        publication_id = f"{index + 1:x}" * 64
        _write_observer_projection(runtime, business_day, publication_id)
        status = runtime.observer(now=datetime(business_day.year, business_day.month, business_day.day, 12, tzinfo=UTC))
        assert status["human_status"] == "已更新"
        if index == 0:
            assert runtime.state.observer_days(limit=5) == []
            assert runtime.state.observer_window()["baseline_business_date"] == business_day.isoformat()
            # A retry on the deployment baseline is evidence refresh only; it
            # must not increment the five-real-business-day counter.
            retry = runtime.observer(now=datetime(business_day.year, business_day.month, business_day.day, 13, tzinfo=UTC))
            assert retry["human_status"] == "已更新"
            assert runtime.state.observer_days(limit=5) == []
    flow = json.loads((runtime.config.publication_dir / "flow_state.json").read_text(encoding="utf-8"))
    assert flow["deployment"]["instance_state"] == "OBSERVED"
    assert flow["deployment"]["identity_state"] == "UNKNOWN"
    assert flow["post_deploy_observer"]["state"] == "COMPLETE"
    assert flow["post_deploy_observer"]["completed_business_days"] == 5
    assert [row["business_date"] for row in flow["post_deploy_observer"]["comparisons"]] == [
        "2026-08-04", "2026-08-05", "2026-08-06", "2026-08-07", "2026-08-10",
    ]
    assert all(row["amount_state"] == "ZERO_FEN" for row in flow["post_deploy_observer"]["comparisons"])
    assert runtime.config.group_id not in json.dumps(flow, ensure_ascii=False)
    assert runtime.config.sender_id not in json.dumps(flow, ensure_ascii=False)


def test_post_deploy_observer_fails_closed_when_d1_disagrees_with_pointer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import daily_funds.runtime as runtime_module

    runtime = DailyFundsRuntime(_config(tmp_path))
    monkeypatch.setenv("DAILY_FUNDS_DEPLOYMENT_MARKER", "t08-fixture-deployment")
    business_day = date(2026, 8, 3)
    _write_observer_projection(runtime, business_day, "a" * 64)

    class MismatchedD1:
        def __init__(self, _config):
            pass

        def oracle(self, _publication_id: str):
            return {"payload_json": "{\"unexpected\":true}\n"}

    monkeypatch.setattr(runtime_module, "D1Projection", MismatchedD1)
    status = runtime.observer(now=datetime(2026, 8, 3, 12, tzinfo=UTC))
    assert status["human_status"] == "需处理"
    assert status["machine_code"] == "D1_FAILED"
    assert runtime.state.observer_window() is None
    flow = json.loads((runtime.config.publication_dir / "flow_state.json").read_text(encoding="utf-8"))
    assert flow["post_deploy_observer"]["state"] == "NEEDS_ATTENTION"
    assert flow["post_deploy_observer"]["completed_business_days"] == 0


def test_observer_lock_is_status_registered_as_inflight_not_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = DailyFundsRuntime(_config(tmp_path))
    monkeypatch.setenv("DAILY_FUNDS_DEPLOYMENT_MARKER", "t08-fixture-deployment")
    runtime.record_operation_start(job="observer", code="OBSERVER_RUNNING")
    assert runtime.state.acquire_lease("observer_lock", "other-holder", ttl_seconds=60)
    try:
        status = runtime.observer(now=datetime(2026, 8, 3, 12, tzinfo=UTC))
    finally:
        runtime.state.release_lease("observer_lock", "other-holder")

    assert status["human_status"] == "处理中"
    assert status["machine_code"] == "OBSERVER_LOCK_HELD"
    flow = json.loads((runtime.config.publication_dir / "flow_state.json").read_text(encoding="utf-8"))
    assert flow["operations"]["observer"]["state"] == "RUNNING"
    assert flow["operations"]["observer"]["code"] == "OBSERVER_RUNNING"
    assert flow["post_deploy_observer"]["state"] == "WAITING_FOR_LOCK"
    assert flow["post_deploy_observer"]["last_comparison"] == "OBSERVER_LOCK_HELD"


def _t06_projection_rows() -> tuple[tuple[DailyBalance, ...], tuple[dict[str, object], ...], tuple[dict[str, object], ...]]:
    balances = (DailyBalance(date(2026, 7, 30), 107, True, False, False),)
    transactions = (
        {
            "transaction_key_hash": "1" * 64,
            "business_date": "2026-07-30",
            "inflow_fen": 10,
            "outflow_fen": 0,
            "adjustment_fen": 0,
            "internal_transfer": False,
            "source_version": "d" * 64,
            "message_id_hash": "2" * 64,
        },
        {
            "transaction_key_hash": "3" * 64,
            "business_date": "2026-07-30",
            "inflow_fen": 0,
            "outflow_fen": 3,
            "adjustment_fen": 0,
            "internal_transfer": False,
            "source_version": "d" * 64,
            "message_id_hash": "2" * 64,
        },
    )
    accounts = ({
        "account_key_hash": "4" * 64,
        "business_date": "2026-07-30",
        "company_id": "company",
        "bank_id": "bank",
        "account_alias": "4" * 64,
        "opening_available_fen": 100,
        "ending_available_fen": 107,
        "source_version": "c" * 64,
        "message_id_hash": "2" * 64,
    },)
    return balances, transactions, accounts


def _t06_attachment(payload: bytes = b"daily-funds-r2-fixture") -> DownloadedAttachment:
    return DownloadedAttachment(
        message={},
        message_id="fixture-message",
        message_id_hash="2" * 64,
        message_at=datetime(2026, 7, 30, tzinfo=UTC),
        index=0,
        filename="资金账户明细表_20260730.csv",
        family="资金账户明细表",
        payload=payload,
        sha256=sha256(payload).hexdigest(),
        mime="text/csv",
    )


def test_d1_batch_uses_cloudflare_batch_envelope(tmp_path: Path) -> None:
    class CaptureD1(D1Projection):
        def __init__(self):
            self.payload = None

        def _request(self, payload):
            self.payload = payload
            return {"success": True, "result": [{"success": True}]}

    d1 = CaptureD1()
    d1._batch((("SELECT ?,?", ["fixture", 7]),))
    assert d1.payload == {"batch": [{"sql": "SELECT ?,?", "params": ["fixture", "7"]}]}
    with pytest.raises(PublicationError, match="D1_PARAMETER_INVALID"):
        d1._batch((("SELECT ?", [True]),))


def test_d1_query_oracle_requires_both_fact_families_and_matching_ending() -> None:
    publication_id = "f" * 64
    publication = {
        "publication_id": publication_id,
        "business_date": "2026-07-30",
        "status": "VALID",
        "source_versions": [{"source_version": "a" * 64}, {"source_version": "b" * 64}],
        "reconciliation_difference_fen": 0,
        "threshold_snapshot": {"fixed_risk": "正常", "dynamic_flag": None},
        "created_at": "2026-07-30T12:00:00Z",
        "git_commit_sha": "c" * 40,
        "d1_projection_version": "kmfa.daily_funds.d1.v1",
        "r2_manifest_sha256": "d" * 64,
        "oci_backup_state": "PENDING",
    }
    payload_json = json.dumps(publication, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"

    class OracleD1(D1Projection):
        def __init__(self, check):
            self.check = check

        def _query(self, sql, params=None):
            if "FROM daily_funds_publications" in sql:
                return [{
                    "publication_id": publication_id,
                    "business_date": publication["business_date"],
                    "reconciliation_difference_fen": 0,
                    "status": "VALID",
                    "git_commit_sha": publication["git_commit_sha"],
                    "payload_json": payload_json,
                    "created_at": publication["created_at"],
                }]
            return [self.check]

    healthy = {
        "account_count": 1,
        "transaction_count": 1,
        "account_ending_fen": 107,
        "balance_count": 1,
        "balance_ending_fen": 107,
    }
    assert OracleD1(healthy).oracle(publication_id)["publication_id"] == publication_id
    with pytest.raises(PublicationError, match="D1_ORACLE_RECONCILIATION_FAILED"):
        OracleD1({**healthy, "balance_ending_fen": 106}).oracle(publication_id)
    with pytest.raises(PublicationError, match="D1_ORACLE_PROJECTION_MISSING"):
        OracleD1({**healthy, "transaction_count": 0}).oracle(publication_id)
    with pytest.raises(PublicationError, match="D1_ORACLE_PROJECTION_MISSING"):
        OracleD1({**healthy, "account_count": True}).oracle(publication_id)
    with pytest.raises(PublicationError, match="D1_ORACLE_PROJECTION_MISSING"):
        OracleD1({**healthy, "balance_ending_fen": 107.0}).oracle(publication_id)


def test_d1_projection_is_immutable_and_rejects_non_integer_projection_input() -> None:
    class CaptureD1(D1Projection):
        def __init__(self):
            self.payloads = []

        def ensure_schema(self):
            return None

        def _request(self, payload):
            self.payloads.append(payload)
            return {"success": True, "result": [{"success": True}]}

    publication = _t06_publication()
    balances, transactions, accounts = _t06_projection_rows()
    d1 = CaptureD1()
    d1.project(publication, balances, transactions, accounts)
    batch = d1.payloads[-1]["batch"]
    sql = "\n".join(statement["sql"] for statement in batch)
    assert "INSERT INTO daily_funds_publications" in sql
    assert "INSERT OR REPLACE" not in sql
    assert all(
        isinstance(parameter, str)
        for statement in batch
        for parameter in statement["params"]
    )
    d1.project(
        publication,
        balances,
        transactions,
        ({**accounts[0], "opening_available_fen": None},),
    )
    null_account_insert = next(
        statement
        for statement in d1.payloads[-1]["batch"]
        if "INSERT INTO daily_funds_account_snapshots" in statement["sql"]
    )
    assert "VALUES(?,?,?,?,?,?,NULL,?,?,?)" in null_account_insert["sql"]
    assert all(parameter is not None for parameter in null_account_insert["params"])
    with pytest.raises(PublicationError, match="PROJECTION_BALANCE_NOT_INTEGER_FEN"):
        d1.project(
            publication,
            (DailyBalance(date(2026, 7, 30), True, True, False, False),),
            transactions,
            accounts,
        )


def test_d1_projection_requires_exact_distinct_source_pair(tmp_path: Path) -> None:
    publication = _t06_publication()
    balances, transactions, accounts = _t06_projection_rows()
    d1 = D1Projection(_config(tmp_path))
    with pytest.raises(PublicationError, match="PUBLICATION_INVALID"):
        d1.project(
            {**publication, "source_versions": [
                {"source_version": "a" * 64},
                {"source_version": "b" * 64},
                {"source_version": "c" * 64},
            ]},
            balances,
            transactions,
            accounts,
        )
    with pytest.raises(PublicationError, match="PROJECTION_SOURCE_VERSION_PAIR_INVALID"):
        d1.project(
            publication,
            balances,
            tuple({**row, "source_version": "c" * 64} for row in transactions),
            accounts,
        )
    with pytest.raises(PublicationError, match="PROJECTION_SOURCE_VERSION_MISMATCH"):
        d1.project(
            {**publication, "source_versions": [
                {"source_version": "c" * 64},
                {"source_version": "e" * 64},
            ]},
            balances,
            transactions,
            accounts,
        )


def test_r2_mirror_requires_exact_object_readback_and_manifest() -> None:
    class MemoryStore:
        def __init__(self, *, corrupt_reads: bool = False):
            self.values = {}
            self.corrupt_reads = corrupt_reads

        def put_bytes(self, key, payload, *, metadata=None):
            self.values[key] = payload

        def get_bytes(self, key):
            payload = self.values[key]
            return b"corrupt" if self.corrupt_reads else payload

    attachment = _t06_attachment()
    store = MemoryStore()
    mirror = R2Mirror(store)
    manifest_sha, manifest = mirror.mirror((attachment,), git_commit_sha="e" * 40)
    assert mirror.verify_manifest(
        manifest_sha,
        expected_git_commit_sha="e" * 40,
        expected_attachment_hashes=(attachment.sha256,),
    ) == manifest
    with pytest.raises(PublicationError, match="R2_READBACK_FAILED"):
        R2Mirror(MemoryStore(corrupt_reads=True)).mirror((attachment,), git_commit_sha="e" * 40)


def test_oci_backup_requires_exact_readback() -> None:
    class CorruptStore:
        def put_bytes(self, key, payload, *, metadata=None):
            return None

        def get_bytes(self, key):
            return b"corrupt"

    with pytest.raises(PublicationError, match="OCI_BACKUP_READBACK_FAILED"):
        OciColdBackup(CorruptStore()).backup(
            publication_id="a" * 64,
            publication_sha256="b" * 64,
            publication_created_at="2026-07-30T12:00:00Z",
            git_publication_commit_sha="c" * 40,
            git_bundle=b"bundle",
            d1_export=b"export",
            r2_inventory=b"inventory",
        )


def test_oci_par_is_a_valid_dedicated_recovery_transport(tmp_path: Path) -> None:
    config = replace(
        _config(tmp_path),
        oci_endpoint_url="",
        oci_bucket="",
        oci_access_key_id="",
        oci_secret_access_key="",
        oci_par_url="https://objectstorage.example.invalid/p/token/n/namespace/b/daily-funds/o/",
    )
    config.validate()
    assert isinstance(DailyFundsRuntime(config)._oci_store(), OciParStore)


def test_oci_par_rejects_ambiguous_or_malformed_credential_modes(tmp_path: Path) -> None:
    par_url = "https://objectstorage.example.invalid/p/token/n/namespace/b/daily-funds/o/"
    with pytest.raises(ConfigError, match="OCI_CREDENTIAL_MODE_AMBIGUOUS"):
        replace(_config(tmp_path), oci_par_url=par_url).validate()
    malformed = replace(
        _config(tmp_path),
        oci_endpoint_url="",
        oci_bucket="",
        oci_access_key_id="",
        oci_secret_access_key="",
        oci_par_url="http://objectstorage.example.invalid/not-a-par",
    )
    with pytest.raises(ConfigError, match="OCI_PAR_URL_INVALID"):
        malformed.validate()


def test_oci_par_store_writes_and_reads_only_escaped_object_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    saved: dict[str, bytes] = {}

    class Response:
        status = 200

        def __init__(self, payload: bytes = b""):
            self.payload = payload

        def read(self) -> bytes:
            return self.payload

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake_urlopen(request, *, timeout):
        assert timeout == 30
        url = request.full_url if hasattr(request, "full_url") else str(request)
        method = request.get_method() if hasattr(request, "get_method") else "GET"
        if method == "PUT":
            saved[url] = request.data
            return Response()
        if url not in saved:
            raise urllib.error.HTTPError(url, 404, "not found", hdrs=None, fp=None)
        return Response(saved[url])

    monkeypatch.setattr("daily_funds.publication.urllib.request.urlopen", fake_urlopen)
    store = OciParStore(par_url="https://objectstorage.example.invalid/p/token/n/namespace/b/daily-funds/o/")
    key = "daily-funds/a file.json"
    store.put_bytes(key, b"payload", metadata={"sha256": "abc"})
    assert store.get_bytes(key) == b"payload"
    with pytest.raises(PublicationError, match="OBJECT_STORE_FAILED"):
        store.get_bytes("../outside")


def test_oci_restore_rejects_non_byte_manifest_without_adapter_error_leakage() -> None:
    class TextStore:
        def get_bytes(self, key):
            return "not-bytes"

    with pytest.raises(PublicationError, match="RESTORE_MANIFEST_UNAVAILABLE"):
        OciColdBackup(TextStore()).restore_artifacts("a" * 64)


def test_cold_backup_uses_the_same_publisher_lease_as_publication(tmp_path: Path) -> None:
    runtime = DailyFundsRuntime(_config(tmp_path))
    holder = "another-publisher"
    assert runtime.state.acquire_lease("publisher_lock", holder, ttl_seconds=60)
    try:
        status = runtime.cold_backup()
    finally:
        runtime.state.release_lease("publisher_lock", holder)
    assert status["human_status"] == "处理中"
    assert status["machine_code"] == "PUBLISHER_LOCK_HELD"


def test_cold_backup_requires_private_publication_commit_binding(tmp_path: Path) -> None:
    runtime = DailyFundsRuntime(_config(tmp_path))
    runtime.config.publication_dir.mkdir(parents=True, exist_ok=True)
    (runtime.config.publication_dir / "current.json").write_text(json.dumps({
        "publication": {
            "status": "VALID",
            "publication_id": "a" * 64,
            "r2_manifest_sha256": "b" * 64,
        },
        "runtime": {"oci_backup_state": "LAG"},
    }), encoding="utf-8")
    status = runtime.cold_backup()
    assert status["human_status"] == "需处理"
    assert status["machine_code"] == "PUBLICATION_INVALID"


def test_restore_decode_rejects_boolean_or_float_fen_without_coercion() -> None:
    publication = _t06_publication()
    publication_bytes = (json.dumps(publication, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    balances, transactions, accounts = _t06_projection_rows()
    export = {
        "publication": {
            "publication_id": publication["publication_id"],
            "business_date": publication["business_date"],
            "status": publication["status"],
            "reconciliation_difference_fen": publication["reconciliation_difference_fen"],
            "git_commit_sha": publication["git_commit_sha"],
            "payload_json": publication_bytes.decode(),
            "created_at": publication["created_at"],
        },
        "daily_balances": [{
            "business_date": balances[0].business_day.isoformat(),
            "scope": "global",
            "ending_available_fen": True,
            "direct_observation": True,
            "coverage_gap": False,
            "carried_forward": False,
        }],
        "transactions": list(transactions),
        "account_snapshots": list(accounts),
    }
    with pytest.raises(PublicationError, match="RESTORE_D1_EXPORT_INVALID"):
        RestoreOracle.decode_d1_export(
            json.dumps(export, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(),
            publication_id=str(publication["publication_id"]),
            expected_publication_sha=sha256(publication_bytes).hexdigest(),
        )


def test_oci_restore_rebuilds_d1_only_after_manifest_hash_checks(tmp_path: Path) -> None:
    class MemoryStore:
        def __init__(self):
            self.values = {}

        def put_bytes(self, key, payload, *, metadata=None):
            self.values[key] = payload

        def get_bytes(self, key):
            try:
                return self.values[key]
            except KeyError as exc:
                raise PublicationError("OBJECT_STORE_FAILED") from exc

    class RestorableD1:
        def __init__(self):
            self.calls = []

        def project(self, publication, balances, transactions, accounts):
            self.calls.append((publication, tuple(balances), tuple(transactions), tuple(accounts)))

        def oracle(self, publication_id):
            assert publication_id == "f" * 64
            return {"publication_id": publication_id, "status": "VALID", "reconciliation_difference_fen": 0}

    # The recovery test uses a real, complete Git bundle.  A non-empty byte
    # string is not enough evidence that OCI can restore the cited raw commit.
    source_repo = tmp_path / "bundle-source"
    source_repo.mkdir()
    def git(*args: str) -> str:
        completed = subprocess.run(
            ["git", *args], cwd=source_repo, capture_output=True, text=True, check=True,
        )
        return completed.stdout.strip()

    git("init", "--quiet")
    git("config", "user.name", "fixture")
    git("config", "user.email", "fixture@example.invalid")
    (source_repo / "raw.txt").write_text("fixture\\n", encoding="utf-8")
    git("add", "raw.txt")
    git("commit", "--quiet", "-m", "fixture raw")
    raw_commit = git("rev-parse", "HEAD")
    raw_bundle_path = tmp_path / "daily-funds-raw-only.bundle"
    git("bundle", "create", str(raw_bundle_path), "HEAD")

    publication = {
        "publication_id": "f" * 64,
        "business_date": "2026-07-30",
        "status": "VALID",
        "source_versions": [{"source_version": "a" * 64}, {"source_version": "b" * 64}],
        "reconciliation_difference_fen": 0,
        "threshold_snapshot": {"fixed_risk": "正常", "dynamic_flag": None},
        "created_at": "2026-07-30T12:00:00Z",
        "git_commit_sha": raw_commit,
        "d1_projection_version": "kmfa.daily_funds.d1.v1",
        "r2_manifest_sha256": "",
        "oci_backup_state": "PENDING",
    }
    r2_inventory = (json.dumps({
        "schema_version": "kmfa.daily_funds.r2_manifest.v1",
        "git_commit_sha": raw_commit,
        "objects": [],
        "created_at": "2026-07-30T12:00:00Z",
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    publication["r2_manifest_sha256"] = __import__("hashlib").sha256(r2_inventory).hexdigest()
    publication_bytes = (json.dumps(publication, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    private_publication = source_repo / "Private-KMDatabase/KMFA/daily_funds/publications/2026-07-30" / ("f" * 64 + ".json")
    private_publication.parent.mkdir(parents=True)
    private_publication.write_bytes(publication_bytes)
    git("add", str(private_publication.relative_to(source_repo)))
    git("commit", "--quiet", "-m", "fixture publication")
    publication_commit = git("rev-parse", "HEAD")
    bundle_path = tmp_path / "daily-funds.bundle"
    git("bundle", "create", str(bundle_path), "HEAD")
    d1_export = json.dumps({
        "publication": {
            "publication_id": publication["publication_id"],
            "business_date": publication["business_date"],
            "status": publication["status"],
            "reconciliation_difference_fen": publication["reconciliation_difference_fen"],
            "git_commit_sha": publication["git_commit_sha"],
            "payload_json": publication_bytes.decode(),
            "created_at": publication["created_at"],
        },
        "daily_balances": [{"business_date": "2026-07-30", "scope": "global", "ending_available_fen": 107, "direct_observation": True, "coverage_gap": False, "carried_forward": False}],
        "transactions": [
            {"transaction_key_hash": "d" * 64, "business_date": "2026-07-30", "inflow_fen": 10, "outflow_fen": 0, "adjustment_fen": 0, "internal_transfer": False, "source_version": "b" * 64, "message_id_hash": "c" * 64},
            {"transaction_key_hash": "e" * 64, "business_date": "2026-07-30", "inflow_fen": 0, "outflow_fen": 3, "adjustment_fen": 0, "internal_transfer": False, "source_version": "b" * 64, "message_id_hash": "c" * 64},
        ],
        "account_snapshots": [{"account_key_hash": "f" * 64, "business_date": "2026-07-30", "company_id": "company", "bank_id": "bank", "account_alias": "f" * 64, "opening_available_fen": 100, "ending_available_fen": 107, "source_version": "a" * 64, "message_id_hash": "c" * 64}],
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    store = MemoryStore()
    backup = OciColdBackup(store)
    manifest_sha = backup.backup(
        publication_id="f" * 64,
        publication_sha256=__import__("hashlib").sha256(publication_bytes).hexdigest(),
        publication_created_at=publication["created_at"],
        git_publication_commit_sha=publication_commit,
        git_bundle=bundle_path.read_bytes(),
        d1_export=d1_export,
        r2_inventory=r2_inventory,
    )
    assert backup.backup(
        publication_id="f" * 64,
        publication_sha256=__import__("hashlib").sha256(publication_bytes).hexdigest(),
        publication_created_at=publication["created_at"],
        git_publication_commit_sha=publication_commit,
        git_bundle=bundle_path.read_bytes(),
        d1_export=d1_export,
        r2_inventory=r2_inventory,
    ) == manifest_sha
    d1 = RestorableD1()
    restored = RestoreCoordinator(d1=d1, oci=backup).restore("f" * 64)
    assert restored.publication["publication_id"] == "f" * 64
    assert len(d1.calls) == 1
    assert d1.calls[0][1][0].ending_available_fen == 107

    legacy_manifest_key = f"daily-funds/{'f' * 64}/restore_manifest.json"
    legacy_manifest = json.loads(store.values[legacy_manifest_key])
    del legacy_manifest["git_publication_commit_sha"]
    store.values[legacy_manifest_key] = (
        json.dumps(legacy_manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    blocked_d1 = RestorableD1()
    with pytest.raises(PublicationError, match="RESTORE_MANIFEST_INVALID"):
        RestoreCoordinator(d1=blocked_d1, oci=backup).restore("f" * 64)
    assert blocked_d1.calls == []

    incomplete_store = MemoryStore()
    incomplete_backup = OciColdBackup(incomplete_store)
    with pytest.raises(PublicationError, match="OCI_BACKUP_INVALID"):
        incomplete_backup.backup(
            publication_id="f" * 64,
            publication_sha256=__import__("hashlib").sha256(publication_bytes).hexdigest(),
            publication_created_at=publication["created_at"],
            git_publication_commit_sha=raw_commit,
            git_bundle=raw_bundle_path.read_bytes(),
            d1_export=d1_export,
            r2_inventory=r2_inventory,
        )
    assert f"daily-funds/{'f' * 64}/restore_manifest.json" not in incomplete_store.values


def test_restore_rejects_non_git_bundle() -> None:
    with pytest.raises(PublicationError, match="RESTORE_GIT_BUNDLE_INVALID"):
        RestoreOracle.verify_git_bundle(b"not-a-git-bundle", expected_commit_sha="c" * 40)


class _R2Okay:
    def mirror(self, attachments, *, git_commit_sha):
        return "d" * 64, b"r2-inventory"


class _D1Failure:
    def project(self, *args, **kwargs):
        raise PublicationError("D1_FAILED")

    def oracle(self, *args, **kwargs):
        raise AssertionError("must not reach oracle")


class _OciUnused:
    def backup(self, **kwargs):
        raise AssertionError("must not reach OCI")


def test_d1_failure_does_not_advance_existing_pointer(tmp_path: Path) -> None:
    publication_dir = tmp_path / "publication"
    publication_dir.mkdir()
    pointer = publication_dir / "current.json"
    pointer.write_text('{"old":true}\n', encoding="utf-8")
    report = ReconciliationReport(
        date(2026, 7, 30),
        (AccountReconciliation("h" * 64, 100, 10, 3, 0, 0, 0, 107, 0, ("a" * 64, "b" * 64)),),
        100, 10, 3, 0, 107, 0, {}, {}, ("a" * 64, "b" * 64),
    )
    from daily_funds.ingestion import GitCommit, StagedRawBatch
    commit = GitCommit("c" * 40, StagedRawBatch("d" * 64, (), (), 0, ()), b"bundle")
    coordinator = PublicationCoordinator(
        publication_dir=publication_dir,
        status=StatusWriter(publication_dir),
        d1=_D1Failure(),
        r2=_R2Okay(),
        oci=_OciUnused(),
    )
    with pytest.raises(PublicationError) as error:
        coordinator.publish(
            report=report,
            git_commit=commit,
            attachments=(),
            daily_balances=(DailyBalance(date(2026, 7, 30), 107, True),),
            transaction_rows=(),
            private_publication_sink=lambda publication: "f" * 40,
            git_bundle_sink=lambda: b"bundle",
        )
    assert error.value.code == "D1_FAILED"
    assert pointer.read_text(encoding="utf-8") == '{"old":true}\n'


def test_r2_failure_and_oci_lag_have_distinct_pointer_semantics(tmp_path: Path) -> None:
    class MemoryStore:
        def __init__(self):
            self.values = {}

        def put_bytes(self, key, payload, *, metadata=None):
            self.values[key] = payload

        def get_bytes(self, key):
            return self.values[key]

    class D1Okay:
        def project(self, publication, balances, transactions, accounts):
            self.publication = publication

        def oracle(self, publication_id):
            return {"publication_id": publication_id}

        def export(self, publication_id):
            return b"d1-export"

    class R2Failure:
        def mirror(self, attachments, *, git_commit_sha):
            raise PublicationError("OBJECT_STORE_FAILED")

    class OciLag:
        def backup(self, **kwargs):
            raise PublicationError("OBJECT_STORE_FAILED")

    report = ReconciliationReport(
        date(2026, 7, 30),
        (AccountReconciliation("4" * 64, 100, 10, 3, 0, 0, 0, 107, 0, ("c" * 64, "d" * 64)),),
        100, 10, 3, 0, 107, 0, {"company": 107}, {"bank": 107}, ("c" * 64, "d" * 64),
        {"company": 0}, {"bank": 0},
    )
    from daily_funds.ingestion import GitCommit, StagedRawBatch
    commit = GitCommit("e" * 40, StagedRawBatch("a" * 64, (), (), 0, ()), b"bundle")
    balances, transactions, accounts = _t06_projection_rows()
    attachment = _t06_attachment()
    publication_dir = tmp_path / "publication"
    publication_dir.mkdir()
    pointer = publication_dir / "current.json"
    pointer.write_text('{"old":true}\n', encoding="utf-8")

    failed = PublicationCoordinator(
        publication_dir=publication_dir,
        status=StatusWriter(publication_dir),
        d1=D1Okay(),
        r2=R2Failure(),
        oci=OciLag(),
    )
    with pytest.raises(PublicationError, match="R2_FAILED"):
        failed.publish(
            report=report,
            git_commit=commit,
            attachments=(attachment,),
            daily_balances=balances,
            transaction_rows=transactions,
            account_rows=accounts,
            private_publication_sink=lambda publication: "f" * 40,
            git_bundle_sink=lambda: b"bundle",
        )
    assert pointer.read_text(encoding="utf-8") == '{"old":true}\n'

    mirror = R2Mirror(MemoryStore())
    pre_mirrored = mirror.mirror((attachment,), git_commit_sha=commit.commit_sha)
    lagging = PublicationCoordinator(
        publication_dir=publication_dir,
        status=StatusWriter(publication_dir),
        d1=D1Okay(),
        r2=mirror,
        oci=OciLag(),
    )
    published = lagging.publish(
        report=report,
        git_commit=commit,
        attachments=(attachment,),
        daily_balances=balances,
        transaction_rows=transactions,
        account_rows=accounts,
        private_publication_sink=lambda publication: "f" * 40,
        git_bundle_sink=lambda: b"bundle",
        pre_mirrored=pre_mirrored,
    )
    current = json.loads(pointer.read_text(encoding="utf-8"))
    assert published.oci_backup_state == "LAG"
    assert current["publication"]["status"] == "VALID"
    assert current["runtime"] == {"oci_backup_state": "LAG", "git_publication_commit_sha": "f" * 40}


def test_three_statuses_and_no_old_threshold_constants() -> None:
    assert HUMAN_STATUSES == {"已更新", "处理中", "需处理"}
    source = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "daily_funds").rglob("*.py"))
    assert "50_000_000" not in source
    assert "100_000_000" not in source
    assert "KMFA_DINGTALK_ATTENDANCE" not in source
    assert "kmfa-dws-auth" not in source


def test_daily_funds_deployment_keeps_its_auth_bundle_and_identifiers_private() -> None:
    repo = ROOT.parents[2]
    compose = (repo / "KMFA/deploy/coolify/docker-compose.yml").read_text(encoding="utf-8")
    daily_service = compose.split("\n  skills:", 1)[0]
    env_example = (repo / "KMFA/deploy/coolify/.env.example").read_text(encoding="utf-8")
    ops = (repo / ".github/workflows/coolify-ops.yml").read_text(encoding="utf-8")
    assert 'DAILY_FUNDS_DWS_AUTH_BUNDLE_B64: "${DAILY_FUNDS_DWS_AUTH_BUNDLE_B64:-}"' in daily_service
    assert "DAILY_FUNDS_DWS_AUTH_BUNDLE_B64=" in env_example
    assert "DAILY_FUNDS_DWS_CLIENT_SECRET" not in daily_service
    assert "DAILY_FUNDS_DWS_CLIENT_SECRET" not in env_example
    # A stale legacy AppSecret is explicitly pruned during the atomic-ish
    # replacement, but it is never read from GitHub Secrets or re-created.
    assert "DAILY_FUNDS_DWS_CLIENT_SECRET: ${{ secrets." not in ops
    assert '"DAILY_FUNDS_DWS_CLIENT_SECRET",' in ops
    assert "每日资金 12 个必填 secret" in ops
    assert "DAILY_FUNDS_OCI_PAR_URL" in ops
    assert "optional_keys=(DAILY_FUNDS_DWS_CLIENT_ID DAILY_FUNDS_DWS_AUTH_BUNDLE_B64)" in ops
    assert "留空时使用 DWS 官方默认客户端" in env_example
    assert "kmfa-dws-auth" not in daily_service
    assert "sync-daily-funds-secrets" in ops
    assert "|^DAILY_FUNDS_" in ops
    entrypoint = (ROOT / "entrypoint.sh").read_text(encoding="utf-8")
    assert "chmod 0700" in entrypoint
    assert "DAILY_FUNDS_DWS_KEYRING_DIR" in entrypoint
    assert "DAILY_FUNDS_RUNTIME_PATH_INVALID" in entrypoint
    assert "runtime-audit" in entrypoint
    runner = (ROOT / "scripts/run_daily_funds.py").read_text(encoding="utf-8")
    crontab = (ROOT / "crontab.txt").read_text(encoding="utf-8")
    assert "bootstrap-dws-auth" in runner
    assert "root /opt/daily-funds/scripts/run_daily_funds.py bootstrap-dws-auth" not in crontab
