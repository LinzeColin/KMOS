from __future__ import annotations

import base64
import importlib.util
import json
import subprocess
import sys
import threading
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

from daily_funds.config import ConfigError, DailyFundsConfig, r2_worst_case_monthly_usage
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
    KMFILE_METADATA_PATH,
    PersistedRawAttachment,
    RawArchiveAudit,
    RawMaterializer,
    ReopenedRawEvidence,
    SPARSE_PATH,
    StagedRawBatch,
)
from daily_funds.models import SourceRef
from daily_funds.parsing import (
    ACCOUNT_FAMILY,
    CASHFLOW_OBSERVATION_PARSER_VERSION,
    PAYMENT_REQUEST_OBSERVATION_PARSER_VERSION,
    PARSER_VERSION,
    ParseError,
    deterministic_ocr_runtime_ready,
    is_ocr_attachment,
    is_payment_request_workbook_candidate,
    parse_attachment,
    parse_cashflow_observation,
    parse_generic_structured_attachment,
    parse_ocr_attachment,
    parse_payment_request_observation,
    parse_payment_request_workbook_observation,
)
from daily_funds.publication import D1Projection, OciColdBackup, OciParStore, PublicationCoordinator, PublicationError, R2Mirror, RestoreCoordinator, RestoreOracle, S3CompatibleStore
from daily_funds.r2_guard import R2FreeTierGuard, R2GuardError
from daily_funds.reconcile import AccountReconciliation, ReconciliationError, ReconciliationReport, account_key_hash, reconcile
from daily_funds.recovery import ACTOR, RECOVERY_MAX_SECONDS, REQUEST_FILE, REQUEST_SCHEMA
from daily_funds.runtime import AttachmentCapabilityInspection, DailyFundsRuntime, TimedFacts
from daily_funds.state import RuntimeState, StatusWriter, atomic_json_write
from daily_funds.startup import raw_archive_audit_required

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
        # The unit suite has no container-provisioned Tesseract binary.  OCR
        # contract cases opt in with a mocked deterministic runner below;
        # production Compose defaults this feature to enabled.
        "DAILY_FUNDS_OCR_ENABLED": "0",
        "DAILY_FUNDS_OCR_MIN_CONFIDENCE": "0.98",
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


def test_live_payment_request_source_validation_is_independent_from_archive_and_storage_credentials(tmp_path: Path) -> None:
    config = _config(tmp_path)
    source_only = replace(
        config,
        git_ssh_key_b64="",
        private_repo="git@github.com:example/Private-Database.git",
        r2_endpoint_url="",
        r2_bucket="",
        r2_access_key_id="",
        r2_secret_access_key="",
    )

    source_only.validate_live_payment_request_source()


def test_r2_periodic_budget_is_pessimistic_and_capped_below_free_tier_40_percent(tmp_path: Path) -> None:
    config = _config(tmp_path)
    class_a, class_b, storage = r2_worst_case_monthly_usage(
        max_new_objects_per_poll=config.r2_max_new_objects_per_poll,
        max_new_bytes_per_poll=config.r2_max_new_bytes_per_poll,
    )
    assert class_a < 400_000
    assert class_b < 4_000_000
    assert storage < 4_000_000_000
    with pytest.raises(ConfigError, match="R2_FREE_TIER_BUDGET_EXCEEDED"):
        replace(config, r2_max_new_objects_per_poll=134).validate()
    with pytest.raises(ConfigError, match="R2_FREE_TIER_BUDGET_EXCEEDED"):
        replace(config, r2_max_new_bytes_per_poll=1_300_000).validate()


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
                "status": "VALID",
                "publication_id": "a" * 64,
                "ending_available_fen": 100,
                "direct_observation": True,
                "coverage_gap": False,
                "carried_forward": False,
                "account_ending_by_hash": {"b" * 64: 100},
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


def test_daily_balance_rejects_nonvalid_or_inconsistent_history_rows(tmp_path: Path) -> None:
    runtime = DailyFundsRuntime(_config(tmp_path))
    runtime._history_path.parent.mkdir(parents=True, exist_ok=True)
    report = SimpleNamespace(business_date=date(2026, 8, 1), total_ending_fen=100)
    runtime._history_path.write_text(json.dumps({
        "schema_version": "kmfa.daily_funds.history.v1",
        "days": {
            "2026-07-31": {
                "status": "PENDING",
                "publication_id": "a" * 64,
                "ending_available_fen": 100,
                "direct_observation": True,
                "coverage_gap": False,
                "carried_forward": False,
                "account_ending_by_hash": {"b" * 64: 100},
            },
        },
    }), encoding="utf-8")
    with pytest.raises(ReconciliationError, match="HISTORY_BALANCE_NOT_VALID"):
        runtime._daily_balances(report)

    runtime._history_path.write_text(json.dumps({
        "schema_version": "kmfa.daily_funds.history.v1",
        "days": {
            "2026-07-31": {
                "status": "VALID",
                "publication_id": "a" * 64,
                "ending_available_fen": 100,
                "direct_observation": True,
                "coverage_gap": False,
                "carried_forward": False,
                "account_ending_by_hash": {"b" * 64: 99},
            },
        },
    }), encoding="utf-8")
    with pytest.raises(ReconciliationError, match="HISTORY_BALANCE_TOTAL_MISMATCH"):
        runtime._daily_balances(report)

    runtime._history_path.write_text("{", encoding="utf-8")
    with pytest.raises(ReconciliationError, match="HISTORY_INVALID"):
        runtime._daily_balances(report)

    runtime._history_path.write_text(json.dumps({
        "schema_version": "kmfa.daily_funds.history.v1", "days": {},
    }), encoding="utf-8")
    (runtime.config.publication_dir / "current.json").write_text("[]", encoding="utf-8")
    with pytest.raises(ReconciliationError, match="CURRENT_PROJECTION_INVALID"):
        runtime._daily_balances(report)


def test_daily_balance_rejects_conflicting_current_pointer_mirror(tmp_path: Path) -> None:
    runtime = DailyFundsRuntime(_config(tmp_path))
    runtime._history_path.parent.mkdir(parents=True, exist_ok=True)
    runtime._history_path.write_text(json.dumps({
        "schema_version": "kmfa.daily_funds.history.v1",
        "days": {
            "2026-07-31": {
                "status": "VALID",
                "publication_id": "a" * 64,
                "ending_available_fen": 100,
                "direct_observation": True,
                "coverage_gap": False,
                "carried_forward": False,
                "account_ending_by_hash": {"b" * 64: 100},
            },
        },
    }), encoding="utf-8")
    (runtime.config.publication_dir / "current.json").write_text(json.dumps({
        "publication": {"status": "VALID"},
        "daily_balances": [{
            "business_date": "2026-07-31",
            "ending_available_fen": 101,
            "direct_observation": True,
            "coverage_gap": False,
            "carried_forward": False,
        }],
    }), encoding="utf-8")
    report = SimpleNamespace(business_date=date(2026, 8, 1), total_ending_fen=100)
    with pytest.raises(ReconciliationError, match="DAILY_BALANCE_MIRROR_CONFLICT"):
        runtime._daily_balances(report)


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


def test_threshold_control_rejects_corrupt_documents_instead_of_disabling_custom_lines(tmp_path: Path) -> None:
    control = ThresholdControl(tmp_path / "control")
    control.root.mkdir(parents=True)
    control.request_path.write_text("{", encoding="utf-8")
    with pytest.raises(ControlError, match="THRESHOLD_REQUEST_INVALID"):
        control.apply_pending()

    control.request_path.unlink()
    control.active_path.write_text("[]", encoding="utf-8")
    with pytest.raises(ControlError, match="THRESHOLD_ACTIVE_INVALID"):
        control.line((), date(2026, 8, 1))

    directory_control = ThresholdControl(tmp_path / "directory-control")
    directory_control.root.mkdir(parents=True)
    directory_control.request_path.mkdir()
    with pytest.raises(ControlError, match="THRESHOLD_REQUEST_INVALID"):
        directory_control.apply_pending()


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


def test_transaction_parser_accepts_taskpack_optional_bank_and_source_row_identity() -> None:
    account_payload = (
        "业务日期,公司,开户行,账号,期初余额,期末余额\n"
        "2026-07-30,甲公司,甲银行,001,100.00,110.00\n"
    ).encode()
    accounts = parse_attachment(
        family=ACCOUNT_FAMILY,
        filename="资金账户明细表_20260730.csv",
        payload=account_payload,
        source=_source(account_payload, message_id_hash="a" * 64),
    )
    transaction_payload = (
        "业务日期,公司,账号,流入,流出\n"
        "2026-07-30,甲公司,001,10.00,\n"
    ).encode()
    transactions = parse_attachment(
        family="资金流水明细",
        filename="资金流水明细_20260730.csv",
        payload=transaction_payload,
        source=_source(transaction_payload, message_id_hash="b" * 64),
    )

    transaction = transactions.transactions[0]
    assert transaction.bank is None
    assert transaction.transaction_id == "source-row-1"
    assert reconcile((accounts, transactions)).valid


def test_reconciliation_rejects_bankless_transaction_with_ambiguous_account_alias() -> None:
    account_payload = (
        "业务日期,公司,开户行,账号,期初余额,期末余额\n"
        "2026-07-30,甲公司,甲银行,001,100.00,100.00\n"
        "2026-07-30,甲公司,乙银行,001,100.00,100.00\n"
    ).encode()
    accounts = parse_attachment(
        family=ACCOUNT_FAMILY,
        filename="资金账户明细表_20260730.csv",
        payload=account_payload,
        source=_source(account_payload, message_id_hash="a" * 64),
    )
    transaction_payload = (
        "业务日期,公司,账号,流入,流出\n"
        "2026-07-30,甲公司,001,1.00,\n"
    ).encode()
    transactions = parse_attachment(
        family="资金流水明细",
        filename="资金流水明细_20260730.csv",
        payload=transaction_payload,
        source=_source(transaction_payload, message_id_hash="b" * 64),
    )

    with pytest.raises(ReconciliationError, match="TRANSACTION_ACCOUNT_AMBIGUOUS"):
        reconcile((accounts, transactions))


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
        "业务日期,公司,开户行,账号,期初余额,期末余额\n"
        "2026-07-30,甲,乙,001,100.00,100.00\n"
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


def test_reconciliation_rejects_prior_account_missing_from_current_snapshot() -> None:
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
    current_key = ("甲", "乙", "001")
    prior_only_key = ("丙", "丁", "002")
    with pytest.raises(ReconciliationError, match="PRIOR_ACCOUNT_MISSING_FROM_SNAPSHOT"):
        reconcile(
            (accounts, transactions),
            previous_ending_by_account={
                account_key_hash(current_key): 10_000,
                account_key_hash(prior_only_key): 50_000,
            },
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


def test_xls_parser_requires_one_plain_sheet_and_never_uses_cached_formula_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise the legacy-XLS boundary without adding a workbook writer to runtime.

    The OLE and xlrd readers are deliberately supplied as small deterministic
    fakes here.  A separate container acceptance run opens a real synthetic
    XLS fixture using the locked dependencies; this regression test fixes the
    policy decisions that must precede any cell values being read.
    """

    def biff_record(record_id: int, body: bytes = b"") -> bytes:
        return record_id.to_bytes(2, "little") + len(body).to_bytes(2, "little") + body

    state: dict[str, object] = {
        "stream": biff_record(0x0809, b"\x00\x06\x05\x00")
        + biff_record(0x0085, b"\x00\x00\x00\x00\x00\x00")
        + biff_record(0x000A),
        "paths": [["Workbook"]],
    }

    class FakeOle:
        parsing_issues: tuple[object, ...] = ()

        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def __enter__(self) -> "FakeOle":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def listdir(self, **_kwargs: object) -> list[list[str]]:
            return state["paths"]  # type: ignore[return-value]

        def openstream(self, _path: object) -> BytesIO:
            return BytesIO(state["stream"])  # type: ignore[arg-type]

    class FakeCell:
        def __init__(self, value: object, ctype: int = 1) -> None:
            self.value = value
            self.ctype = ctype

    class FakeSheet:
        nrows = 2

        def row(self, index: int) -> list[FakeCell]:
            rows = (
                [FakeCell(value) for value in ("业务日期", "公司", "开户行", "账号", "期初余额", "期末余额", "币种")],
                [
                    FakeCell(datetime(2026, 7, 30), ctype=3),
                    *[FakeCell(value) for value in ("甲", "乙", "00123", 1000.01, 1000.11, "CNY")],
                ],
            )
            return rows[index]

    class FakeBook:
        datemode = 0
        nsheets = 1

        def sheet_by_index(self, index: int) -> FakeSheet:
            assert index == 0
            return FakeSheet()

        def release_resources(self) -> None:
            return None

    book = FakeBook()
    fake_xlrd = SimpleNamespace(
        XL_CELL_DATE=3,
        open_workbook=lambda **_kwargs: book,
        xldate_as_datetime=lambda value, _datemode: value,
    )
    fake_olefile = SimpleNamespace(OleFileIO=FakeOle, DEFECT_INCORRECT=40)
    monkeypatch.setitem(sys.modules, "xlrd", fake_xlrd)
    monkeypatch.setitem(sys.modules, "olefile", fake_olefile)

    payload = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1synthetic-xls"
    facts = parse_attachment(
        family=ACCOUNT_FAMILY,
        filename="资金账户明细表_20260730.xls",
        payload=payload,
        source=_source(payload),
        mime="application/vnd.ms-excel",
    )
    assert facts.accounts[0].account == "00123"
    assert facts.accounts[0].ending_available_fen == 100011
    assert facts.parser_evidence.format == "XLS"
    assert facts.parser_evidence.magic == "OLE"

    state["stream"] = state["stream"] + biff_record(0x0006)
    with pytest.raises(ParseError, match="XLS_FORMULA_UNSUPPORTED"):
        parse_attachment(
            family=ACCOUNT_FAMILY,
            filename="资金账户明细表_20260730.xls",
            payload=payload,
            source=_source(payload),
        )

    state["stream"] = biff_record(0x0809, b"\x00\x06\x05\x00") + biff_record(0x0085, b"\x00\x00\x00\x00\x00\x00") + biff_record(0x000A)
    state["paths"] = [["Workbook"], ["_VBA_PROJECT_CUR", "VBA", "dir"]]
    with pytest.raises(ParseError, match="XLS_MACRO_UNSUPPORTED"):
        parse_attachment(
            family=ACCOUNT_FAMILY,
            filename="资金账户明细表_20260730.xls",
            payload=payload,
            source=_source(payload),
        )

    state["paths"] = [["Workbook"]]
    book.nsheets = 2
    with pytest.raises(ParseError, match="XLS_WORKSHEET_AMBIGUOUS"):
        parse_attachment(
            family=ACCOUNT_FAMILY,
            filename="资金账户明细表_20260730.xls",
            payload=payload,
            source=_source(payload),
        )

    with pytest.raises(ParseError, match="MIME_SUFFIX_MISMATCH"):
        parse_attachment(
            family=ACCOUNT_FAMILY,
            filename="资金账户明细表_20260730.xls",
            payload=payload,
            source=_source(payload),
            mime="application/pdf",
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


def _ocr_tsv(
    headers: list[str],
    values: list[str],
    *,
    value_confidence: str = "99.0",
    extra_rows: list[list[str]] | None = None,
) -> str:
    """Build a synthetic, value-free Tesseract TSV table fixture."""

    columns = [
        "level", "page_num", "block_num", "par_num", "line_num", "word_num",
        "left", "top", "width", "height", "conf", "text",
    ]
    rows = ["\t".join(columns)]
    all_rows = [(headers, "99.0"), (values, value_confidence)] + [
        (tokens, value_confidence) for tokens in (extra_rows or [])
    ]
    for line_number, (tokens, confidence) in enumerate(all_rows, 1):
        for index, token in enumerate(tokens, 1):
            rows.append("\t".join((
                "5", "1", "1", "1", str(line_number), str(index),
                str((index - 1) * 120), str(10 + (line_number - 1) * 50), "80", "20",
                confidence, token,
            )))
    return "\n".join(rows) + "\n"


def _ocr_runner(tsv: str):
    def run(command, **_kwargs):
        assert command[0] == "tesseract"
        assert command[-1] == "tsv"
        assert "chi_sim+eng" in command
        return SimpleNamespace(returncode=0, stdout=tsv, stderr="")
    return run


def _ocr_runner_by_psm(primary_tsv: str, fallback_tsv: str, calls: list[str]):
    """Return distinct deterministic OCR layouts for the two allowed PSM modes."""

    def run(command, **_kwargs):
        assert command[0] == "tesseract"
        assert command[-1] == "tsv"
        assert "chi_sim+eng" in command
        psm = command[command.index("--psm") + 1]
        calls.append(psm)
        assert psm in {"6", "11"}
        return SimpleNamespace(returncode=0, stdout=primary_tsv if psm == "6" else fallback_tsv, stderr="")

    return run


def _ocr_tsv_split_header(headers: list[str], rows: list[list[str]]) -> str:
    """Make a table whose visual header shares a row but not Tesseract lines."""

    columns = [
        "level", "page_num", "block_num", "par_num", "line_num", "word_num",
        "left", "top", "width", "height", "conf", "text",
    ]
    output = ["\t".join(columns)]
    for index, token in enumerate(headers, 1):
        output.append("\t".join((
            "5", "1", "1", "1", str(index), "1",
            str((index - 1) * 120), "10", "80", "20", "99.0", token,
        )))
    for row_index, tokens in enumerate(rows, len(headers) + 1):
        for index, token in enumerate(tokens, 1):
            output.append("\t".join((
                "5", "1", "1", "2", str(row_index), str(index),
                str((index - 1) * 120), str(60 + (row_index - len(headers) - 1) * 50), "80", "20", "99.0", token,
            )))
    return "\n".join(output) + "\n"


def test_deterministic_ocr_requires_high_confidence_and_opens_a_strict_table() -> None:
    headers = ["业务日期", "公司", "开户行", "账号", "期初余额", "期末余额", "币种"]
    values = ["2026-07-30", "甲", "乙", "001", "100.00", "110.00", "CNY"]
    payload = b"\x89PNG\r\n\x1a\nsynthetic-ocr-table"
    candidate = parse_ocr_attachment(
        family=ACCOUNT_FAMILY,
        filename="资金账户明细表_20260730.png",
        payload=payload,
        source=_source(payload),
        mime="image/png",
        runner=_ocr_runner(_ocr_tsv(headers, values)),
    )
    assert len(candidate.facts.accounts) == 1
    assert candidate.facts.parser_evidence.format == "OCR_PNG"
    assert len(candidate.layout_fingerprint) == 64

    with pytest.raises(ParseError, match="OCR_LOW_CONFIDENCE"):
        parse_ocr_attachment(
            family=ACCOUNT_FAMILY,
            filename="资金账户明细表_20260730.png",
            payload=payload,
            source=_source(payload),
            mime="image/png",
            runner=_ocr_runner(_ocr_tsv(headers, values, value_confidence="97.99")),
        )


def test_deterministic_ocr_normalizes_an_opaque_suffix_only_from_verified_magic() -> None:
    headers = ["业务日期", "公司", "开户行", "账号", "期初余额", "期末余额", "币种"]
    values = ["2026-07-30", "甲", "乙", "001", "100.00", "110.00", "CNY"]
    payload = b"\x89PNG\r\n\x1a\nopaque-client-suffix"

    assert is_ocr_attachment("opaque.client-upload", payload=payload)
    candidate = parse_ocr_attachment(
        family=ACCOUNT_FAMILY,
        filename="opaque.client-upload",
        payload=payload,
        source=_source(payload),
        mime="image/png",
        runner=_ocr_runner(_ocr_tsv(headers, values)),
    )
    assert candidate.facts.parser_evidence.suffix == ".png"

    assert not is_ocr_attachment("opaque.csv", payload=payload)
    with pytest.raises(ParseError, match="UNSUPPORTED_ATTACHMENT"):
        parse_ocr_attachment(
            family=ACCOUNT_FAMILY,
            filename="opaque.csv",
            payload=payload,
            source=_source(payload),
            mime="image/png",
            runner=_ocr_runner(_ocr_tsv(headers, values)),
        )
    with pytest.raises(ParseError, match="MIME_SUFFIX_MISMATCH"):
        parse_ocr_attachment(
            family=ACCOUNT_FAMILY,
            filename="opaque.client-upload",
            payload=payload,
            source=_source(payload),
            mime="text/plain",
            runner=_ocr_runner(_ocr_tsv(headers, values)),
        )


def test_generic_ocr_reassembles_a_visually_aligned_split_header_without_relaxing_schema() -> None:
    headers = ["业务日期", "公司", "开户行", "账号", "期初余额", "期末余额", "币种"]
    values = ["2026-07-30", "甲", "乙", "001", "100.00", "110.00", "CNY"]
    payload = b"\x89PNG\r\n\x1a\nsplit-formal-ocr-header"

    candidate = parse_ocr_attachment(
        family="资金明细",
        filename="资金明细_20260730.png",
        payload=payload,
        source=_source(payload),
        mime="image/png",
        runner=_ocr_runner(_ocr_tsv_split_header(headers, [values])),
    )

    assert candidate.facts.family == ACCOUNT_FAMILY
    assert len(candidate.facts.accounts) == 1
    assert len(candidate.facts.transactions) == 0


def test_generic_ocr_uses_sparse_layout_fallback_only_after_both_primary_headers_are_missing() -> None:
    payload = b"\x89PNG\r\n\x1a\nsparse-layout-fallback"
    primary = _ocr_tsv(["公司", "开户行", "账号"], ["甲", "乙", "001"])
    fallback = _ocr_tsv(
        ["业务日期", "公司", "账号", "流出"],
        ["2026-07-30", "甲", "001", "10.00"],
    )
    calls: list[str] = []

    candidate = parse_ocr_attachment(
        family="资金明细",
        filename="资金明细_20260730.png",
        payload=payload,
        source=_source(payload),
        mime="image/png",
        runner=_ocr_runner_by_psm(primary, fallback, calls),
    )

    assert calls == ["6", "11"]
    assert candidate.facts.family == "资金明细"
    assert len(candidate.facts.accounts) == 0
    assert len(candidate.facts.transactions) == 1


def test_generic_ocr_does_not_try_sparse_layout_after_a_primary_row_failure() -> None:
    payload = b"\x89PNG\r\n\x1a\nno-layout-retry-after-row-failure"
    primary = _ocr_tsv(
        ["业务日期", "公司", "账号", "流出"],
        ["2026-07-30", "甲", "001", ""],
    )
    fallback = _ocr_tsv(
        ["业务日期", "公司", "账号", "流出"],
        ["2026-07-30", "甲", "001", "10.00"],
    )
    calls: list[str] = []

    with pytest.raises(ParseError, match="OCR_GENERIC_FAMILY_UNRESOLVED"):
        parse_ocr_attachment(
            family="资金明细",
            filename="资金明细_20260730.png",
            payload=payload,
            source=_source(payload),
            mime="image/png",
            runner=_ocr_runner_by_psm(primary, fallback, calls),
        )

    assert calls == ["6"]


def test_generic_ocr_source_label_classifies_a_uniquely_matching_account_table() -> None:
    headers = ["业务日期", "公司", "开户行", "账号", "期初余额", "期末余额", "币种"]
    values = ["2026-07-30", "甲", "乙", "001", "100.00", "110.00", "CNY"]
    payload = b"\x89PNG\r\n\x1a\ngeneric-account-table"

    candidate = parse_ocr_attachment(
        family="资金明细",
        filename="资金明细_20260730.png",
        payload=payload,
        source=_source(payload),
        mime="image/png",
        runner=_ocr_runner(_ocr_tsv(headers, values)),
    )

    assert candidate.facts.family == ACCOUNT_FAMILY
    assert len(candidate.facts.accounts) == 1
    assert len(candidate.facts.transactions) == 0

    transaction = parse_ocr_attachment(
        family="资金明细",
        filename="资金明细_20260730.png",
        payload=payload,
        source=_source(payload),
        mime="image/png",
        runner=_ocr_runner(_ocr_tsv(
            ["业务日期", "公司", "账号", "流入", "流出"],
            ["2026-07-30", "甲", "001", "10.00", ""],
        )),
    )

    assert transaction.facts.family == "资金明细"
    assert len(transaction.facts.accounts) == 0
    assert len(transaction.facts.transactions) == 1


def test_generic_structured_source_label_requires_exactly_one_complete_schema() -> None:
    account_payload = (
        "业务日期,公司,开户行,账号,期末余额\n"
        "2026-07-30,甲,乙,001,110.00\n"
    ).encode()
    account = parse_generic_structured_attachment(
        filename="资金明细_20260730.csv",
        payload=account_payload,
        source=_source(account_payload),
        mime="text/csv",
    )
    assert account.family == ACCOUNT_FAMILY
    assert len(account.accounts) == 1

    transaction_payload = (
        "业务日期,公司,账号,流入,流出\n"
        "2026-07-30,甲,001,10.00,\n"
    ).encode()
    transaction = parse_generic_structured_attachment(
        filename="资金明细_20260730.csv",
        payload=transaction_payload,
        source=_source(transaction_payload),
        mime="text/csv",
    )
    assert transaction.family == "资金明细"
    assert len(transaction.transactions) == 1

    ambiguous_payload = (
        "业务日期,公司,开户行,账号,期末余额,流入\n"
        "2026-07-30,甲,乙,001,110.00,10.00\n"
    ).encode()
    with pytest.raises(ParseError, match="GENERIC_SOURCE_SCHEMA_AMBIGUOUS"):
        parse_generic_structured_attachment(
            filename="资金明细_20260730.csv",
            payload=ambiguous_payload,
            source=_source(ambiguous_payload),
            mime="text/csv",
        )

    broken_source = _source(account_payload)
    broken_source = replace(
        broken_source,
        attachment_sha256="0" * 64,
        source_version="0" * 64,
    )
    with pytest.raises(ParseError, match="SOURCE_PAYLOAD_HASH_MISMATCH"):
        parse_generic_structured_attachment(
            filename="资金明细_20260730.csv",
            payload=account_payload,
            source=broken_source,
            mime="text/csv",
        )


def test_generic_ocr_source_label_rejects_zero_or_multiple_complete_schemas() -> None:
    payload = b"\x89PNG\r\n\x1a\ngeneric-schema-gate"

    # Both schemas stop before a complete header can be formed.  The code is
    # more useful for a values-free capability receipt, but remains a failed
    # generic source classification rather than a fact.
    with pytest.raises(ParseError, match="OCR_GENERIC_HEADER_SCHEMA_MISSING"):
        parse_ocr_attachment(
            family="资金明细",
            filename="资金明细_20260730.png",
            payload=payload,
            source=_source(payload),
            mime="image/png",
            runner=_ocr_runner(_ocr_tsv(["公司", "开户行", "账号"], ["甲", "乙", "001"])),
        )

    # A row-level failure for one candidate plus a header failure for the
    # other is deliberately not collapsed into a misleading single phase.
    with pytest.raises(ParseError, match="OCR_GENERIC_FAMILY_UNRESOLVED"):
        parse_ocr_attachment(
            family="资金明细",
            filename="资金明细_20260730.png",
            payload=payload,
            source=_source(payload),
            mime="image/png",
            runner=_ocr_runner(_ocr_tsv(
                ["业务日期", "公司", "开户行", "账号", "期初余额", "期末余额", "币种"],
                ["2026-07-30", "甲", "乙", "001", "100.00", "", "CNY"],
            )),
        )

    with pytest.raises(ParseError, match="OCR_GENERIC_FAMILY_AMBIGUOUS"):
        parse_ocr_attachment(
            family="资金明细",
            filename="资金明细_20260730.png",
            payload=payload,
            source=_source(payload),
            mime="image/png",
            runner=_ocr_runner(_ocr_tsv(
                ["业务日期", "公司", "开户行", "账号", "期末余额", "流水号", "流入"],
                ["2026-07-30", "甲", "乙", "001", "110.00", "T-1", "10.00"],
            )),
        )


def test_cashflow_observation_ocr_requires_footer_reconciliation_without_creating_balance_facts() -> None:
    headers = ["日期", "事由", "收（付）款人", "收支类别", "转出", "收入", "银行"]
    rows = [
        ["08月07日", "付款", "", "项目成本", "40.00", "", "银行A"],
        ["08月07日", "收款", "", "其他收款", "", "50.00", "银行A"],
        ["", "", "", "合计", "40.00", "50.00", ""],
    ]
    payload = b"\x89PNG\r\n\x1a\nreceipt-payment-observation"
    observation = parse_cashflow_observation(
        family="资金明细",
        filename="资金明细_20260807.png",
        payload=payload,
        source=_source(payload),
        received_at=datetime(2026, 8, 10, tzinfo=UTC),
        mime="image/png",
        runner=_ocr_runner(_ocr_tsv(headers, rows[0], extra_rows=rows[1:])),
    )

    assert observation.business_date.isoformat() == "2026-08-07"
    assert observation.inflow_fen == 5_000
    assert observation.outflow_fen == 4_000
    assert observation.parser_evidence.parser_version == CASHFLOW_OBSERVATION_PARSER_VERSION
    assert len(observation.layout_fingerprint) == 64

    mismatched_total = rows[:-1] + [["", "", "", "合计", "40.00", "49.00", ""]]
    with pytest.raises(ParseError, match="CASHFLOW_OBSERVATION_TOTAL_MISMATCH"):
        parse_cashflow_observation(
            family="资金明细",
            filename="资金明细_20260807.png",
            payload=payload,
            source=_source(payload),
            received_at=datetime(2026, 8, 10, tzinfo=UTC),
            mime="image/png",
            runner=_ocr_runner(_ocr_tsv(headers, mismatched_total[0], extra_rows=mismatched_total[1:])),
        )


def test_cashflow_observation_reassembles_a_visually_aligned_split_ocr_header() -> None:
    headers = ["日期", "事由", "收（付）款人", "收支类别", "转出", "收入", "银行"]
    rows = [
        ["08月07日", "付款", "", "项目成本", "40.00", "", "银行A"],
        ["08月07日", "收款", "", "其他收款", "", "50.00", "银行A"],
        ["", "", "", "合计", "40.00", "50.00", ""],
    ]
    payload = b"\x89PNG\r\n\x1a\nsplit-ocr-header"
    observation = parse_cashflow_observation(
        family="资金明细",
        filename="资金明细_20260807.png",
        payload=payload,
        source=_source(payload),
        received_at=datetime(2026, 8, 10, tzinfo=UTC),
        mime="image/png",
        runner=_ocr_runner(_ocr_tsv_split_header(headers, rows)),
    )

    assert observation.business_date.isoformat() == "2026-08-07"
    assert observation.inflow_fen == 5_000
    assert observation.outflow_fen == 4_000


def test_cashflow_observation_uses_sparse_layout_fallback_only_after_missing_header() -> None:
    """PSM 11 is a layout repair, never a retry after a financial failure."""

    headers = ["日期", "事由", "收（付）款人", "收支类别", "转出", "收入", "银行"]
    rows = [
        ["08月07日", "付款", "", "项目成本", "40.00", "", "银行A"],
        ["08月07日", "收款", "", "其他收款", "", "50.00", "银行A"],
        ["", "", "", "合计", "40.00", "50.00", ""],
    ]
    payload = b"\x89PNG\r\n\x1a\nsparse-cashflow-layout"
    primary = _ocr_tsv(["日期", "事由", "收支类别"], ["08月07日", "付款", "项目成本"])
    fallback = _ocr_tsv(headers, rows[0], extra_rows=rows[1:])
    calls: list[str] = []

    observation = parse_cashflow_observation(
        family="资金明细",
        filename="资金明细_20260807.png",
        payload=payload,
        source=_source(payload),
        received_at=datetime(2026, 8, 10, tzinfo=UTC),
        mime="image/png",
        runner=_ocr_runner_by_psm(primary, fallback, calls),
    )

    assert calls == ["6", "11"]
    assert observation.business_date.isoformat() == "2026-08-07"
    assert observation.inflow_fen == 5_000
    assert observation.outflow_fen == 4_000


def test_cashflow_observation_uses_alternate_layout_only_with_exact_consensus() -> None:
    """Two alternate segmenters may repair a missing header, never one alone."""

    headers = ["日期", "事由", "收（付）款人", "收支类别", "转出", "收入", "银行"]
    rows = [
        ["08月07日", "付款", "", "项目成本", "40.00", "", "银行A"],
        ["08月07日", "收款", "", "其他收款", "", "50.00", "银行A"],
        ["", "", "", "合计", "40.00", "50.00", ""],
    ]
    payload = b"\x89PNG\r\n\x1a\nconsensus-cashflow-layout"
    missing_header = _ocr_tsv(["日期", "事由", "收支类别"], ["08月07日", "付款", "项目成本"])
    consensus = _ocr_tsv(headers, rows[0], extra_rows=rows[1:])
    calls: list[str] = []

    def runner(command, **_kwargs):
        psm = command[command.index("--psm") + 1]
        calls.append(psm)
        assert psm in {"4", "6", "11", "12"}
        return SimpleNamespace(returncode=0, stdout=consensus if psm in {"4", "12"} else missing_header, stderr="")

    observation = parse_cashflow_observation(
        family="资金明细",
        filename="资金明细_20260807.png",
        payload=payload,
        source=_source(payload),
        received_at=datetime(2026, 8, 10, tzinfo=UTC),
        mime="image/png",
        runner=runner,
    )

    assert calls == ["6", "11", "4", "12"]
    assert observation.business_date.isoformat() == "2026-08-07"
    assert observation.inflow_fen == 5_000
    assert observation.outflow_fen == 4_000


def test_cashflow_observation_rejects_disagreeing_alternate_layouts() -> None:
    headers = ["日期", "事由", "收（付）款人", "收支类别", "转出", "收入", "银行"]
    primary_rows = [
        ["08月07日", "付款", "", "项目成本", "40.00", "", "银行A"],
        ["08月07日", "收款", "", "其他收款", "", "50.00", "银行A"],
        ["", "", "", "合计", "40.00", "50.00", ""],
    ]
    alternate_rows = [
        ["08月07日", "付款", "", "项目成本", "41.00", "", "银行A"],
        ["08月07日", "收款", "", "其他收款", "", "50.00", "银行A"],
        ["", "", "", "合计", "41.00", "50.00", ""],
    ]
    payload = b"\x89PNG\r\n\x1a\ndisagreeing-cashflow-layout"
    missing_header = _ocr_tsv(["日期", "事由", "收支类别"], ["08月07日", "付款", "项目成本"])
    psm4 = _ocr_tsv(headers, primary_rows[0], extra_rows=primary_rows[1:])
    psm12 = _ocr_tsv(headers, alternate_rows[0], extra_rows=alternate_rows[1:])
    calls: list[str] = []

    def runner(command, **_kwargs):
        psm = command[command.index("--psm") + 1]
        calls.append(psm)
        output = {"4": psm4, "12": psm12}.get(psm, missing_header)
        return SimpleNamespace(returncode=0, stdout=output, stderr="")

    with pytest.raises(ParseError, match="CASHFLOW_OBSERVATION_LAYOUT_CONSENSUS_MISSING"):
        parse_cashflow_observation(
            family="资金明细",
            filename="资金明细_20260807.png",
            payload=payload,
            source=_source(payload),
            received_at=datetime(2026, 8, 10, tzinfo=UTC),
            mime="image/png",
            runner=runner,
        )

    assert calls == ["6", "11", "4", "12"]


def test_cashflow_observation_recovers_a_synthetic_ruled_table_only_after_normalized_consensus() -> None:
    """Grid removal is deterministic and still requires both strict OCR modes."""

    image_module = pytest.importorskip("PIL.Image")
    draw_module = pytest.importorskip("PIL.ImageDraw")
    width, height = 224, 128
    image = image_module.new("L", (width, height), 255)
    draw = draw_module.Draw(image)
    for x in range(0, width, 32):
        draw.line((x, 0, x, height - 1), fill=0, width=1)
    for y in range(0, height, 32):
        draw.line((0, y, width - 1, y), fill=0, width=1)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    payload = buffer.getvalue()

    headers = ["日期", "事由", "收（付）款人", "收支类别", "转出", "收入", "银行"]
    rows = [
        ["08月07日", "付款", "", "项目成本", "40.00", "", "银行A"],
        ["08月07日", "收款", "", "其他收款", "", "50.00", "银行A"],
        ["", "", "", "合计", "40.00", "50.00", ""],
    ]
    missing_header = _ocr_tsv(["日期", "事由", "收支类别"], ["08月07日", "付款", "项目成本"])
    strict_table = _ocr_tsv(headers, rows[0], extra_rows=rows[1:])
    calls: list[tuple[str, str]] = []

    def runner(command, **_kwargs):
        psm = command[command.index("--psm") + 1]
        source_name = Path(command[1]).name
        normalized = source_name == "ocr-grid-normalized.png"
        calls.append(("normalized" if normalized else "raw", psm))
        if normalized:
            with image_module.open(command[1]) as normalized_image:
                assert normalized_image.size == (width * 2, height * 2)
                assert all(pixel == 255 for pixel in normalized_image.convert("L").getdata())
            assert psm in {"6", "11"}
            return SimpleNamespace(returncode=0, stdout=strict_table, stderr="")
        assert psm in {"4", "6", "11", "12"}
        return SimpleNamespace(returncode=0, stdout=missing_header, stderr="")

    observation = parse_cashflow_observation(
        family="资金明细",
        filename="synthetic-ruled-table.png",
        payload=payload,
        source=_source(payload),
        received_at=datetime(2026, 8, 10, tzinfo=UTC),
        mime="image/png",
        runner=runner,
    )

    assert calls == [
        ("raw", "6"),
        ("raw", "11"),
        ("raw", "4"),
        ("raw", "12"),
        ("normalized", "6"),
        ("normalized", "11"),
    ]
    assert observation.business_date.isoformat() == "2026-08-07"
    assert observation.inflow_fen == 5_000
    assert observation.outflow_fen == 4_000
    assert observation.parser_evidence.parser_version == CASHFLOW_OBSERVATION_PARSER_VERSION


def test_cashflow_observation_stops_before_enhancement_after_grid_disagreement() -> None:
    """A grid-reading disagreement is a terminal ambiguity, never an enhancement trigger."""

    image_module = pytest.importorskip("PIL.Image")
    draw_module = pytest.importorskip("PIL.ImageDraw")
    image = image_module.new("L", (224, 128), 255)
    draw = draw_module.Draw(image)
    for x in range(0, 224, 32):
        draw.line((x, 0, x, 127), fill=0, width=1)
    for y in range(0, 128, 32):
        draw.line((0, y, 223, y), fill=0, width=1)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    payload = buffer.getvalue()

    headers = ["日期", "事由", "收（付）款人", "收支类别", "转出", "收入", "银行"]
    first_rows = [
        ["08月07日", "付款", "", "项目成本", "40.00", "", "银行A"],
        ["08月07日", "收款", "", "其他收款", "", "50.00", "银行A"],
        ["", "", "", "合计", "40.00", "50.00", ""],
    ]
    second_rows = [
        ["08月07日", "付款", "", "项目成本", "41.00", "", "银行A"],
        ["08月07日", "收款", "", "其他收款", "", "50.00", "银行A"],
        ["", "", "", "合计", "41.00", "50.00", ""],
    ]
    missing_header = _ocr_tsv(["日期", "事由", "收支类别"], ["08月07日", "付款", "项目成本"])
    normalized_by_psm = {
        "6": _ocr_tsv(headers, first_rows[0], extra_rows=first_rows[1:]),
        "11": _ocr_tsv(headers, second_rows[0], extra_rows=second_rows[1:]),
    }
    calls: list[tuple[str, str]] = []

    def runner(command, **_kwargs):
        psm = command[command.index("--psm") + 1]
        normalized = Path(command[1]).name == "ocr-grid-normalized.png"
        calls.append(("normalized" if normalized else "raw", psm))
        return SimpleNamespace(
            returncode=0,
            stdout=normalized_by_psm[psm] if normalized else missing_header,
            stderr="",
        )

    with pytest.raises(ParseError, match="CASHFLOW_OBSERVATION_LAYOUT_CONSENSUS_MISSING"):
        parse_cashflow_observation(
            family="资金明细",
            filename="synthetic-ruled-table-disagreement.png",
            payload=payload,
            source=_source(payload),
            received_at=datetime(2026, 8, 10, tzinfo=UTC),
            mime="image/png",
            runner=runner,
        )

    assert calls == [
        ("raw", "6"),
        ("raw", "11"),
        ("raw", "4"),
        ("raw", "12"),
        ("normalized", "6"),
        ("normalized", "11"),
    ]


def test_cashflow_observation_uses_enhanced_rendering_only_after_grid_recovery_stops() -> None:
    """Contrast rendering remains a two-segmenter layout repair, never a value fallback."""

    image_module = pytest.importorskip("PIL.Image")
    draw_module = pytest.importorskip("PIL.ImageDraw")
    image = image_module.new("L", (224, 128), 255)
    draw = draw_module.Draw(image)
    for x in range(0, 224, 32):
        draw.line((x, 0, x, 127), fill=0, width=1)
    for y in range(0, 128, 32):
        draw.line((0, y, 223, y), fill=0, width=1)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    payload = buffer.getvalue()

    headers = ["日期", "事由", "收（付）款人", "收支类别", "转出", "收入", "银行"]
    rows = [
        ["08月07日", "付款", "", "项目成本", "40.00", "", "银行A"],
        ["08月07日", "收款", "", "其他收款", "", "50.00", "银行A"],
        ["", "", "", "合计", "40.00", "50.00", ""],
    ]
    missing_header = _ocr_tsv(["日期", "事由", "收支类别"], ["08月07日", "付款", "项目成本"])
    strict_table = _ocr_tsv(headers, rows[0], extra_rows=rows[1:])
    calls: list[tuple[str, str]] = []

    def runner(command, **_kwargs):
        psm = command[command.index("--psm") + 1]
        source_name = Path(command[1]).name
        mode = "enhanced" if source_name == "ocr-enhanced.png" else "other"
        calls.append((mode, psm))
        return SimpleNamespace(
            returncode=0,
            stdout=strict_table if mode == "enhanced" else missing_header,
            stderr="",
        )

    observation = parse_cashflow_observation(
        family="资金明细",
        filename="enhanced-cashflow.png",
        payload=payload,
        source=_source(payload),
        received_at=datetime(2026, 8, 10, tzinfo=UTC),
        mime="image/png",
        runner=runner,
    )

    assert calls == [
        ("other", "6"),
        ("other", "11"),
        ("other", "4"),
        ("other", "12"),
        ("other", "6"),
        ("enhanced", "6"),
        ("enhanced", "11"),
    ]
    assert observation.business_date.isoformat() == "2026-08-07"
    assert observation.inflow_fen == 5_000
    assert observation.outflow_fen == 4_000
    assert observation.parser_evidence.parser_version == CASHFLOW_OBSERVATION_PARSER_VERSION


def test_cashflow_observation_uses_binarized_rendering_only_after_enhanced_recovery_stops() -> None:
    image_module = pytest.importorskip("PIL.Image")
    draw_module = pytest.importorskip("PIL.ImageDraw")
    image = image_module.new("L", (224, 128), 255)
    # Otsu binarization requires a non-degenerate histogram.  These fixed
    # layout-only strokes intentionally contain no business text or amounts.
    draw = draw_module.Draw(image)
    draw.line((0, 24, 223, 24), fill=0, width=1)
    draw.line((32, 0, 32, 127), fill=0, width=1)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    payload = buffer.getvalue()
    headers = ["日期", "事由", "收（付）款人", "收支类别", "转出", "收入", "银行"]
    rows = [
        ["08月07日", "付款", "", "项目成本", "40.00", "", "银行A"],
        ["08月07日", "收款", "", "其他收款", "", "50.00", "银行A"],
        ["", "", "", "合计", "40.00", "50.00", ""],
    ]
    missing_header = _ocr_tsv(["日期", "事由", "收支类别"], ["08月07日", "付款", "项目成本"])
    strict_table = _ocr_tsv(headers, rows[0], extra_rows=rows[1:])
    calls: list[tuple[str, str]] = []

    def runner(command, **_kwargs):
        psm = command[command.index("--psm") + 1]
        source_name = Path(command[1]).name
        mode = "binarized" if source_name == "ocr-binarized.png" else "other"
        calls.append((mode, psm))
        return SimpleNamespace(returncode=0, stdout=strict_table if mode == "binarized" else missing_header, stderr="")

    observation = parse_cashflow_observation(
        family="资金明细", filename="binarized-cashflow.png", payload=payload,
        source=_source(payload), received_at=datetime(2026, 8, 10, tzinfo=UTC),
        mime="image/png", runner=runner,
    )

    assert calls[-2:] == [("binarized", "6"), ("binarized", "11")]
    assert observation.business_date.isoformat() == "2026-08-07"
    assert observation.inflow_fen == 5_000
    assert observation.outflow_fen == 4_000


def test_cashflow_observation_rejects_disagreeing_enhanced_renderings() -> None:
    image_module = pytest.importorskip("PIL.Image")
    draw_module = pytest.importorskip("PIL.ImageDraw")
    image = image_module.new("L", (224, 128), 255)
    draw = draw_module.Draw(image)
    for x in range(0, 224, 32):
        draw.line((x, 0, x, 127), fill=0, width=1)
    for y in range(0, 128, 32):
        draw.line((0, y, 223, y), fill=0, width=1)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    payload = buffer.getvalue()

    headers = ["日期", "事由", "收（付）款人", "收支类别", "转出", "收入", "银行"]
    first_rows = [
        ["08月07日", "付款", "", "项目成本", "40.00", "", "银行A"],
        ["08月07日", "收款", "", "其他收款", "", "50.00", "银行A"],
        ["", "", "", "合计", "40.00", "50.00", ""],
    ]
    second_rows = [
        ["08月07日", "付款", "", "项目成本", "41.00", "", "银行A"],
        ["08月07日", "收款", "", "其他收款", "", "50.00", "银行A"],
        ["", "", "", "合计", "41.00", "50.00", ""],
    ]
    missing_header = _ocr_tsv(["日期", "事由", "收支类别"], ["08月07日", "付款", "项目成本"])
    enhanced_by_psm = {
        "6": _ocr_tsv(headers, first_rows[0], extra_rows=first_rows[1:]),
        "11": _ocr_tsv(headers, second_rows[0], extra_rows=second_rows[1:]),
    }
    calls: list[tuple[str, str]] = []

    def runner(command, **_kwargs):
        psm = command[command.index("--psm") + 1]
        enhanced = Path(command[1]).name == "ocr-enhanced.png"
        calls.append(("enhanced" if enhanced else "other", psm))
        return SimpleNamespace(
            returncode=0,
            stdout=enhanced_by_psm[psm] if enhanced else missing_header,
            stderr="",
        )

    with pytest.raises(ParseError, match="CASHFLOW_OBSERVATION_LAYOUT_CONSENSUS_MISSING"):
        parse_cashflow_observation(
            family="资金明细",
            filename="enhanced-cashflow-disagreement.png",
            payload=payload,
            source=_source(payload),
            received_at=datetime(2026, 8, 10, tzinfo=UTC),
            mime="image/png",
            runner=runner,
        )

    assert calls == [
        ("other", "6"),
        ("other", "11"),
        ("other", "4"),
        ("other", "12"),
        ("other", "6"),
        ("enhanced", "6"),
        ("enhanced", "11"),
    ]


def test_cashflow_observation_does_not_try_alternates_after_fallback_footer_failure() -> None:
    headers = ["日期", "事由", "收（付）款人", "收支类别", "转出", "收入", "银行"]
    rows = [
        ["08月07日", "付款", "", "项目成本", "40.00", "", "银行A"],
        ["08月07日", "收款", "", "其他收款", "", "50.00", "银行A"],
        ["", "", "", "合计", "40.00", "49.00", ""],
    ]
    payload = b"\x89PNG\r\n\x1a\nno-alternate-after-fallback-footer"
    missing_header = _ocr_tsv(["日期", "事由", "收支类别"], ["08月07日", "付款", "项目成本"])
    fallback = _ocr_tsv(headers, rows[0], extra_rows=rows[1:])
    calls: list[str] = []

    def runner(command, **_kwargs):
        psm = command[command.index("--psm") + 1]
        calls.append(psm)
        return SimpleNamespace(returncode=0, stdout=fallback if psm == "11" else missing_header, stderr="")

    with pytest.raises(ParseError, match="CASHFLOW_OBSERVATION_TOTAL_MISMATCH"):
        parse_cashflow_observation(
            family="资金明细",
            filename="资金明细_20260807.png",
            payload=payload,
            source=_source(payload),
            received_at=datetime(2026, 8, 10, tzinfo=UTC),
            mime="image/png",
            runner=runner,
        )

    assert calls == ["6", "11"]


def test_cashflow_observation_does_not_retry_sparse_layout_after_footer_failure() -> None:
    """A visible but inconsistent total must remain a hard failure."""

    headers = ["日期", "事由", "收（付）款人", "收支类别", "转出", "收入", "银行"]
    mismatched_rows = [
        ["08月07日", "付款", "", "项目成本", "40.00", "", "银行A"],
        ["08月07日", "收款", "", "其他收款", "", "50.00", "银行A"],
        ["", "", "", "合计", "40.00", "49.00", ""],
    ]
    payload = b"\x89PNG\r\n\x1a\nno-cashflow-footer-retry"
    primary = _ocr_tsv(headers, mismatched_rows[0], extra_rows=mismatched_rows[1:])
    fallback = _ocr_tsv(headers, mismatched_rows[0], extra_rows=mismatched_rows[1:])
    calls: list[str] = []

    with pytest.raises(ParseError, match="CASHFLOW_OBSERVATION_TOTAL_MISMATCH"):
        parse_cashflow_observation(
            family="资金明细",
            filename="资金明细_20260807.png",
            payload=payload,
            source=_source(payload),
            received_at=datetime(2026, 8, 10, tzinfo=UTC),
            mime="image/png",
            runner=_ocr_runner_by_psm(primary, fallback, calls),
        )

    assert calls == ["6"]


def test_cashflow_observation_uses_fixed_layout_template_when_money_headers_are_unreadable() -> None:
    headers = ["日期", "事由", "收（付）款人", "收支类别", "出列", "入列", "机构"]
    rows = [
        ["08月07日", "付款", "", "项目成本", "40.00", "", "机构甲"],
        ["08月07日", "收款", "", "其他收款", "", "50.00", "机构甲"],
        ["", "", "", "合计", "40.00", "50.00", ""],
    ]
    payload = b"\x89PNG\r\n\x1a\nfixed-layout-cashflow-observation"

    observation = parse_cashflow_observation(
        family="资金明细",
        filename="资金明细_20260807.png",
        payload=payload,
        source=_source(payload),
        received_at=datetime(2026, 8, 10, tzinfo=UTC),
        mime="image/png",
        runner=_ocr_runner(_ocr_tsv(headers, rows[0], extra_rows=rows[1:])),
    )

    assert observation.business_date.isoformat() == "2026-08-07"
    assert observation.inflow_fen == 5_000
    assert observation.outflow_fen == 4_000
    assert observation.parser_evidence.parser_version == CASHFLOW_OBSERVATION_PARSER_VERSION


def test_cashflow_observation_uses_headerless_geometry_only_with_repeated_dates_and_footer() -> None:
    """Unreadable captions still need a reproducible same-day table shape."""

    headers = ["列一", "列二", "列三", "列四", "列五"]
    rows = [
        ["08月07日", "付款", "40.00", "", "机构甲"],
        ["08月07日", "收款", "", "50.00", "机构甲"],
        ["", "合计", "40.00", "50.00", ""],
    ]
    payload = b"\x89PNG\r\n\x1a\nheaderless-cashflow-observation"

    observation = parse_cashflow_observation(
        family="资金明细",
        filename="资金明细_20260807.png",
        payload=payload,
        source=_source(payload),
        received_at=datetime(2026, 8, 10, tzinfo=UTC),
        mime="image/png",
        runner=_ocr_runner(_ocr_tsv(headers, rows[0], extra_rows=rows[1:])),
    )

    assert observation.business_date.isoformat() == "2026-08-07"
    assert observation.inflow_fen == 5_000
    assert observation.outflow_fen == 4_000

    with pytest.raises(ParseError, match="CASHFLOW_OBSERVATION_TOTAL_MISSING"):
        parse_cashflow_observation(
            family="资金明细",
            filename="资金明细_20260807.png",
            payload=payload,
            source=_source(payload),
            received_at=datetime(2026, 8, 10, tzinfo=UTC),
            mime="image/png",
            runner=_ocr_runner(_ocr_tsv(headers, rows[0], extra_rows=rows[1:-1])),
        )


def test_cashflow_observation_headerless_geometry_requires_independent_agreement() -> None:
    """A headerless result must be reproduced by both alternate segmenters."""

    headers = ["列一", "列二", "列三", "列四", "列五"]
    rows = [
        ["08月07日", "付款", "40.00", "", "机构甲"],
        ["08月07日", "收款", "", "50.00", "机构甲"],
        ["", "合计", "40.00", "50.00", ""],
    ]
    alternate_rows = [
        ["08月07日", "付款", "41.00", "", "机构甲"],
        ["08月07日", "收款", "", "50.00", "机构甲"],
        ["", "合计", "41.00", "50.00", ""],
    ]
    payload = b"\x89PNG\r\n\x1a\nheaderless-cashflow-consensus"
    primary = _ocr_tsv(headers, rows[0], extra_rows=rows[1:])
    alternate = _ocr_tsv(headers, alternate_rows[0], extra_rows=alternate_rows[1:])
    calls: list[str] = []

    def runner(command, **_kwargs):
        psm = command[command.index("--psm") + 1]
        calls.append(psm)
        assert psm in {"4", "6", "12"}
        return SimpleNamespace(returncode=0, stdout=alternate if psm == "12" else primary, stderr="")

    with pytest.raises(ParseError, match="CASHFLOW_OBSERVATION_LAYOUT_CONSENSUS_MISSING"):
        parse_cashflow_observation(
            family="资金明细",
            filename="资金明细_20260807.png",
            payload=payload,
            source=_source(payload),
            received_at=datetime(2026, 8, 10, tzinfo=UTC),
            mime="image/png",
            runner=runner,
        )

    assert calls == ["6", "4", "12"]


def test_cashflow_observation_headerless_geometry_rejects_third_money_column() -> None:
    """A third money column has no safe outflow/inflow identity without captions."""

    headers = ["列一", "列二", "列三", "列四", "列五", "列六"]
    rows = [
        ["08月07日", "付款", "40.00", "", "100.00", "机构甲"],
        ["08月07日", "收款", "", "50.00", "150.00", "机构甲"],
        ["", "合计", "40.00", "50.00", "150.00", ""],
    ]
    payload = b"\x89PNG\r\n\x1a\nheaderless-cashflow-third-money-column"

    with pytest.raises(ParseError, match="CASHFLOW_OBSERVATION_HEADER_AMBIGUOUS"):
        parse_cashflow_observation(
            family="资金明细",
            filename="资金明细_20260807.png",
            payload=payload,
            source=_source(payload),
            received_at=datetime(2026, 8, 10, tzinfo=UTC),
            mime="image/png",
            runner=_ocr_runner(_ocr_tsv(headers, rows[0], extra_rows=rows[1:])),
        )


def test_runtime_cashflow_observation_requires_complete_unique_day_coverage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import daily_funds.runtime as runtime_module

    config = replace(_config(tmp_path), ocr_enabled=True)
    runtime = DailyFundsRuntime(config)

    def attachment(day: str, marker: bytes, index: int) -> DownloadedAttachment:
        payload = b"\x89PNG\r\n\x1a\n" + marker
        return DownloadedAttachment(
            message={},
            message_id=f"cashflow-{index}",
            message_id_hash=(str(index) * 64)[:64],
            message_at=datetime.fromisoformat(day + "T12:00:00+00:00"),
            index=0,
            filename=f"资金明细_{day.replace('-', '')}.png",
            family="资金明细",
            payload=payload,
            sha256=sha256(payload).hexdigest(),
            mime="image/png",
        )

    first = attachment("2026-08-07", b"first", 1)
    second = attachment("2026-08-08", b"second", 2)
    monkeypatch.setattr(runtime_module, "deterministic_ocr_runtime_ready", lambda: True)

    def observed(**kwargs):
        source = kwargs["source"]
        received_at = kwargs["received_at"]
        amount = 1_000 if source.attachment_sha256 == first.sha256 else 2_000
        return SimpleNamespace(
            business_date=received_at.date(),
            inflow_fen=amount,
            outflow_fen=amount // 2,
        )

    monkeypatch.setattr(runtime_module, "parse_cashflow_observation", observed)
    verified = runtime._write_cashflow_observation((first, second))
    assert verified["status"] == "VERIFIED"
    assert verified["machine_code"] == "CASHFLOW_OBSERVATION_VERIFIED"
    assert verified["source_coverage"] == {
        "eligible_documents": 2,
        "parsed_documents": 2,
        "rejected_documents": 0,
        "distinct_business_days": 2,
    }
    assert verified["rejection_categories"] == {}
    saved = (config.publication_dir / "cashflow_observation.json").read_text(encoding="utf-8")
    assert first.sha256 not in saved
    assert second.sha256 not in saved
    assert "cashflow-1" not in saved

    opaque_first = replace(first, filename="opaque.client-upload")
    opaque_verified = runtime._write_cashflow_observation((opaque_first, second))
    assert opaque_verified["status"] == "VERIFIED"
    assert opaque_verified["source_coverage"] == {
        "eligible_documents": 2,
        "parsed_documents": 2,
        "rejected_documents": 0,
        "distinct_business_days": 2,
    }

    duplicate = attachment("2026-08-07", b"duplicate", 3)
    blocked = runtime._write_cashflow_observation((first, duplicate))
    assert blocked["status"] == "NEEDS_REVIEW"
    assert blocked["machine_code"] == "CASHFLOW_OBSERVATION_DUPLICATE_DAY"
    assert blocked["rejection_categories"] == {}
    assert blocked["points"] == []

    def footer_rejected(**_kwargs):
        raise ParseError("CASHFLOW_OBSERVATION_TOTAL_MISMATCH")

    monkeypatch.setattr(runtime_module, "parse_cashflow_observation", footer_rejected)
    rejected = runtime._write_cashflow_observation((first, second))
    assert rejected["status"] == "NEEDS_REVIEW"
    assert rejected["machine_code"] == "CASHFLOW_OBSERVATION_PARSE_NEEDS_REVIEW"
    assert rejected["rejection_categories"] == {"FOOTER_RECONCILIATION": 2}


def test_payment_request_observation_requires_fixed_title_date_label_and_total_consensus() -> None:
    image_module = pytest.importorskip("PIL.Image")
    image = image_module.new("RGB", (1000, 2000), "white")
    stream = BytesIO()
    image.save(stream, format="PNG")
    payload = stream.getvalue()

    def runner(command, **_kwargs):
        region = Path(command[1]).stem.removeprefix("payment-")
        psm = command[command.index("--psm") + 1]
        output = {
            "title": "待付款请示明细表",
            "business_date": "2026-08-21",
            "grand_total_label": "总合计",
            "grand_total": "80397.63",
        }[region]
        assert psm in {"6", "11", "12"}
        assert command[command.index("--oem") + 1] == "1"
        assert command[command.index("--dpi") + 1] == "300"
        return SimpleNamespace(returncode=0, stdout=output, stderr="")

    observation = parse_payment_request_observation(
        filename="payment-request.png",
        payload=payload,
        source=_source(payload),
        received_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
        mime="image/png",
        runner=runner,
    )
    assert observation is not None
    assert observation.business_date.isoformat() == "2026-08-21"
    assert observation.date_basis == "DOCUMENT_DAY"
    assert observation.request_total_fen == 8_039_763
    assert observation.parser_evidence.parser_version == PAYMENT_REQUEST_OBSERVATION_PARSER_VERSION
    assert len(observation.layout_fingerprint) == 64

    def disagreeing_total(command, **_kwargs):
        region = Path(command[1]).stem.removeprefix("payment-")
        psm = command[command.index("--psm") + 1]
        output = {
            "title": "待付款请示明细表",
            "business_date": "2026-08-21",
            "grand_total_label": "总合计",
            "grand_total": "80397.63" if psm != "12" else "80398.63",
        }[region]
        return SimpleNamespace(returncode=0, stdout=output, stderr="")

    with pytest.raises(ParseError, match="PAYMENT_REQUEST_TOTAL_CONSENSUS_MISSING"):
        parse_payment_request_observation(
            filename="payment-request.png",
            payload=payload,
            source=_source(payload),
            received_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
            mime="image/png",
            runner=disagreeing_total,
        )

    def non_candidate(command, **_kwargs):
        region = Path(command[1]).stem.removeprefix("payment-")
        output = "普通图片" if region == "title" else ""
        return SimpleNamespace(returncode=0, stdout=output, stderr="")

    assert parse_payment_request_observation(
        filename="payment-request.png",
        payload=payload,
        source=_source(payload),
        received_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
        mime="image/png",
        runner=non_candidate,
    ) is None


def test_payment_request_message_strip_uses_the_exact_message_day() -> None:
    image_module = pytest.importorskip("PIL.Image")
    image = image_module.new("RGB", (1261, 262), "white")
    stream = BytesIO()
    image.save(stream, format="PNG")
    payload = stream.getvalue()

    def runner(command, **_kwargs):
        region = Path(command[1]).stem.removeprefix("payment-")
        assert region in {"strip_grand_total_label", "strip_grand_total"}
        assert command[command.index("--oem") + 1] == "1"
        assert command[command.index("--dpi") + 1] == "300"
        output = {
            "strip_grand_total_label": {
                "6": "合 计",
                "11": "合计",
                "12": "合\n计",
            }[command[command.index("--psm") + 1]],
            "strip_grand_total": "80397.63",
        }[region]
        return SimpleNamespace(returncode=0, stdout=output, stderr="")

    observation = parse_payment_request_observation(
        filename="payment-request-strip.png",
        payload=payload,
        source=_source(payload),
        received_at=datetime(2026, 8, 21, 1, tzinfo=UTC),
        mime="image/png",
        runner=runner,
    )

    assert observation is not None
    assert observation.business_date.isoformat() == "2026-08-21"
    assert observation.date_basis == "MESSAGE_DAY"
    assert observation.request_total_fen == 8_039_763
    assert len(observation.layout_fingerprint) == 64

    def unrecognized_footer_label(command, **_kwargs):
        region = Path(command[1]).stem.removeprefix("payment-")
        output = "小计" if region == "strip_grand_total_label" else "80397.63"
        return SimpleNamespace(returncode=0, stdout=output, stderr="")

    with pytest.raises(ParseError, match="PAYMENT_REQUEST_GRAND_TOTAL_LABEL_MISSING"):
        parse_payment_request_observation(
            filename="payment-request-strip.png",
            payload=payload,
            source=_source(payload),
            received_at=datetime(2026, 8, 21, 1, tzinfo=UTC),
            mime="image/png",
            runner=unrecognized_footer_label,
        )

    def ocr_label_failure(command, **_kwargs):
        region = Path(command[1]).stem.removeprefix("payment-")
        return SimpleNamespace(returncode=1 if region == "strip_grand_total_label" else 0, stdout="", stderr="")

    with pytest.raises(ParseError, match="PAYMENT_REQUEST_GRAND_TOTAL_LABEL_OCR_FAILED"):
        parse_payment_request_observation(
            filename="payment-request-strip.png",
            payload=payload,
            source=_source(payload),
            received_at=datetime(2026, 8, 21, 1, tzinfo=UTC),
            mime="image/png",
            runner=ocr_label_failure,
        )

    def ocr_total_failure(command, **_kwargs):
        region = Path(command[1]).stem.removeprefix("payment-")
        return SimpleNamespace(returncode=1 if region == "strip_grand_total" else 0, stdout="", stderr="")

    with pytest.raises(ParseError, match="PAYMENT_REQUEST_TOTAL_OCR_FAILED"):
        parse_payment_request_observation(
            filename="payment-request-strip.png",
            payload=payload,
            source=_source(payload),
            received_at=datetime(2026, 8, 21, 1, tzinfo=UTC),
            mime="image/png",
            runner=ocr_total_failure,
        )

    assert DailyFundsRuntime._payment_request_rejection_category(
        ParseError("PAYMENT_REQUEST_GRAND_TOTAL_LABEL_OCR_FAILED"),
    ) == "GRAND_TOTAL_LABEL"
    assert DailyFundsRuntime._payment_request_rejection_category(
        ParseError("PAYMENT_REQUEST_TOTAL_OCR_FAILED"),
    ) == "GRAND_TOTAL"


def test_payment_request_observation_renders_a_single_page_scanned_pdf() -> None:
    image_module = pytest.importorskip("PIL.Image")
    rendered = image_module.new("RGB", (1000, 2000), "white")
    payload = b"%PDF-1.4\nsynthetic-payment-request\n"

    def runner(command, **_kwargs):
        executable = Path(command[0]).name
        if executable == "pdfinfo":
            return SimpleNamespace(returncode=0, stdout="Pages: 1\n", stderr="")
        if executable == "pdftoppm":
            rendered.save(f"{command[-1]}-1.png", format="PNG")
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        region = Path(command[1]).stem.removeprefix("payment-")
        output = {
            "title": "待付款请示明细表",
            "business_date": "2026-08-21",
            "grand_total_label": "总合计",
            "grand_total": "100.00",
        }[region]
        return SimpleNamespace(returncode=0, stdout=output, stderr="")

    observation = parse_payment_request_observation(
        filename="payment-request.pdf",
        payload=payload,
        source=_source(payload),
        received_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
        mime="application/pdf",
        runner=runner,
    )

    assert observation is not None
    assert observation.business_date.isoformat() == "2026-08-21"
    assert observation.request_total_fen == 10_000
    assert observation.parser_evidence.magic == "PDF"


def _payment_request_workbook_payload(*, grand_total: str = "250.00") -> bytes:
    openpyxl = pytest.importorskip("openpyxl")
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["申请编号", "收款单位", "本周支付"])
    sheet.append(["REQ-01", "单位甲", "100.00"])
    sheet.append(["REQ-02", "单位乙", "150.00"])
    sheet.append([None, "总合计", grand_total])
    stream = BytesIO()
    workbook.save(stream)
    workbook.close()
    return stream.getvalue()


def test_payment_request_workbook_requires_filename_day_detail_rows_and_grand_total() -> None:
    payload = _payment_request_workbook_payload()
    filename = "项目资金计划2026.08.21.xlsx"

    assert is_payment_request_workbook_candidate(filename)
    observation = parse_payment_request_workbook_observation(
        filename=filename,
        payload=payload,
        source=_source(payload),
        received_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    assert observation is not None
    assert observation.business_date.isoformat() == "2026-08-21"
    assert observation.date_basis == "FILENAME_DAY"
    assert observation.request_total_fen == 25_000
    assert observation.parser_evidence.parser_version == PAYMENT_REQUEST_OBSERVATION_PARSER_VERSION
    assert len(observation.layout_fingerprint) == 64
    assert parse_payment_request_workbook_observation(
        filename="普通文件2026.08.21.xlsx",
        payload=payload,
        source=_source(payload),
        received_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ) is None

    message_day_observation = parse_payment_request_workbook_observation(
        filename="项目资金计划.xlsx",
        payload=payload,
        source=_source(payload),
        received_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert message_day_observation is not None
    assert message_day_observation.business_date.isoformat() == "2026-08-21"
    assert message_day_observation.date_basis == "MESSAGE_DAY"

    mismatched_payload = _payment_request_workbook_payload(grand_total="240.00")
    with pytest.raises(ParseError, match="PAYMENT_REQUEST_TOTAL_RECONCILIATION_MISSING"):
        parse_payment_request_workbook_observation(
            filename=filename,
            payload=mismatched_payload,
            source=_source(mismatched_payload),
            received_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


def test_runtime_payment_request_workbook_does_not_depend_on_ocr(tmp_path: Path) -> None:
    config = replace(_config(tmp_path), ocr_enabled=False)
    runtime = DailyFundsRuntime(config)
    payload = _payment_request_workbook_payload()
    attachment = DownloadedAttachment(
        message={},
        message_id="payment-workbook",
        message_id_hash="f" * 64,
        message_at=datetime(2026, 8, 21, 12, tzinfo=UTC),
        index=0,
        filename="项目资金计划2026.08.21.xlsx",
        family=None,
        payload=payload,
        sha256=sha256(payload).hexdigest(),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    verified = runtime._write_payment_request_observation((attachment,))

    assert verified["status"] == "VERIFIED"
    assert verified["machine_code"] == "PAYMENT_REQUEST_OBSERVATION_VERIFIED"
    assert verified["source_coverage"] == {
        "eligible_documents": 1,
        "parsed_documents": 1,
        "rejected_documents": 0,
        "distinct_business_days": 1,
        "superseded_reports": 0,
    }
    assert verified["points"] == [{
        "business_date": "2026-08-21",
        "date_basis": "FILENAME_DAY",
        "request_total_fen": 25_000,
    }]


def test_payment_request_compact_layouts_keep_the_existing_fixed_crops() -> None:
    import daily_funds.parsing as parsing_module

    sheet_layout, sheet_crops = parsing_module._payment_request_layout_and_crops(
        width=320,
        height=450,
    )
    strip_layout, strip_crops = parsing_module._payment_request_layout_and_crops(
        width=480,
        height=120,
    )

    assert sheet_layout == "SHEET"
    assert sheet_crops == parsing_module._PAYMENT_REQUEST_SHEET_CROPS
    assert strip_layout == "MESSAGE_STRIP"
    assert strip_crops == parsing_module._PAYMENT_REQUEST_MESSAGE_STRIP_CROPS


def test_runtime_payment_request_observation_exposes_verified_latest_request_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import daily_funds.runtime as runtime_module

    config = replace(_config(tmp_path), ocr_enabled=True)
    runtime = DailyFundsRuntime(config)

    def attachment(day: str, marker: bytes, index: int) -> DownloadedAttachment:
        payload = b"\x89PNG\r\n\x1a\n" + marker
        return DownloadedAttachment(
            message={},
            message_id=f"payment-{index}",
            message_id_hash=(str(index) * 64)[:64],
            message_at=datetime.fromisoformat(day + "T12:00:00+00:00"),
            index=0,
            filename=f"payment-{index}.png",
            family=None,
            payload=payload,
            sha256=sha256(payload).hexdigest(),
            mime="image/png",
        )

    first = attachment("2026-08-20", b"first", 1)
    second = attachment("2026-08-21", b"second", 2)
    monkeypatch.setattr(runtime_module, "deterministic_ocr_runtime_ready", lambda: True)

    def observed(**kwargs):
        source = kwargs["source"]
        received_at = kwargs["received_at"]
        total = 8_000 if source.attachment_sha256 == first.sha256 else 9_000
        return SimpleNamespace(
            business_date=received_at.date(),
            date_basis="DOCUMENT_DAY",
            request_total_fen=total,
        )

    monkeypatch.setattr(runtime_module, "parse_payment_request_observation", observed)
    verified = runtime._write_payment_request_observation((first, second))
    assert verified["status"] == "VERIFIED"
    assert verified["machine_code"] == "PAYMENT_REQUEST_OBSERVATION_VERIFIED"
    assert verified["source_coverage"] == {
        "eligible_documents": 2,
        "parsed_documents": 2,
        "rejected_documents": 0,
        "distinct_business_days": 2,
        "superseded_reports": 0,
    }
    assert [point["request_total_fen"] for point in verified["points"]] == [8_000, 9_000]
    saved = (config.publication_dir / "payment_request_observation.json").read_text(encoding="utf-8")
    assert first.sha256 not in saved
    assert second.sha256 not in saved

    def rejected(**_kwargs):
        raise ParseError("PAYMENT_REQUEST_TOTAL_CONSENSUS_MISSING")

    monkeypatch.setattr(runtime_module, "parse_payment_request_observation", rejected)
    needs_review = runtime._write_payment_request_observation((first, second))
    assert needs_review["status"] == "NEEDS_REVIEW"
    assert needs_review["rejection_categories"] == {"GRAND_TOTAL": 2}


def test_payment_request_refresh_reads_the_exact_dws_source_without_waiting_for_raw_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The live view stays independent from historical raw-archive progress."""

    import daily_funds.runtime as runtime_module

    runtime = DailyFundsRuntime(_config(tmp_path))
    moment = datetime(2026, 8, 26, 1, tzinfo=UTC)
    message = {"fixture": "exact-source-message", "createTime": "2026-08-26T01:00:00Z"}
    payload = b"\x89PNG\r\n\x1a\nrefresh"
    downloaded = DownloadedAttachment(
        message=message,
        message_id="refresh-message",
        message_id_hash="c" * 64,
        message_at=moment,
        index=0,
        filename="refresh.png",
        family=None,
        payload=payload,
        sha256=sha256(payload).hexdigest(),
        mime="image/png",
    )
    windows: list[tuple[datetime, datetime]] = []

    class ExactSourceClient:
        def collect_group_history_v2(self, start: datetime, end: datetime) -> DwsPage:
            windows.append((start, end))
            return DwsPage(messages=(message,), next_cursor=None, has_more=False)

        @staticmethod
        def selected_messages(_page: DwsPage):
            return ()

        @staticmethod
        def quarantine_messages(_page: DwsPage):
            return (message,)

        @staticmethod
        def message_id_hash(_message: dict[str, object]) -> str:
            return "c" * 64

        @staticmethod
        def attachment_count(_message: dict[str, object]) -> int:
            return 1

        @staticmethod
        def download(_message: dict[str, object], index: int) -> DownloadedAttachment:
            assert index == 0
            return downloaded

    monkeypatch.setattr(runtime, "_dws_client", ExactSourceClient)
    monkeypatch.setattr(runtime_module, "GitSparseWriter", lambda *_args, **_kwargs: pytest.fail("live snapshot must not wait for raw archive"))
    received: list[tuple[DownloadedAttachment, ...]] = []

    def write_observation(attachments):
        received.append(tuple(attachments))
        return {"status": "VERIFIED", "points": [{"business_date": "2026-08-25"}]}

    monkeypatch.setattr(runtime, "_write_payment_request_observation", write_observation)
    result = runtime.payment_request_refresh(now=moment)

    assert result == {"ok": True, "code": "PAYMENT_REQUEST_REFRESH_VERIFIED"}
    assert received == [(downloaded,)]
    assert windows == [(moment - timedelta(days=31), moment)]


def test_payment_request_refresh_clears_stale_points_when_the_exact_source_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = DailyFundsRuntime(_config(tmp_path))

    class FailingClient:
        @staticmethod
        def collect_group_history_v2(_start: datetime, _end: datetime) -> DwsPage:
            raise IngestionError("DWS_HISTORY_FAILED")

    monkeypatch.setattr(runtime, "_dws_client", FailingClient)
    result = runtime.payment_request_refresh(now=datetime(2026, 8, 26, 1, tzinfo=UTC))

    assert result == {"ok": False, "code": "PAYMENT_REQUEST_REFRESH_SOURCE_READ_FAILED"}
    projection = json.loads((runtime.config.publication_dir / "payment_request_observation.json").read_text(encoding="utf-8"))
    assert projection["status"] == "NEEDS_REVIEW"
    assert projection["machine_code"] == "PAYMENT_REQUEST_OBSERVATION_REFRESH_UNAVAILABLE"
    assert projection["points"] == []
    assert "DWS_HISTORY_FAILED" not in json.dumps(projection)


def test_payment_request_refresh_reports_attachment_provider_phase_without_provider_detail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = DailyFundsRuntime(_config(tmp_path))
    message = {"fixture": "attachment-failure", "createTime": "2026-08-26T01:00:00Z"}

    class AttachmentFailureClient:
        @staticmethod
        def collect_group_history_v2(_start: datetime, _end: datetime) -> DwsPage:
            return DwsPage(messages=(message,), next_cursor=None, has_more=False)

        @staticmethod
        def selected_messages(_page: DwsPage):
            return (message,)

        @staticmethod
        def quarantine_messages(_page: DwsPage):
            return ()

        @staticmethod
        def message_id_hash(_message: dict[str, object]) -> str:
            return "d" * 64

        @staticmethod
        def attachment_count(_message: dict[str, object]) -> int:
            return 1

        @staticmethod
        def download(_message: dict[str, object], _index: int) -> DownloadedAttachment:
            raise IngestionError("ATTACHMENT_DOWNLOAD_FAILED")

    monkeypatch.setattr(runtime, "_dws_client", AttachmentFailureClient)
    result = runtime.payment_request_refresh(now=datetime(2026, 8, 26, 1, tzinfo=UTC))

    assert result == {"ok": False, "code": "PAYMENT_REQUEST_REFRESH_ATTACHMENT_PROVIDER_FAILED"}
    saved = (runtime.config.publication_dir / "payment_request_observation.json").read_text(encoding="utf-8")
    assert "ATTACHMENT_DOWNLOAD_FAILED" not in saved


def test_payment_request_refresh_keeps_a_newer_verified_report_when_an_older_attachment_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An old provider miss cannot erase a newer parsed finance-group report."""

    import daily_funds.runtime as runtime_module

    runtime = DailyFundsRuntime(replace(_config(tmp_path), ocr_enabled=True))
    older = {"openMessageId": "older", "createTime": "2026-08-24T01:00:00Z"}
    newer = {"openMessageId": "newer", "createTime": "2026-08-25T01:00:00Z"}
    payload = b"\x89PNG\r\n\x1a\nnewer-payment-request"
    downloaded = DownloadedAttachment(
        message=newer,
        message_id="newer",
        message_id_hash="b" * 64,
        message_at=datetime(2026, 8, 25, 1, tzinfo=UTC),
        index=0,
        filename="newer.png",
        family=None,
        payload=payload,
        sha256=sha256(payload).hexdigest(),
        mime="image/png",
    )
    downloads: list[str] = []

    class MixedClient:
        @staticmethod
        def collect_group_history_v2(_start: datetime, _end: datetime) -> DwsPage:
            return DwsPage(messages=(older, newer), next_cursor=None, has_more=False)

        @staticmethod
        def selected_messages(_page: DwsPage):
            return (older, newer)

        @staticmethod
        def quarantine_messages(_page: DwsPage):
            return ()

        @staticmethod
        def message_id_hash(message: dict[str, object]) -> str:
            return "a" * 64 if message is older else "b" * 64

        @staticmethod
        def attachment_count(_message: dict[str, object]) -> int:
            return 1

        @staticmethod
        def download(message: dict[str, object], _index: int) -> DownloadedAttachment:
            downloads.append(str(message["openMessageId"]))
            if message is older:
                raise IngestionError("ATTACHMENT_DOWNLOAD_FAILED")
            return downloaded

    monkeypatch.setattr(runtime, "_dws_client", MixedClient)
    monkeypatch.setattr(runtime_module, "deterministic_ocr_runtime_ready", lambda: True)
    monkeypatch.setattr(
        runtime_module,
        "parse_payment_request_observation",
        lambda **kwargs: SimpleNamespace(
            business_date=kwargs["received_at"].date(),
            date_basis="DOCUMENT_DAY",
            request_total_fen=1,
        ),
    )

    result = runtime.payment_request_refresh(now=datetime(2026, 8, 26, 1, tzinfo=UTC))

    assert result == {"ok": True, "code": "PAYMENT_REQUEST_REFRESH_VERIFIED"}
    projection = json.loads((runtime.config.publication_dir / "payment_request_observation.json").read_text(encoding="utf-8"))
    assert projection["status"] == "VERIFIED"
    assert projection["source_coverage"]["parsed_documents"] == 1
    assert downloads == ["newer"]


def test_payment_request_refresh_blocks_a_newer_attachment_failure_before_stale_data_can_publish(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A later unavailable source remains a hard stop for the live page."""

    import daily_funds.runtime as runtime_module

    runtime = DailyFundsRuntime(replace(_config(tmp_path), ocr_enabled=True))
    older = {"openMessageId": "older", "createTime": "2026-08-24T01:00:00Z"}
    newer = {"openMessageId": "newer", "createTime": "2026-08-25T01:00:00Z"}
    payload = b"\x89PNG\r\n\x1a\nolder-payment-request"
    downloaded = DownloadedAttachment(
        message=older,
        message_id="older",
        message_id_hash="a" * 64,
        message_at=datetime(2026, 8, 24, 1, tzinfo=UTC),
        index=0,
        filename="older.png",
        family=None,
        payload=payload,
        sha256=sha256(payload).hexdigest(),
        mime="image/png",
    )
    downloads: list[str] = []

    class MixedClient:
        @staticmethod
        def collect_group_history_v2(_start: datetime, _end: datetime) -> DwsPage:
            return DwsPage(messages=(older, newer), next_cursor=None, has_more=False)

        @staticmethod
        def selected_messages(_page: DwsPage):
            return (older, newer)

        @staticmethod
        def quarantine_messages(_page: DwsPage):
            return ()

        @staticmethod
        def message_id_hash(message: dict[str, object]) -> str:
            return "a" * 64 if message is older else "b" * 64

        @staticmethod
        def attachment_count(_message: dict[str, object]) -> int:
            return 1

        @staticmethod
        def download(message: dict[str, object], _index: int) -> DownloadedAttachment:
            downloads.append(str(message["openMessageId"]))
            if message is newer:
                raise IngestionError("ATTACHMENT_DOWNLOAD_FAILED")
            return downloaded

    monkeypatch.setattr(runtime, "_dws_client", MixedClient)
    monkeypatch.setattr(runtime_module, "deterministic_ocr_runtime_ready", lambda: True)
    monkeypatch.setattr(
        runtime_module,
        "parse_payment_request_observation",
        lambda **kwargs: SimpleNamespace(
            business_date=kwargs["received_at"].date(),
            date_basis="DOCUMENT_DAY",
            request_total_fen=1,
        ),
    )

    result = runtime.payment_request_refresh(now=datetime(2026, 8, 26, 1, tzinfo=UTC))

    assert result == {"ok": False, "code": "PAYMENT_REQUEST_REFRESH_ATTACHMENT_PROVIDER_FAILED"}
    projection = json.loads((runtime.config.publication_dir / "payment_request_observation.json").read_text(encoding="utf-8"))
    assert projection["status"] == "NEEDS_REVIEW"
    assert projection["points"] == []
    assert downloads == ["newer"]


def test_payment_request_refresh_blocks_a_newer_parse_rejection_before_stale_data_can_publish(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A newer identified report must resolve before an older report is considered."""

    import daily_funds.runtime as runtime_module

    runtime = DailyFundsRuntime(replace(_config(tmp_path), ocr_enabled=True))
    older = {"openMessageId": "older", "createTime": "2026-08-24T01:00:00Z"}
    newer = {"openMessageId": "newer", "createTime": "2026-08-25T01:00:00Z"}

    def attachment(message: dict[str, object], marker: bytes, key: str) -> DownloadedAttachment:
        payload = b"\x89PNG\r\n\x1a\n" + marker
        return DownloadedAttachment(
            message=message,
            message_id=str(message["openMessageId"]),
            message_id_hash=key * 64,
            message_at=datetime.fromisoformat(str(message["createTime"]).replace("Z", "+00:00")),
            index=0,
            filename=f"{message['openMessageId']}.png",
            family=None,
            payload=payload,
            sha256=sha256(payload).hexdigest(),
            mime="image/png",
        )

    downloaded = {
        "older": attachment(older, b"older-payment-request", "a"),
        "newer": attachment(newer, b"newer-payment-request", "b"),
    }
    downloads: list[str] = []

    class MixedClient:
        @staticmethod
        def collect_group_history_v2(_start: datetime, _end: datetime) -> DwsPage:
            return DwsPage(messages=(older, newer), next_cursor=None, has_more=False)

        @staticmethod
        def selected_messages(_page: DwsPage):
            return (older, newer)

        @staticmethod
        def quarantine_messages(_page: DwsPage):
            return ()

        @staticmethod
        def message_id_hash(message: dict[str, object]) -> str:
            return "a" * 64 if message is older else "b" * 64

        @staticmethod
        def attachment_count(_message: dict[str, object]) -> int:
            return 1

        @staticmethod
        def download(message: dict[str, object], _index: int) -> DownloadedAttachment:
            identifier = str(message["openMessageId"])
            downloads.append(identifier)
            return downloaded[identifier]

    def parse(**kwargs):
        if kwargs["received_at"] == downloaded["newer"].message_at:
            raise ParseError("PAYMENT_REQUEST_TOTAL_CONSENSUS_MISSING")
        return SimpleNamespace(
            business_date=kwargs["received_at"].date(),
            date_basis="DOCUMENT_DAY",
            request_total_fen=1,
        )

    monkeypatch.setattr(runtime, "_dws_client", MixedClient)
    monkeypatch.setattr(runtime_module, "deterministic_ocr_runtime_ready", lambda: True)
    monkeypatch.setattr(runtime_module, "parse_payment_request_observation", parse)

    result = runtime.payment_request_refresh(now=datetime(2026, 8, 26, 1, tzinfo=UTC))

    assert result == {"ok": False, "code": "PAYMENT_REQUEST_REFRESH_GRAND_TOTAL_NEEDS_REVIEW"}
    projection = json.loads((runtime.config.publication_dir / "payment_request_observation.json").read_text(encoding="utf-8"))
    assert projection["status"] == "NEEDS_REVIEW"
    assert projection["points"] == []
    assert downloads == ["newer"]


@pytest.mark.parametrize(
    ("projection", "expected_code"),
    (
        ({"machine_code": "PAYMENT_REQUEST_OBSERVATION_OCR_UNAVAILABLE"}, "PAYMENT_REQUEST_REFRESH_OCR_UNAVAILABLE"),
        ({"machine_code": "PAYMENT_REQUEST_OBSERVATION_DUPLICATE_AMBIGUOUS"}, "PAYMENT_REQUEST_REFRESH_DUPLICATE_NEEDS_REVIEW"),
        ({"rejection_categories": {"TITLE_CONFIRMATION": 1}}, "PAYMENT_REQUEST_REFRESH_TITLE_NEEDS_REVIEW"),
        ({"rejection_categories": {"DATE_FIELD": 1}}, "PAYMENT_REQUEST_REFRESH_DATE_NEEDS_REVIEW"),
        ({"rejection_categories": {"GRAND_TOTAL_LABEL": 1}}, "PAYMENT_REQUEST_REFRESH_GRAND_TOTAL_LABEL_NEEDS_REVIEW"),
        ({"rejection_categories": {"GRAND_TOTAL": 1}}, "PAYMENT_REQUEST_REFRESH_GRAND_TOTAL_NEEDS_REVIEW"),
        ({"rejection_categories": {"WORKBOOK_LAYOUT": 1}}, "PAYMENT_REQUEST_REFRESH_WORKBOOK_NEEDS_REVIEW"),
        ({"rejection_categories": {"OCR_FORMAT": 1}}, "PAYMENT_REQUEST_REFRESH_OCR_NEEDS_REVIEW"),
        ({"rejection_categories": {"DATE_FIELD": 1, "GRAND_TOTAL": 1}}, "PAYMENT_REQUEST_REFRESH_NEEDS_REVIEW"),
        ({"rejection_categories": {"OTHER_REVIEW": 1}}, "PAYMENT_REQUEST_REFRESH_NEEDS_REVIEW"),
    ),
)
def test_payment_request_refresh_exposes_one_safe_projection_gate(
    projection: dict[str, object],
    expected_code: str,
) -> None:
    assert DailyFundsRuntime._payment_request_refresh_projection_code(projection) == expected_code


@pytest.mark.parametrize(("internal_code", "expected_code"), (
    ("DWS_ATTACHMENT_PERMISSION_DENIED", "PAYMENT_REQUEST_REFRESH_ATTACHMENT_PERMISSION_DENIED"),
    ("ATTACHMENT_DOWNLOAD_ARGUMENT_INVALID", "PAYMENT_REQUEST_REFRESH_ATTACHMENT_ARGUMENT_INVALID"),
    ("ATTACHMENT_DOWNLOAD_AMBIGUOUS", "PAYMENT_REQUEST_REFRESH_ATTACHMENT_OUTPUT_INVALID"),
    ("ATTACHMENT_DOWNLOAD_FAILED", "PAYMENT_REQUEST_REFRESH_ATTACHMENT_PROVIDER_FAILED"),
    ("ATTACHMENT_DOWNLOAD_READ_FAILED", "PAYMENT_REQUEST_REFRESH_ATTACHMENT_READ_FAILED"),
    ("ATTACHMENT_DOWNLOAD_TRANSPORT_FAILED", "PAYMENT_REQUEST_REFRESH_ATTACHMENT_TRANSPORT_UNAVAILABLE"),
    ("ATTACHMENT_INDEX_INVALID", "PAYMENT_REQUEST_REFRESH_ATTACHMENT_INDEX_INVALID"),
    ("UNSUPPORTED_ATTACHMENT", "PAYMENT_REQUEST_REFRESH_ATTACHMENT_UNSUPPORTED"),
    ("CORRUPT_ATTACHMENT", "PAYMENT_REQUEST_REFRESH_ATTACHMENT_CONTENT_INVALID"),
))
def test_payment_request_refresh_preserves_values_free_attachment_outcome(
    internal_code: str,
    expected_code: str,
) -> None:
    """The schedule receipt retains a safe repair category, not provider text."""

    assert DailyFundsRuntime._payment_request_refresh_failure_code(
        IngestionError(internal_code),
    ) == expected_code


def test_cashflow_observation_admits_explicit_generic_source_labels_to_the_strict_chart_gate(tmp_path: Path) -> None:
    runtime = DailyFundsRuntime(_config(tmp_path))
    moment = datetime(2026, 8, 1, tzinfo=UTC)

    def attachment(family: str, marker: bytes, index: int) -> DownloadedAttachment:
        payload = b"\x89PNG\r\n\x1a\n" + marker
        return DownloadedAttachment(
            message={},
            message_id=f"candidate-{index}",
            message_id_hash=(str(index) * 64)[:64],
            message_at=moment,
            index=0,
            filename=f"candidate-{index}.png",
            family=family,
            payload=payload,
            sha256=sha256(payload).hexdigest(),
            mime="image/png",
        )

    generic = attachment("资金明细", b"generic", 1)
    explicit_flow = attachment("资金流水明细", b"flow", 2)
    unresolved: dict[str, str] = {}

    # ``资金明细`` is an explicitly allowed source family.  Its chart-only
    # admission cannot make it a formal fact: ``_write_cashflow_observation``
    # still runs the independent strict date/bank/inflow/outflow/footer gate.
    assert runtime._cashflow_observation_candidates((generic, explicit_flow), unresolved) == (generic, explicit_flow)

    # A title-less document does not inherit the permissive route.  It must
    # first have a deterministic raw-byte family resolution; otherwise it
    # remains outside both the formal and chart-only paths.
    titleless = replace(generic, family=None)
    assert runtime._cashflow_observation_candidates((titleless,), unresolved) == ()


def test_deterministic_ocr_runtime_requires_all_pdf_tools() -> None:
    def runner(command, **_kwargs):
        if command[0] == "tesseract":
            return SimpleNamespace(returncode=0, stdout="List of available languages (1):\nchi_sim\n", stderr="")
        if command[0] == "pdfinfo":
            raise FileNotFoundError(command[0])
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    assert deterministic_ocr_runtime_ready(runner=runner) is False


@pytest.mark.parametrize(
    ("source_family", "expected_family"),
    ((ACCOUNT_FAMILY, ACCOUNT_FAMILY), ("资金明细", ACCOUNT_FAMILY)),
)
def test_runtime_ocr_needs_two_days_of_layout_calibration_before_supporting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_family: str,
    expected_family: str,
) -> None:
    import daily_funds.runtime as runtime_module

    config = replace(_config(tmp_path), ocr_enabled=True)
    runtime = DailyFundsRuntime(config)
    headers = ["业务日期", "公司", "开户行", "账号", "期初余额", "期末余额", "币种"]

    def attachment(day: str, marker: bytes, index: int) -> DownloadedAttachment:
        payload = b"\x89PNG\r\n\x1a\n" + marker
        moment = datetime.fromisoformat(day + "T00:00:00+00:00")
        return DownloadedAttachment(
            message={},
            message_id="ocr-message-" + str(index),
            message_id_hash=(str(index) * 64)[:64],
            message_at=moment,
            index=0,
            filename=("资金账户明细表_" if source_family == ACCOUNT_FAMILY else "资金明细_") + day.replace("-", "") + ".png",
            family=source_family,
            payload=payload,
            sha256=sha256(payload).hexdigest(),
            mime="image/png",
        )

    attachments = (
        attachment("2026-07-30", b"first", 1),
        attachment("2026-07-31", b"second", 2),
        attachment("2026-08-01", b"third", 3),
    )
    candidates = []
    for item, day in zip(attachments, ("2026-07-30", "2026-07-31", "2026-08-01")):
        values = [day, "甲", "乙", "001", "100.00", "110.00", "CNY"]
        candidates.append(parse_ocr_attachment(
            family=source_family,
            filename=item.filename,
            payload=item.payload,
            source=runtime._source_ref(item),
            mime=item.mime,
            runner=_ocr_runner(_ocr_tsv(headers, values)),
        ))
    iterator = iter(candidates)
    monkeypatch.setattr(runtime_module, "parse_ocr_attachment", lambda **_kwargs: next(iterator))

    with pytest.raises(ParseError, match="OCR_PROFILE_CALIBRATING"):
        runtime._parse((attachments[0],))
    with pytest.raises(ParseError, match="OCR_PROFILE_CALIBRATING"):
        runtime._parse((attachments[1],))
    parsed = runtime._parse((attachments[2],))
    assert len(parsed) == 1
    assert parsed[0].facts.family == expected_family
    with runtime.state.connection() as connection:
        profile_days = connection.execute("SELECT COUNT(*) FROM ocr_profile_observations").fetchone()[0]
        outcomes = connection.execute("SELECT outcome,code FROM capability_evidence ORDER BY observed_at,attachment_sha256").fetchall()
    # Every successful opening is retained as values-free evidence.  The first
    # two distinct dates calibrate the layout; the third is the first one
    # permitted to become a supported parse.
    assert profile_days == 3
    assert sorted(tuple(row) for row in outcomes) == sorted([
        ("NEEDS_REVIEW", "OCR_PROFILE_CALIBRATING"),
        ("NEEDS_REVIEW", "OCR_PROFILE_CALIBRATING"),
        ("SUPPORTED", "PARSER_OPEN_OK"),
    ])


def test_runtime_resolves_unclassified_ocr_only_after_dual_schema_and_calibration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A title-less source needs byte-proven family plus an established layout."""

    import daily_funds.runtime as runtime_module

    runtime = DailyFundsRuntime(replace(_config(tmp_path), ocr_enabled=True))
    headers = ["业务日期", "公司", "开户行", "账号", "期初余额", "期末余额", "币种"]

    def attachment(day: str, marker: bytes, index: int) -> DownloadedAttachment:
        payload = b"\x89PNG\r\n\x1a\n" + marker
        moment = datetime.fromisoformat(day + "T00:00:00+00:00")
        return DownloadedAttachment(
            message={},
            message_id="unclassified-ocr-" + str(index),
            message_id_hash=(str(index) * 64)[:64],
            message_at=moment,
            index=0,
            filename="archive_" + day.replace("-", "") + ".png",
            family=None,
            payload=payload,
            sha256=sha256(payload).hexdigest(),
            mime="image/png",
        )

    attachments = (
        attachment("2026-07-30", b"first", 1),
        attachment("2026-07-31", b"second", 2),
        attachment("2026-08-01", b"third", 3),
    )
    candidates = []
    for item, day in zip(attachments, ("2026-07-30", "2026-07-31", "2026-08-01")):
        candidates.append(parse_ocr_attachment(
            family="资金明细",
            filename=item.filename,
            payload=item.payload,
            source=runtime._source_ref(item),
            mime=item.mime,
            runner=_ocr_runner(_ocr_tsv(headers, [day, "甲", "乙", "001", "100.00", "110.00", "CNY"])),
        ))
    iterator = iter(candidates)
    monkeypatch.setattr(runtime_module, "parse_ocr_attachment", lambda **_kwargs: next(iterator))

    assert runtime._resolved_ambiguous_source_attachments((attachments[0],)) == ()
    assert runtime._resolved_ambiguous_source_attachments((attachments[1],)) == ()
    resolved = runtime._resolved_ambiguous_source_attachments((attachments[2],))

    assert len(resolved) == 1
    assert resolved[0].family == ACCOUNT_FAMILY
    assert resolved[0].sha256 == attachments[2].sha256
    with runtime.state.connection() as connection:
        rows = connection.execute(
            "SELECT family,outcome,code FROM capability_evidence ORDER BY observed_at,attachment_sha256"
        ).fetchall()
    assert sorted(tuple(row) for row in rows) == sorted([
        ("UNCLASSIFIED", "NEEDS_REVIEW", "OCR_PROFILE_CALIBRATING"),
        ("UNCLASSIFIED", "NEEDS_REVIEW", "OCR_PROFILE_CALIBRATING"),
        (ACCOUNT_FAMILY, "SUPPORTED", "PARSER_OPEN_OK"),
    ])


def test_runtime_resolves_unclassified_structured_attachment_only_by_complete_schema(tmp_path: Path) -> None:
    """A missing title cannot hide a byte-proven legacy/table source forever."""

    payload = (
        "业务日期,公司,开户行,账号,期末余额\n"
        "2026-07-30,甲,乙,00123,110.00\n"
    ).encode()
    attachment = DownloadedAttachment(
        message={},
        message_id="unclassified-structured-message",
        message_id_hash="8" * 64,
        message_at=datetime(2026, 7, 30, 8, tzinfo=UTC),
        index=0,
        filename="opaque-export.csv",
        family=None,
        payload=payload,
        sha256=sha256(payload).hexdigest(),
        mime="text/csv",
    )
    runtime = DailyFundsRuntime(_config(tmp_path))

    inspection = runtime._inspect_attachment_capabilities((attachment,))

    assert len(inspection.parsed) == 1
    assert inspection.failures == ()
    assert inspection.parsed[0].facts.family == ACCOUNT_FAMILY
    assert inspection.parsed[0].facts.accounts[0].account == "00123"
    with runtime.state.connection() as connection:
        evidence = connection.execute(
            "SELECT family,outcome,code FROM capability_evidence"
        ).fetchone()
    assert tuple(evidence) == (ACCOUNT_FAMILY, "SUPPORTED", "PARSER_OPEN_OK")


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
    state.replace_capability_scope(
        parser_version=PARSER_VERSION,
        attachments=((digest, ACCOUNT_FAMILY),),
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


def test_capability_projection_excludes_current_parser_receipts_outside_latest_raw_census(tmp_path: Path) -> None:
    state = RuntimeState(tmp_path / "state")
    current = "a" * 64
    stale = "b" * 64
    for digest in (current, stale):
        state.record_capability_evidence(
            attachment_sha256=digest,
            family=ACCOUNT_FAMILY,
            suffix=".png",
            declared_mime="image/png",
            magic="PNG",
            parser_version=PARSER_VERSION,
            outcome="NEEDS_REVIEW",
            code="OCR_GENERIC_FAMILY_UNRESOLVED",
        )
    state.replace_capability_scope(
        parser_version=PARSER_VERSION,
        attachments=((current, ACCOUNT_FAMILY),),
    )
    scoped = state.capability_matrix(parser_version=PARSER_VERSION)
    assert len(scoped) == 1
    assert scoped[0]["count"] == 1
    # The historic same-version row is retained for audit but cannot alter
    # the browser's current-source count.
    assert sum(row["count"] for row in state.capability_matrix()) == 2


def test_page_two_failure_never_advances_cursor(tmp_path: Path) -> None:
    config = _config(tmp_path)
    state = RuntimeState(config.state_dir)
    state.commit_cursor("opaque-resume-cursor")
    responses = [
        {
            "success": True,
            "result": {
                "hasMore": True,
                "nextCursor": "opaque-page-2",
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
        if command[1:4] == ["chat", "message", "search-advanced"]:
            assert command[command.index("--conversation-ids") + 1] == config.group_id
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
    assert state.get_cursor() == "opaque-resume-cursor"
    assert state.get("history_high_water_at") is None


def test_terminal_cursor_is_not_reused_for_the_next_overlap_window(tmp_path: Path) -> None:
    config = _config(tmp_path)
    state = RuntimeState(config.state_dir)
    state.commit_cursor("opaque-resume-cursor")
    cursors: list[str] = []
    responses = [
        {"success": True, "result": {"hasMore": False, "messages": []}},
        {"success": True, "result": {"hasMore": False, "messages": []}},
    ]

    def runner(command, **kwargs):
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": True, "refresh_token_valid": True}), "")
        if command[1:4] == ["chat", "message", "search-advanced"]:
            cursors.append(command[command.index("--cursor") + 1])
            return subprocess.CompletedProcess(command, 0, json.dumps(responses.pop(0)), "")
        raise AssertionError(f"unexpected DWS command: {command}")

    poller = HistoryPoller(state, DwsHistoryClient(config, runner=runner))
    first_now = datetime(2026, 8, 1, 0, 0, tzinfo=UTC)
    poller.poll(now=first_now, persist_page=lambda _page: None, holder="fixture-1")
    poller.poll(now=datetime(2026, 8, 1, 1, 0, tzinfo=UTC), persist_page=lambda _page: None, holder="fixture-2")

    assert cursors == ["opaque-resume-cursor", "0"]
    assert state.get_cursor() is None


def test_legacy_backfill_lease_never_blocks_live_or_new_historical_poll(tmp_path: Path) -> None:
    """A deployment-interrupted legacy lease must not strand the next batch."""

    state = RuntimeState(_config(tmp_path).state_dir)

    class EmptyClient:
        @staticmethod
        def search(_start, _end, _cursor):
            return DwsPage(messages=(), next_cursor=None, has_more=False)

    assert state.acquire_lease("backfill_lock", "historical-holder", ttl_seconds=60)
    try:
        pages = HistoryPoller(state, EmptyClient()).poll(
            now=datetime(2026, 8, 1, tzinfo=UTC),
            persist_page=lambda _page: None,
            holder="live-holder",
            lease_profile="live",
        )
        assert pages == 1
        pages = HistoryPoller(state, EmptyClient()).poll(
            now=datetime(2026, 8, 1, tzinfo=UTC),
            persist_page=lambda _page: None,
            holder="other-historical-holder",
            lease_profile="backfill",
        )
        assert pages == 1
    finally:
        state.release_lease("backfill_lock", "historical-holder")


def test_backfill_process_lock_serializes_a_real_competing_batch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Only a live process, never an abandoned lease, may hold backfill."""

    config = _config(tmp_path)
    holder = DailyFundsRuntime(config)
    contender = DailyFundsRuntime(config)
    monkeypatch.setattr(contender, "poll", lambda **_kwargs: pytest.fail("competing backfill must not poll"))

    with holder._backfill_process_lock():
        result = contender.backfill(now=datetime(2026, 8, 1, 4, tzinfo=UTC), max_days=1)

    assert result == {"ok": False, "completed_days": [], "code": "BACKFILL_LOCK_HELD"}


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
        and row["lease_profile"] == "backfill"
        for row in observed
    )


def test_historical_backfill_coverage_is_values_free_and_never_exposes_cursor(tmp_path: Path) -> None:
    runtime = DailyFundsRuntime(_config(tmp_path))
    runtime.state.put("backfill_next_business_date", "2025-10-05")
    now = datetime(2026, 8, 1, 4, tzinfo=UTC)

    coverage = runtime._historical_backfill_coverage(now=now)

    assert coverage == {
        "state": "IN_PROGRESS",
        "window_days": 360,
        "completed_days": 60,
        "remaining_days": 300,
    }
    runtime._write_flow_state(stage="BACKFILLING")
    flow_text = (runtime.config.publication_dir / "flow_state.json").read_text(encoding="utf-8")
    assert json.loads(flow_text)["historical_backfill"]["window_days"] == 360
    assert "2025-10-05" not in flow_text


def test_backfill_scans_the_exact_360_day_range_without_gaps(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Bounded runs must eventually cover every required historical calendar day."""

    from zoneinfo import ZoneInfo

    runtime = DailyFundsRuntime(_config(tmp_path))
    observed_days: list[date] = []

    def empty_poll(**kwargs):
        observed_days.append(kwargs["start_override"].astimezone(ZoneInfo("Asia/Shanghai")).date())
        return {"ok": True, "pages": 1, "attachments": 0, "empty_window": True}

    monkeypatch.setattr(runtime, "poll", empty_poll)
    now = datetime(2026, 8, 1, 4, tzinfo=UTC)
    runs = [runtime.backfill(now=now, max_days=7) for _ in range(52)]

    first_required = date(2025, 8, 6)
    assert all(run["ok"] is True for run in runs)
    assert runs[-1]["complete"] is True
    assert observed_days == [first_required + timedelta(days=offset) for offset in range(360)]
    assert runtime.state.get("backfill_next_business_date") == "2026-08-01"


def test_backfill_runtime_caps_a_direct_call_at_seven_days(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The scheduler contract cannot be bypassed by a direct runtime caller."""

    runtime = DailyFundsRuntime(_config(tmp_path))
    calls = 0

    def empty_poll(**_kwargs):
        nonlocal calls
        calls += 1
        return {"ok": True, "pages": 1, "attachments": 0, "empty_window": True}

    monkeypatch.setattr(runtime, "poll", empty_poll)
    result = runtime.backfill(now=datetime(2026, 8, 1, 4, tzinfo=UTC), max_days=99)

    assert result["ok"] is True
    assert len(result["completed_days"]) == 7
    assert calls == 7


def test_backfill_failure_keeps_the_failed_day_pending(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed historical day cannot be advanced or silently skipped."""

    runtime = DailyFundsRuntime(_config(tmp_path))
    calls = 0

    def failing_second_poll(**_kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            return {"ok": False, "code": "BACKFILL_TEST_FAILURE"}
        return {"ok": True, "pages": 1, "attachments": 0, "empty_window": True}

    monkeypatch.setattr(runtime, "poll", failing_second_poll)
    result = runtime.backfill(now=datetime(2026, 8, 1, 4, tzinfo=UTC), max_days=7)

    assert result == {
        "ok": False,
        "completed_days": ["2025-08-06"],
        "code": "BACKFILL_TEST_FAILURE",
    }
    assert runtime.state.get("backfill_next_business_date") == "2025-08-07"


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


def test_backfill_records_a_missing_historical_attachment_and_continues(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """One attachment-less source message must not strand later history scans."""

    runtime = DailyFundsRuntime(_config(tmp_path))
    calls = 0

    def source_gap_then_empty(**_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {"ok": False, "code": "SOURCE_ATTACHMENT_MISSING"}
        return {"ok": True, "pages": 1, "attachments": 0, "empty_window": True}

    monkeypatch.setattr(runtime, "poll", source_gap_then_empty)
    result = runtime.backfill(now=datetime(2026, 8, 1, 4, tzinfo=UTC), max_days=2)

    assert result["ok"] is True
    assert result["completed_days"] == ["2025-08-06", "2025-08-07"]
    assert result["source_gap_days"] == ["2025-08-06"]
    assert result["needs_review_days"] == ["2025-08-06"]
    assert result["needs_review_attachments"] == 0
    assert result["empty_days"] == ["2025-08-07"]
    assert result["code"] == "BACKFILLING_NEEDS_REVIEW"
    assert runtime.state.get("backfill_next_business_date") == "2025-08-08"


def test_raw_coverage_repair_archives_only_the_missing_source_occurrence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A completed planner is repaired by identity, never by a fake publication."""

    import daily_funds.runtime as runtime_module

    moment = datetime(2026, 7, 30, 8, tzinfo=UTC)
    existing_payload = b"\x89PNG\r\n\x1a\nexisting-raw-image"
    missing_payload = (
        "业务日期,公司,开户行,账号,期末余额\n"
        "2026-07-30,甲,乙,00123,110.00\n"
    ).encode()
    existing = DownloadedAttachment(
        message={},
        message_id="coverage-message",
        message_id_hash="9" * 64,
        message_at=moment,
        index=0,
        filename="existing.png",
        family=None,
        payload=existing_payload,
        sha256=sha256(existing_payload).hexdigest(),
        mime="image/png",
    )
    missing = DownloadedAttachment(
        message={},
        message_id="coverage-message",
        message_id_hash="9" * 64,
        message_at=moment,
        index=1,
        filename="opaque-export.csv",
        family=None,
        payload=missing_payload,
        sha256=sha256(missing_payload).hexdigest(),
        mime="text/csv",
    )
    source_message = {"fixture": "coverage-repair"}
    persisted: list[tuple[DownloadedAttachment, ...]] = []

    class CoverageClient:
        @staticmethod
        def collect_group_history_v2(_start, _end):
            return DwsPage(messages=(source_message,), next_cursor=None, has_more=False)

        @staticmethod
        def selected_messages(_page):
            return ()

        @staticmethod
        def quarantine_messages(_page):
            return (source_message,)

        @staticmethod
        def message_id_hash(_message):
            return missing.message_id_hash

        @staticmethod
        def attachment_count(_message):
            return 2

        @staticmethod
        def download(_message, index):
            assert index == 1
            return missing

    class CoverageWriter:
        def __init__(self, _config):
            self.persisted = False

        def audit_raw_archive(self, *, on_attachment):
            attachments = (existing, missing) if self.persisted else (existing,)
            for attachment in attachments:
                on_attachment(attachment)
            return RawArchiveAudit("a" * 40, (), len(attachments), 1, len(attachments))

        def persist(self, attachments):
            received = tuple(attachments)
            assert received == (missing,)
            persisted.append(received)
            self.persisted = True
            return GitCommit("a" * 40, SimpleNamespace(), received)

    runtime = DailyFundsRuntime(_config(tmp_path))
    monkeypatch.setattr(runtime, "_dws_client", lambda: CoverageClient())
    monkeypatch.setattr(runtime_module, "GitSparseWriter", CoverageWriter)
    monkeypatch.setattr(runtime, "_coordinator", lambda: pytest.fail("coverage repair must not publish"))

    result = runtime.raw_coverage_repair(now=datetime(2026, 8, 1, tzinfo=UTC))

    assert result == {
        "ok": True,
        "code": "RAW_COVERAGE_REPAIRED",
        "source_occurrences": 2,
        "recovered_occurrences": 1,
        "capability_supported": 1,
        "capability_needs_review": 0,
    }
    assert persisted == [(missing,)]
    assert not (runtime.config.publication_dir / "current.json").exists()
    with runtime.state.connection() as connection:
        evidence = connection.execute("SELECT family,outcome,code FROM capability_evidence").fetchone()
        inbox = connection.execute("SELECT state FROM inbox").fetchone()
    assert tuple(evidence) == (ACCOUNT_FAMILY, "SUPPORTED", "PARSER_OPEN_OK")
    assert tuple(inbox) == ("ARCHIVED_CAPABILITY_RECORDED",)
    receipt = json.loads(runtime.state.get("raw_coverage_360d_receipt") or "{}")
    assert receipt == {
        "raw_archive_occurrences": 2,
        "raw_commit_sha": "a" * 40,
        "schema_version": "kmfa.daily_funds.raw_coverage_receipt.v1",
        "source_occurrences": 2,
        "verified_occurrences": 2,
        "window_days": 360,
    }


def test_raw_fact_replay_requires_a_fresh_coverage_receipt(tmp_path: Path) -> None:
    runtime = DailyFundsRuntime(_config(tmp_path))

    assert runtime.raw_fact_replay(now=datetime(2026, 8, 1, tzinfo=UTC)) == {
        "ok": False,
        "code": "RAW_COVERAGE_RECEIPT_REQUIRED",
    }
    assert not (runtime.config.publication_dir / "current.json").exists()


def test_raw_coverage_repair_persists_available_occurrences_and_keeps_failed_downloads_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One unavailable media object must not discard byte-proven siblings."""

    import daily_funds.runtime as runtime_module

    moment = datetime(2026, 7, 30, 8, tzinfo=UTC)

    def attachment(index: int, payload: bytes) -> DownloadedAttachment:
        return DownloadedAttachment(
            message={},
            message_id="coverage-partial",
            message_id_hash="c" * 64,
            message_at=moment,
            index=index,
            filename=f"fixture-{index}.csv",
            family=None,
            payload=payload,
            sha256=sha256(payload).hexdigest(),
            mime="text/csv",
        )

    existing = attachment(0, "业务日期,公司,开户行,账号,期末余额\n2026-07-30,甲,乙,001,100.00\n".encode())
    available = attachment(1, "业务日期,公司,开户行,账号,期末余额\n2026-07-30,甲,乙,002,100.00\n".encode())
    unavailable = attachment(2, b"unavailable-fixture")
    source_message = {"fixture": "coverage-partial"}
    attempts = 0

    class PartialClient:
        @staticmethod
        def collect_group_history_v2(_start, _end):
            return DwsPage(messages=(source_message,), next_cursor=None, has_more=False)

        @staticmethod
        def selected_messages(_page):
            return ()

        @staticmethod
        def quarantine_messages(_page):
            return (source_message,)

        @staticmethod
        def message_id_hash(_message):
            return "c" * 64

        @staticmethod
        def attachment_count(_message):
            return 3

        @staticmethod
        def download(_message, index):
            nonlocal attempts
            if index == 1:
                return available
            assert index == 2
            attempts += 1
            raise IngestionError("ATTACHMENT_DOWNLOAD_FAILED")

    class PartialWriter:
        def __init__(self, _config):
            self.persisted = False

        def audit_raw_archive(self, *, on_attachment):
            attachments = (existing, available) if self.persisted else (existing,)
            for item in attachments:
                on_attachment(item)
            return RawArchiveAudit("c" * 40, (), len(attachments), 1, len(attachments))

        def persist(self, attachments):
            received = tuple(attachments)
            assert received == (available,)
            self.persisted = True
            return GitCommit("c" * 40, SimpleNamespace(), received)

    runtime = DailyFundsRuntime(_config(tmp_path))
    monkeypatch.setattr(runtime, "_dws_client", lambda: PartialClient())
    monkeypatch.setattr(runtime_module, "GitSparseWriter", PartialWriter)
    monkeypatch.setattr(runtime, "_coordinator", lambda: pytest.fail("partial coverage must not publish"))

    result = runtime.raw_coverage_repair(now=datetime(2026, 8, 1, tzinfo=UTC))

    assert result == {
        "ok": False,
        "code": "RAW_COVERAGE_REPAIR_INCOMPLETE",
        "source_occurrences": 3,
        "recovered_occurrences": 1,
        "remaining_occurrences": 1,
        "download_failures": 1,
        "capability_supported": 1,
        "capability_needs_review": 0,
    }
    assert attempts == 2
    assert runtime._raw_coverage_receipt() is None
    assert not (runtime.config.publication_dir / "current.json").exists()


def test_raw_fact_replay_reopens_exact_pair_before_publishing_latest_day(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An exact KMFile link may admit title-less bytes to the re-opened pair gate."""

    import daily_funds.runtime as runtime_module

    moment = datetime(2026, 7, 30, 8, tzinfo=UTC)
    account_payload = (
        "业务日期,公司,开户行,账号,期初余额,期末余额\n"
        "2026-07-30,甲,乙,001,100.00,110.00\n"
    ).encode()
    transaction_payload = (
        "业务日期,公司,开户行,账号,流水号,流入,流出\n"
        "2026-07-30,甲,乙,001,t-1,10.00,\n"
    ).encode()
    account = DownloadedAttachment(
        message={
            "openMessageId": "replay-account",
            "attachments": [{"fileId": "registered-account-file"}],
        },
        message_id="replay-account",
        message_id_hash="a" * 64,
        message_at=moment,
        index=0,
        filename="opaque-account.csv",
        family=None,
        payload=account_payload,
        sha256=sha256(account_payload).hexdigest(),
        mime="text/csv",
    )
    transaction = DownloadedAttachment(
        message={
            "openMessageId": "replay-transaction",
            "attachments": [{"fileId": "registered-transaction-file"}],
        },
        message_id="replay-transaction",
        message_id_hash="b" * 64,
        message_at=moment,
        index=0,
        filename="opaque-transaction.csv",
        family=None,
        payload=transaction_payload,
        sha256=sha256(transaction_payload).hexdigest(),
        mime="text/csv",
    )
    attachments = (account, transaction)
    reopened: list[tuple[PersistedRawAttachment, ...]] = []
    publication_calls: list[dict[str, object]] = []

    class ReplayWriter:
        def __init__(self, _config):
            return None

        @staticmethod
        def kmfile_registered_attachment_keys():
            return frozenset({
                ("replay-account", "registered-account-file"),
                ("replay-transaction", "registered-transaction-file"),
            })

        def audit_raw_archive_metadata(self, *, on_attachment, commit_sha):
            assert commit_sha == "a" * 40
            for attachment in attachments:
                on_attachment(PersistedRawAttachment(
                    message=attachment.message,
                    message_id=attachment.message_id,
                    message_id_hash=attachment.message_id_hash,
                    message_at=attachment.message_at,
                    index=attachment.index,
                    sha256=attachment.sha256,
                ))
            return RawArchiveAudit("a" * 40, (), 2, 1, 2)

        def reopen_persisted(self, received, *, commit_sha):
            assert commit_sha == "a" * 40
            rows = tuple(received)
            reopened.append(rows)
            assert {row.sha256 for row in rows} == {account.sha256, transaction.sha256}
            return GitCommit(
                "a" * 40,
                ReopenedRawEvidence(("raw/batches/fixture.json",), tuple(sorted({account.sha256, transaction.sha256})), 2),
                attachments,
            )

        @staticmethod
        def persist_publication(_publication):
            return "f" * 40

        @staticmethod
        def bundle_head():
            return b"fixture-bundle"

    class FakeR2:
        @staticmethod
        def mirror(_attachments, *, git_commit_sha):
            assert git_commit_sha == "a" * 40
            return ("fixture-manifest", b"fixture")

    class FakeCoordinator:
        r2 = FakeR2()

        @staticmethod
        def publish(**kwargs):
            publication_calls.append(kwargs)
            assert kwargs["report"].valid
            assert kwargs["advance_pointer"] is True
            assert kwargs["private_publication_sink"]({"publication_id": "f" * 64}) == "f" * 40
            assert kwargs["git_bundle_sink"]() == b"fixture-bundle"
            return SimpleNamespace(
                publication={"publication_id": "f" * 64},
                oci_backup_state="OK",
            )

    runtime = DailyFundsRuntime(_config(tmp_path))
    runtime._record_raw_coverage_receipt(
        raw_commit_sha="a" * 40,
        source_occurrences=2,
        verified_occurrences=2,
        raw_archive_occurrences=2,
    )
    monkeypatch.setattr(runtime_module, "GitSparseWriter", ReplayWriter)
    monkeypatch.setattr(runtime_module.R2FreeTierGuard, "require_fresh_receipt", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(runtime, "_coordinator", lambda: FakeCoordinator())

    result = runtime.raw_fact_replay(now=datetime(2026, 8, 1, tzinfo=UTC))

    assert result == {
        "ok": True,
        "code": "RAW_FACT_REPLAY_PUBLISHED",
        "source_occurrences": 2,
        "parser_open_occurrences": 2,
        "needs_review_occurrences": 0,
        "published_days": 1,
        "incomplete_days": 0,
        "ambiguous_days": 0,
    }
    assert len(reopened) == 2
    assert len(publication_calls) == 1
    history = json.loads((runtime.config.publication_dir / "history.json").read_text(encoding="utf-8"))
    assert history["days"]["2026-07-30"]["publication_id"] == "f" * 64


def test_raw_fact_replay_keeps_quarantined_titleless_bytes_out_of_formal_pairing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raw preservation is not an implicit document-family admission."""

    import daily_funds.runtime as runtime_module

    moment = datetime(2026, 7, 30, 8, tzinfo=UTC)
    account_payload = (
        "业务日期,公司,开户行,账号,期初余额,期末余额\n"
        "2026-07-30,甲,乙,001,100.00,110.00\n"
    ).encode()
    transaction_payload = (
        "业务日期,公司,开户行,账号,流水号,流入,流出\n"
        "2026-07-30,甲,乙,001,t-1,10.00,\n"
    ).encode()

    def attachment(index: int, payload: bytes) -> DownloadedAttachment:
        return DownloadedAttachment(
            message={},
            message_id=f"quarantined-{index}",
            message_id_hash=("a" if index == 0 else "b") * 64,
            message_at=moment,
            index=0,
            filename=f"opaque-{index}.csv",
            family=None,
            payload=payload,
            sha256=sha256(payload).hexdigest(),
            mime="text/csv",
        )

    attachments = (attachment(0, account_payload), attachment(1, transaction_payload))

    class ReplayWriter:
        def __init__(self, _config):
            return None

        @staticmethod
        def kmfile_registered_attachment_keys():
            return frozenset()

        def audit_raw_archive_metadata(self, *, on_attachment, commit_sha):
            assert commit_sha == "a" * 40
            for item in attachments:
                on_attachment(PersistedRawAttachment(
                    message={"title": None},
                    message_id=item.message_id,
                    message_id_hash=item.message_id_hash,
                    message_at=item.message_at,
                    index=item.index,
                    sha256=item.sha256,
                ))
            return RawArchiveAudit("a" * 40, (), 2, 1, 2)

    runtime = DailyFundsRuntime(_config(tmp_path))
    runtime._record_raw_coverage_receipt(
        raw_commit_sha="a" * 40,
        source_occurrences=2,
        verified_occurrences=2,
        raw_archive_occurrences=2,
    )
    monkeypatch.setattr(runtime_module, "GitSparseWriter", ReplayWriter)
    monkeypatch.setattr(runtime, "_coordinator", lambda: pytest.fail("quarantined inputs must not publish"))

    assert runtime.raw_fact_replay(now=datetime(2026, 8, 1, tzinfo=UTC)) == {
        "ok": False,
        "code": "RAW_FACT_REPLAY_NO_COMPLETE_PAIR",
        "source_occurrences": 2,
        "parser_open_occurrences": 0,
        "needs_review_occurrences": 0,
        "incomplete_days": 0,
        "ambiguous_days": 0,
    }


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
        def quarantine_messages(_page):
            return ()

        @staticmethod
        def attachment_count(_message):
            return 1

        @staticmethod
        def message_id_hash(_message):
            return attachment.message_id_hash

        @staticmethod
        def reopen_candidate(_message, _index, _attachment_sha256):
            # This fixture exercises the normal first-download path.
            return None

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


def test_archive_only_backfill_quarantines_unclassified_source_without_creating_facts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Unknown titles are preserved as raw evidence, never guessed into facts."""

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
    payload = b"\x89PNG\r\n\x1a\nsynthetic-unclassified-image"
    moment = datetime(2026, 7, 30, 8, tzinfo=UTC)
    attachment = DownloadedAttachment(
        message={},
        message_id="synthetic-unclassified-message",
        message_id_hash="5" * 64,
        message_at=moment,
        index=0,
        filename="unclassified.png",
        family=None,
        payload=payload,
        sha256=sha256(payload).hexdigest(),
        mime="image/png",
    )
    message = {"fixture": "unclassified"}

    class QuarantineClient:
        @staticmethod
        def search(_start, _end, _cursor):
            return DwsPage(messages=(message,), next_cursor=None, has_more=False)

        @staticmethod
        def selected_messages(_page):
            return ()

        @staticmethod
        def quarantine_messages(_page):
            return (message,)

        @staticmethod
        def attachment_count(_message):
            return 1

        @staticmethod
        def message_id_hash(_message):
            return attachment.message_id_hash

        @staticmethod
        def reopen_candidate(_message, _index, _attachment_sha256):
            return None

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
            return GitCommit("e" * 40, SimpleNamespace(), reopened)

    runtime = DailyFundsRuntime(config)
    monkeypatch.setattr(runtime, "_dws_client", lambda: QuarantineClient())
    monkeypatch.setattr(runtime_module, "GitSparseWriter", ReadbackWriter)
    monkeypatch.setattr(runtime, "_coordinator", lambda: pytest.fail("quarantine archive must not construct a publication coordinator"))

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
        capability = connection.execute("SELECT family,outcome,code FROM capability_evidence").fetchone()
    assert tuple(capability) == ("UNCLASSIFIED", "NEEDS_REVIEW", "UNSUPPORTED_ATTACHMENT")


def test_live_poll_archives_quarantine_but_never_sends_it_to_publication(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A title-less attachment may enrich raw evidence but cannot become money."""

    import daily_funds.runtime as runtime_module

    payload = b"\x89PNG\r\n\x1a\nlive-unclassified-image"
    attachment = DownloadedAttachment(
        message={},
        message_id="live-unclassified-message",
        message_id_hash="6" * 64,
        message_at=datetime(2026, 8, 1, 8, tzinfo=UTC),
        index=0,
        filename="unclassified.png",
        family=None,
        payload=payload,
        sha256=sha256(payload).hexdigest(),
        mime="image/png",
    )
    message = {"fixture": "live-unclassified"}

    class QuarantineClient:
        @staticmethod
        def search(_start, _end, _cursor):
            return DwsPage(messages=(message,), next_cursor=None, has_more=False)

        @staticmethod
        def selected_messages(_page):
            return ()

        @staticmethod
        def quarantine_messages(_page):
            return (message,)

        @staticmethod
        def attachment_count(_message):
            return 1

        @staticmethod
        def message_id_hash(_message):
            return attachment.message_id_hash

        @staticmethod
        def reopen_candidate(_message, _index, _attachment_sha256):
            return None

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
            return GitCommit("f" * 40, SimpleNamespace(), reopened)

    runtime = DailyFundsRuntime(_config(tmp_path))
    monkeypatch.setattr(runtime, "_dws_client", lambda: QuarantineClient())
    monkeypatch.setattr(runtime_module, "GitSparseWriter", ReadbackWriter)
    monkeypatch.setattr(runtime, "_coordinator", lambda: pytest.fail("quarantine must not reach publication"))

    assert runtime.poll(now=datetime(2026, 8, 1, tzinfo=UTC)) == {
        "ok": False,
        "code": "SOURCE_MATCH_ZERO",
    }
    assert persisted == [(attachment,)]
    assert not (runtime.config.publication_dir / "current.json").exists()
    flow = json.loads((runtime.config.publication_dir / "flow_state.json").read_text(encoding="utf-8"))
    assert flow["source_discovery"] == {"state": "TARGET_DOCUMENT_NOT_FOUND"}


def test_live_poll_uses_only_byte_proven_unclassified_candidate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A resolved unknown enters the normal mirror/parse gates, never facts directly."""

    import daily_funds.runtime as runtime_module

    payload = b"\x89PNG\r\n\x1a\nstrict-unclassified-image"
    attachment = DownloadedAttachment(
        message={},
        message_id="resolved-unclassified-message",
        message_id_hash="7" * 64,
        message_at=datetime(2026, 8, 1, 8, tzinfo=UTC),
        index=0,
        filename="archive_20260801.png",
        family=None,
        payload=payload,
        sha256=sha256(payload).hexdigest(),
        mime="image/png",
    )
    resolved = replace(attachment, family=ACCOUNT_FAMILY)
    message = {"fixture": "resolved-unclassified"}

    class QuarantineClient:
        @staticmethod
        def search(_start, _end, _cursor):
            return DwsPage(messages=(message,), next_cursor=None, has_more=False)

        @staticmethod
        def selected_messages(_page):
            return ()

        @staticmethod
        def quarantine_messages(_page):
            return (message,)

        @staticmethod
        def attachment_count(_message):
            return 1

        @staticmethod
        def message_id_hash(_message):
            return attachment.message_id_hash

        @staticmethod
        def reopen_candidate(_message, _index, _attachment_sha256):
            return None

        @staticmethod
        def download(_message, _index):
            return attachment

    class ReadbackWriter:
        def __init__(self, _config):
            pass

        @staticmethod
        def persist(attachments):
            reopened = tuple(attachments)
            return GitCommit("a" * 40, SimpleNamespace(), reopened)

    mirrored: list[tuple[DownloadedAttachment, ...]] = []

    class FakeR2:
        @staticmethod
        def mirror(attachments, *, git_commit_sha):
            assert git_commit_sha == "a" * 40
            mirrored.append(tuple(attachments))
            return SimpleNamespace()

    runtime = DailyFundsRuntime(_config(tmp_path))
    monkeypatch.setattr(runtime, "_dws_client", lambda: QuarantineClient())
    monkeypatch.setattr(runtime_module, "GitSparseWriter", ReadbackWriter)
    monkeypatch.setattr(runtime, "_resolved_ambiguous_source_attachments", lambda _attachments: (resolved,))
    monkeypatch.setattr(runtime_module.R2FreeTierGuard, "require_fresh_receipt", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(runtime, "_coordinator", lambda: SimpleNamespace(r2=FakeR2()))
    parsed_inputs: list[tuple[DownloadedAttachment, ...]] = []
    monkeypatch.setattr(runtime, "_parse", lambda attachments: parsed_inputs.append(tuple(attachments)) or [])

    assert runtime.poll(now=datetime(2026, 8, 1, tzinfo=UTC)) == {
        "ok": False,
        "code": "SOURCE_MATCH_ZERO",
    }
    assert mirrored == [(resolved,)]
    assert parsed_inputs == [(resolved,)]
    assert not (runtime.config.publication_dir / "current.json").exists()


def test_live_poll_keeps_unresolved_generic_document_out_of_financial_candidates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A generic title preserves raw evidence but cannot reach R2 or publication."""

    import daily_funds.runtime as runtime_module

    payload = b"\x89PNG\r\n\x1a\nunresolved-generic-image"
    attachment = DownloadedAttachment(
        message={},
        message_id="generic-message",
        message_id_hash="6" * 64,
        message_at=datetime(2026, 8, 1, 8, tzinfo=UTC),
        index=0,
        filename="资金明细_20260801.png",
        family="资金明细",
        payload=payload,
        sha256=sha256(payload).hexdigest(),
        mime="image/png",
    )
    message = {"fixture": "generic"}

    class GenericClient:
        @staticmethod
        def search(_start, _end, _cursor):
            return DwsPage(messages=(message,), next_cursor=None, has_more=False)

        @staticmethod
        def selected_messages(_page):
            return (message,)

        @staticmethod
        def quarantine_messages(_page):
            return ()

        @staticmethod
        def attachment_count(_message):
            return 1

        @staticmethod
        def message_id_hash(_message):
            return attachment.message_id_hash

        @staticmethod
        def reopen_candidate(_message, _index, _attachment_sha256):
            return None

        @staticmethod
        def download(_message, _index):
            return attachment

    class ReadbackWriter:
        def __init__(self, _config):
            pass

        @staticmethod
        def persist(attachments):
            return GitCommit("a" * 40, SimpleNamespace(), tuple(attachments))

    runtime = DailyFundsRuntime(_config(tmp_path))
    monkeypatch.setattr(runtime, "_dws_client", lambda: GenericClient())
    monkeypatch.setattr(runtime_module, "GitSparseWriter", ReadbackWriter)
    monkeypatch.setattr(runtime, "_resolved_ambiguous_source_attachments", lambda _attachments: ())
    monkeypatch.setattr(
        runtime_module.R2FreeTierGuard,
        "require_fresh_receipt",
        lambda *_args, **_kwargs: pytest.fail("unresolved generic source must not reach R2"),
    )

    assert runtime.poll(now=datetime(2026, 8, 1, tzinfo=UTC)) == {
        "ok": False,
        "code": "SOURCE_MATCH_ZERO",
    }
    flow = json.loads((runtime.config.publication_dir / "flow_state.json").read_text(encoding="utf-8"))
    assert flow["source_discovery"] == {"state": "GENERIC_DOCUMENT_UNRESOLVED"}
    assert not (runtime.config.publication_dir / "current.json").exists()


def test_overlap_reopens_verified_raw_without_repeating_media_download(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A 30-minute overlap must reopen immutable raw evidence, never guess."""

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
    payload = b"\x89PNG\r\n\x1a\nsynthetic-overlap-image"
    attachment = DownloadedAttachment(
        message={"fixture": "overlap"},
        message_id="overlap-message",
        message_id_hash=sha256(b"overlap-message").hexdigest(),
        message_at=datetime(2026, 7, 30, 8, tzinfo=UTC),
        index=0,
        filename="资金明细_20260730.png",
        family="资金明细",
        payload=payload,
        sha256=sha256(payload).hexdigest(),
        mime="image/png",
    )
    second_payload = b"\x89PNG\r\n\x1a\nsynthetic-overlap-image-two"
    second_attachment = DownloadedAttachment(
        message={"fixture": "overlap-two"},
        message_id="overlap-message-two",
        message_id_hash=sha256(b"overlap-message-two").hexdigest(),
        message_at=attachment.message_at,
        index=0,
        filename="资金明细_20260730_2.png",
        family="资金明细",
        payload=second_payload,
        sha256=sha256(second_payload).hexdigest(),
        mime="image/png",
    )
    attachments_by_message = {
        attachment.message["fixture"]: attachment,
        second_attachment.message["fixture"]: second_attachment,
    }
    messages = tuple(item.message for item in (attachment, second_attachment))

    class CachedClient:
        @staticmethod
        def search(_start, _end, _cursor):
            return DwsPage(messages=messages, next_cursor=None, has_more=False)

        @staticmethod
        def selected_messages(_page):
            return messages

        @staticmethod
        def quarantine_messages(_page):
            return ()

        @staticmethod
        def attachment_count(_message):
            return 1

        @staticmethod
        def message_id_hash(message):
            return attachments_by_message[message["fixture"]].message_id_hash

        @staticmethod
        def reopen_candidate(message, _index, attachment_sha256):
            raw = attachments_by_message[message["fixture"]]
            assert attachment_sha256 == raw.sha256
            return PersistedRawAttachment(
                message=raw.message,
                message_id=raw.message_id,
                message_id_hash=raw.message_id_hash,
                message_at=raw.message_at,
                index=raw.index,
                sha256=raw.sha256,
            )

        @staticmethod
        def download(_message, _index):
            pytest.fail("a verified overlap must not repeat DWS media download")

    reopened: list[tuple[PersistedRawAttachment, ...]] = []

    class ReadbackWriter:
        def __init__(self, _config):
            pass

        def reopen_persisted(self, attachments):
            candidates = tuple(attachments)
            reopened.append(candidates)
            assert candidates == tuple(
                PersistedRawAttachment(
                    message=raw.message,
                    message_id=raw.message_id,
                    message_id_hash=raw.message_id_hash,
                    message_at=raw.message_at,
                    index=raw.index,
                    sha256=raw.sha256,
                )
                for raw in (attachment, second_attachment)
            )
            return GitCommit("b" * 40, SimpleNamespace(), (attachment, second_attachment))

        def persist(self, _attachments):
            pytest.fail("verified overlap must not create a second raw write")

    runtime = DailyFundsRuntime(config)
    for raw in (attachment, second_attachment):
        assert runtime.state.note_inbox(
            f"{raw.message_id_hash}:{raw.index}:{raw.sha256}",
            raw.message_id_hash,
            raw.sha256,
            "GIT_PERSISTED",
        )
    monkeypatch.setattr(runtime, "_dws_client", lambda: CachedClient())
    monkeypatch.setattr(runtime_module, "GitSparseWriter", ReadbackWriter)
    monkeypatch.setattr(runtime, "_coordinator", lambda: pytest.fail("archive-only must not publish"))

    result = runtime.poll(
        now=datetime(2026, 8, 1, tzinfo=UTC),
        start_override=datetime(2026, 7, 30, tzinfo=UTC),
        advance_pointer=False,
        allow_empty_window=True,
        archive_only=True,
    )

    assert result["ok"] is True
    assert result["attachments"] == 2
    assert len(reopened) == 1


def test_restart_after_raw_persist_reopens_the_exact_durable_attachment_without_redownload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """F-015: an interrupted batch resumes from immutable raw evidence only.

    The first runtime is interrupted immediately after the private-Git writer
    returns.  A fresh runtime object must reuse that durable ``GIT_PERSISTED``
    receipt, never fetch the expired DWS media again and never create a second
    raw write.  The fixture remains archive-only, so this proves recovery and
    idempotency without manufacturing a money publication.
    """

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
    payload = b"\x89PNG\r\n\x1a\nsynthetic-restart-raw"
    attachment = DownloadedAttachment(
        message={"fixture": "restart"},
        message_id="restart-message",
        message_id_hash=sha256(b"restart-message").hexdigest(),
        message_at=datetime(2026, 7, 30, 8, tzinfo=UTC),
        index=0,
        filename="资金明细_20260730.png",
        family="资金明细",
        payload=payload,
        sha256=sha256(payload).hexdigest(),
        mime="image/png",
    )

    class FirstClient:
        @staticmethod
        def search(_start, _end, _cursor):
            return DwsPage(messages=(attachment.message,), next_cursor=None, has_more=False)

        @staticmethod
        def selected_messages(_page):
            return (attachment.message,)

        @staticmethod
        def quarantine_messages(_page):
            return ()

        @staticmethod
        def attachment_count(_message):
            return 1

        @staticmethod
        def message_id_hash(_message):
            return attachment.message_id_hash

        @staticmethod
        def reopen_candidate(_message, _index, _attachment_sha256):
            return None

        @staticmethod
        def download(_message, _index):
            return attachment

    initial_writes: list[tuple[DownloadedAttachment, ...]] = []

    class FirstWriter:
        def __init__(self, _config):
            pass

        def persist(self, attachments):
            staged = tuple(attachments)
            initial_writes.append(staged)
            return GitCommit("a" * 40, SimpleNamespace(), staged)

    first_runtime = DailyFundsRuntime(config)
    monkeypatch.setattr(first_runtime, "_dws_client", lambda: FirstClient())
    monkeypatch.setattr(runtime_module, "GitSparseWriter", FirstWriter)
    monkeypatch.setattr(
        first_runtime,
        "_inspect_attachment_capabilities",
        lambda _attachments: (_ for _ in ()).throw(KeyboardInterrupt()),
    )

    with pytest.raises(KeyboardInterrupt):
        first_runtime.poll(
            now=datetime(2026, 8, 1, tzinfo=UTC),
            start_override=datetime(2026, 7, 30, tzinfo=UTC),
            advance_pointer=False,
            allow_empty_window=True,
            archive_only=True,
        )

    occurrence_key = f"{attachment.message_id_hash}:{attachment.index}:{attachment.sha256}"
    with first_runtime.state.connection() as connection:
        assert tuple(connection.execute("SELECT state FROM inbox WHERE occurrence_key=?", (occurrence_key,)).fetchone()) == (
            "GIT_PERSISTED",
        )
    assert initial_writes == [(attachment,)]

    class RestartedClient(FirstClient):
        @staticmethod
        def reopen_candidate(_message, _index, attachment_sha256):
            assert attachment_sha256 == attachment.sha256
            return PersistedRawAttachment(
                message=attachment.message,
                message_id=attachment.message_id,
                message_id_hash=attachment.message_id_hash,
                message_at=attachment.message_at,
                index=attachment.index,
                sha256=attachment.sha256,
            )

        @staticmethod
        def download(_message, _index):
            pytest.fail("restart recovery must not redownload an already persisted attachment")

    reopened: list[tuple[PersistedRawAttachment, ...]] = []

    class RestartWriter:
        def __init__(self, _config):
            pass

        def persist(self, _attachments):
            pytest.fail("restart recovery must not create a second raw write")

        def reopen_persisted(self, attachments):
            cached = tuple(attachments)
            reopened.append(cached)
            return GitCommit("b" * 40, SimpleNamespace(), (attachment,))

    restarted_runtime = DailyFundsRuntime(config)
    monkeypatch.setattr(restarted_runtime, "_dws_client", lambda: RestartedClient())
    monkeypatch.setattr(runtime_module, "GitSparseWriter", RestartWriter)
    result = restarted_runtime.poll(
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
    assert len(reopened) == 1
    assert len(reopened[0]) == 1
    assert reopened[0][0].sha256 == attachment.sha256
    with restarted_runtime.state.connection() as connection:
        assert tuple(connection.execute("SELECT state FROM inbox WHERE occurrence_key=?", (occurrence_key,)).fetchone()) == (
            "ARCHIVED_CAPABILITY_RECORDED",
        )
    assert not (config.publication_dir / "current.json").exists()


def test_raw_archive_audit_records_only_readback_capability_and_never_publishes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T04's cloud job consumes a fresh private-Git audit, not DWS bytes."""

    import daily_funds.runtime as runtime_module

    config = _config(tmp_path)
    moment = datetime(2026, 7, 30, 8, tzinfo=UTC)
    payload = (
        "业务日期,公司,开户行,账号,期初余额,期末余额,币种\n"
        "2026-07-30,甲公司,甲银行,001,1500000.00,1570000.00,CNY\n"
    ).encode()
    message_id = "raw-archive-account"
    attachment = DownloadedAttachment(
        message={
            "openConversationId": "group-fixture",
            "senderOpenDingTalkId": "sender-fixture",
            "openMessageId": message_id,
            "createTime": moment.isoformat(),
            "content": "资金账户明细表 mediaId=fixture-raw-archive",
        },
        message_id=message_id,
        message_id_hash=sha256(message_id.encode()).hexdigest(),
        message_at=moment,
        index=0,
        filename="资金账户明细表_20260730.csv",
        family=ACCOUNT_FAMILY,
        payload=payload,
        sha256=sha256(payload).hexdigest(),
        mime="text/csv",
    )
    calls: list[str] = []

    class ArchiveWriter:
        def __init__(self, _config):
            calls.append("init")

        def audit_raw_archive(self, *, on_attachment=None):
            calls.append("audit")
            result = RawArchiveAudit(
                commit_sha="a" * 40,
                verified_attachments=(attachment,),
                occurrence_count=1,
                batch_count=1,
                batch_occurrence_references=1,
            )
            if on_attachment is not None:
                on_attachment(attachment)
            return result

    runtime = DailyFundsRuntime(config)
    monkeypatch.setattr(runtime_module, "GitSparseWriter", ArchiveWriter)
    monkeypatch.setattr(runtime, "_dws_client", lambda: pytest.fail("raw archive audit must not call DWS"))
    raw_capability_inspect = runtime._inspect_attachment_capabilities

    def capability_before_cashflow(attachments):
        calls.append("capability")
        return raw_capability_inspect(attachments)

    monkeypatch.setattr(runtime, "_inspect_attachment_capabilities", capability_before_cashflow)

    # A full OCR census can run longer than one 15-minute collection window.
    # It reads a commit-pinned snapshot and must therefore not occupy the
    # single-writer Git lease used by the live/backfill persistence path.
    assert runtime.state.acquire_lease("git_writer_lock", "live-writer", ttl_seconds=13 * 60)
    result = runtime.raw_archive_audit()

    assert result == {
        "ok": True,
        "code": "RAW_ARCHIVE_AUDITED",
        "capability_supported": 1,
        "capability_needs_review": 0,
    }
    assert calls == ["init", "audit", "capability"]
    assert not (config.publication_dir / "current.json").exists()
    with runtime.state.connection() as connection:
        inbox = connection.execute("SELECT state FROM inbox").fetchone()
        capability = connection.execute("SELECT outcome,code FROM capability_evidence").fetchone()
        scope = connection.execute("SELECT attachment_sha256,family,parser_version FROM capability_scope").fetchone()
    assert tuple(inbox) == ("ARCHIVED_CAPABILITY_RECORDED",)
    assert tuple(capability) == ("SUPPORTED", "PARSER_OPEN_OK")
    assert tuple(scope) == (attachment.sha256, ACCOUNT_FAMILY, PARSER_VERSION)
    flow = json.loads((config.publication_dir / "flow_state.json").read_text(encoding="utf-8"))
    assert flow["business_flow"]["stage"] == "RAW_ARCHIVE_AUDITED"
    assert flow["source_discovery"] == {"state": "UNKNOWN"}
    assert "raw-archive-account" not in json.dumps(flow, ensure_ascii=False)


def test_raw_archive_metadata_audit_censuses_authority_without_opening_historic_payloads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recovery may verify all source identities before replaying exact facts."""

    import daily_funds.runtime as runtime_module

    config = _config(tmp_path)
    calls: list[str] = []

    class ArchiveWriter:
        def __init__(self, _config):
            calls.append("init")

        def audit_raw_archive_metadata(self):
            calls.append("metadata")
            return RawArchiveAudit(
                commit_sha="a" * 40,
                verified_attachments=(),
                occurrence_count=2,
                batch_count=1,
                batch_occurrence_references=2,
            )

    runtime = DailyFundsRuntime(config)
    monkeypatch.setattr(runtime_module, "GitSparseWriter", ArchiveWriter)
    monkeypatch.setattr(
        runtime,
        "_inspect_attachment_capabilities",
        lambda _attachments: pytest.fail("metadata audit must not OCR historic payloads"),
    )

    assert runtime.raw_archive_metadata_audit() == {
        "ok": True,
        "code": "RAW_ARCHIVE_AUDITED",
    }
    assert calls == ["init", "metadata"]
    assert not (config.publication_dir / "current.json").exists()
    with runtime.state.connection() as connection:
        assert connection.execute("SELECT count(*) FROM capability_evidence").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM capability_scope").fetchone()[0] == 0
    flow = json.loads((config.publication_dir / "flow_state.json").read_text(encoding="utf-8"))
    assert flow["business_flow"]["stage"] == "RAW_ARCHIVE_METADATA_AUDITED"


def test_raw_archive_audit_reuses_only_same_version_receipts_after_fresh_raw_census(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A chart-only parser change must not OCR an unchanged formal census twice."""

    import daily_funds.runtime as runtime_module

    config = _config(tmp_path)
    moment = datetime(2026, 7, 30, 8, tzinfo=UTC)

    def attachment(marker: str) -> DownloadedAttachment:
        payload = (
            "业务日期,公司,开户行,账号,期初余额,期末余额,币种\n"
            f"2026-07-30,甲公司,甲银行,{marker},1500000.00,1570000.00,CNY\n"
        ).encode()
        message_id = f"raw-archive-{marker}"
        return DownloadedAttachment(
            message={
                "openConversationId": "group-fixture",
                "senderOpenDingTalkId": "sender-fixture",
                "openMessageId": message_id,
                "createTime": moment.isoformat(),
                "content": "资金账户明细表 mediaId=fixture-raw-archive",
            },
            message_id=message_id,
            message_id_hash=sha256(message_id.encode()).hexdigest(),
            message_at=moment,
            index=0,
            filename=f"资金账户明细表_{marker}.csv",
            family=ACCOUNT_FAMILY,
            payload=payload,
            sha256=sha256(payload).hexdigest(),
            mime="text/csv",
        )

    cached = attachment("001")
    fresh = attachment("002")

    class ArchiveWriter:
        def __init__(self, _config):
            pass

        def audit_raw_archive(self, *, on_attachment=None):
            # This is the mandatory fresh private-Git census.  The optimization
            # is allowed only after it returns both verified byte strings.
            result = RawArchiveAudit(
                commit_sha="a" * 40,
                verified_attachments=(cached, fresh),
                occurrence_count=2,
                batch_count=1,
                batch_occurrence_references=2,
            )
            if on_attachment is not None:
                on_attachment(cached)
                on_attachment(fresh)
            return result

    runtime = DailyFundsRuntime(config)
    runtime.state.record_parser_evidence(
        attachment_sha256=cached.sha256,
        family=ACCOUNT_FAMILY,
        suffix=".csv",
        declared_mime="text/csv",
        magic="TEXT",
        parser_version=PARSER_VERSION,
    )
    runtime.state.record_capability_evidence(
        attachment_sha256=cached.sha256,
        family=ACCOUNT_FAMILY,
        suffix=".csv",
        declared_mime="text/csv",
        magic="TEXT",
        parser_version=PARSER_VERSION,
        outcome="SUPPORTED",
        code="PARSER_OPEN_OK",
    )
    runtime.state.replace_capability_scope(
        parser_version=PARSER_VERSION,
        attachments=((cached.sha256, ACCOUNT_FAMILY),),
    )
    inspected: list[str] = []
    original_inspect = runtime._inspect_attachment_capabilities

    def inspect_only_unscoped(attachments):
        materialized = tuple(attachments)
        inspected.extend(item.sha256 for item in materialized)
        return original_inspect(materialized)

    monkeypatch.setattr(runtime_module, "GitSparseWriter", ArchiveWriter)
    monkeypatch.setattr(runtime, "_inspect_attachment_capabilities", inspect_only_unscoped)

    result = runtime.raw_archive_audit()

    assert inspected == [fresh.sha256]
    assert result == {
        "ok": True,
        "code": "RAW_ARCHIVE_AUDITED",
        "capability_supported": 2,
        "capability_needs_review": 0,
    }
    with runtime.state.connection() as connection:
        scope_count = connection.execute(
            "SELECT COUNT(*) FROM capability_scope WHERE parser_version=?",
            (PARSER_VERSION,),
        ).fetchone()[0]
    assert scope_count == 2


def test_capability_scope_does_not_reuse_an_orphaned_success_receipt(tmp_path: Path) -> None:
    state = RuntimeState(tmp_path / "state")
    digest = "a" * 64
    state.record_capability_evidence(
        attachment_sha256=digest,
        family=ACCOUNT_FAMILY,
        suffix=".csv",
        declared_mime="text/csv",
        magic="TEXT",
        parser_version=PARSER_VERSION,
        outcome="SUPPORTED",
        code="PARSER_OPEN_OK",
    )
    state.replace_capability_scope(
        parser_version=PARSER_VERSION,
        attachments=((digest, ACCOUNT_FAMILY),),
    )

    # A capability result without the matching exact-version parser evidence
    # cannot suppress another parser run.
    assert state.reusable_capability_scope_receipts(
        parser_version=PARSER_VERSION,
        attachment_sha256s=(digest,),
    ) == {}


def test_startup_raw_archive_audit_gate_requires_a_complete_current_parser_scope(tmp_path: Path) -> None:
    config = _config(tmp_path)
    state = RuntimeState(config.state_dir)
    digest = "a" * 64

    assert raw_archive_audit_required(config) is True

    state.record_capability_evidence(
        attachment_sha256=digest,
        family=ACCOUNT_FAMILY,
        suffix=".csv",
        declared_mime="text/csv",
        magic="TEXT",
        parser_version=PARSER_VERSION,
        outcome="SUPPORTED",
        code="PARSER_OPEN_OK",
    )
    state.replace_capability_scope(
        parser_version=PARSER_VERSION,
        attachments=((digest, ACCOUNT_FAMILY),),
    )

    # A supported scope without its parser-open receipt remains incomplete.
    assert raw_archive_audit_required(config) is True

    state.record_parser_evidence(
        attachment_sha256=digest,
        family=ACCOUNT_FAMILY,
        suffix=".csv",
        declared_mime="text/csv",
        magic="TEXT",
        parser_version=PARSER_VERSION,
    )

    assert state.has_complete_capability_scope(parser_version=PARSER_VERSION) is True
    assert raw_archive_audit_required(config) is False


def test_startup_raw_archive_audit_gate_defers_to_a_live_recovery_request(tmp_path: Path) -> None:
    config = _config(tmp_path)
    now = datetime.now(UTC).replace(microsecond=0)

    atomic_json_write(config.control_dir / REQUEST_FILE, {
        "schema_version": REQUEST_SCHEMA,
        "request_id": "b" * 64,
        "action": "RECOVER",
        "actor": ACTOR,
        "requested_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(seconds=RECOVERY_MAX_SECONDS)).isoformat().replace("+00:00", "Z"),
    })
    assert raw_archive_audit_required(config) is False

    requested_at = now - timedelta(hours=1)
    atomic_json_write(config.control_dir / REQUEST_FILE, {
        "schema_version": REQUEST_SCHEMA,
        "request_id": "c" * 64,
        "action": "RECOVER",
        "actor": ACTOR,
        "requested_at": requested_at.isoformat().replace("+00:00", "Z"),
        "expires_at": (now - timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
    })
    assert raw_archive_audit_required(config) is True


@pytest.mark.parametrize(("internal_code", "expected_code"), (
    ("SOURCE_MISSING", "RAW_ARCHIVE_AUDIT_SOURCE_MISSING"),
    ("GIT_AUDIT_TRANSPORT_RETRYABLE", "RAW_ARCHIVE_AUDIT_TRANSPORT_UNAVAILABLE"),
    ("RAW_ARCHIVE_CENSUS_LIMIT_EXCEEDED", "RAW_ARCHIVE_AUDIT_CENSUS_LIMIT"),
    ("GIT_READBACK_FAILED", "RAW_ARCHIVE_AUDIT_INTEGRITY_NEEDS_REVIEW"),
    ("GIT_SPARSE_SCOPE_VIOLATION", "RAW_ARCHIVE_AUDIT_INTEGRITY_NEEDS_REVIEW"),
    ("RAW_PATH_HASH_COLLISION", "RAW_ARCHIVE_AUDIT_NEEDS_REVIEW"),
))
def test_raw_archive_audit_projects_safe_failure_classes_without_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    internal_code: str,
    expected_code: str,
) -> None:
    """A raw failure keeps exact evidence private and blocks every receipt."""

    import daily_funds.runtime as runtime_module

    config = _config(tmp_path)

    class MissingArchiveWriter:
        def __init__(self, _config):
            pass

        def audit_raw_archive(self, *, on_attachment=None):
            raise IngestionError(internal_code)

    runtime = DailyFundsRuntime(config)
    monkeypatch.setattr(runtime_module, "GitSparseWriter", MissingArchiveWriter)

    assert runtime.raw_archive_audit() == {
        "ok": False,
        "code": expected_code,
    }
    assert not (config.publication_dir / "current.json").exists()
    with runtime.state.connection() as connection:
        assert connection.execute("SELECT count(*) FROM parser_evidence").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM capability_evidence").fetchone()[0] == 0


@pytest.mark.parametrize(("internal_code", "expected_code"), (
    ("RAW_ARCHIVE_METADATA_TREE_CENSUS_NEEDS_REVIEW", "RAW_ARCHIVE_AUDIT_TREE_CENSUS_NEEDS_REVIEW"),
    ("RAW_ARCHIVE_METADATA_CHECKOUT_NEEDS_REVIEW", "RAW_ARCHIVE_AUDIT_CHECKOUT_NEEDS_REVIEW"),
    ("RAW_ARCHIVE_METADATA_OCCURRENCE_METADATA_NEEDS_REVIEW", "RAW_ARCHIVE_AUDIT_OCCURRENCE_METADATA_NEEDS_REVIEW"),
    ("RAW_ARCHIVE_METADATA_SOURCE_ENVELOPE_NEEDS_REVIEW", "RAW_ARCHIVE_AUDIT_SOURCE_ENVELOPE_NEEDS_REVIEW"),
    ("RAW_ARCHIVE_METADATA_BATCH_BINDING_NEEDS_REVIEW", "RAW_ARCHIVE_AUDIT_BATCH_BINDING_NEEDS_REVIEW"),
))
def test_raw_archive_metadata_audit_projects_fixed_stage_without_private_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    internal_code: str,
    expected_code: str,
) -> None:
    """Metadata recovery surfaces only its fixed repair stage."""

    import daily_funds.runtime as runtime_module

    class ArchiveWriter:
        def __init__(self, _config):
            return None

        def audit_raw_archive_metadata(self):
            raise IngestionError(internal_code)

    runtime = DailyFundsRuntime(_config(tmp_path))
    monkeypatch.setattr(runtime_module, "GitSparseWriter", ArchiveWriter)

    assert runtime.raw_archive_metadata_audit() == {
        "ok": False,
        "code": expected_code,
    }
    assert not (runtime.config.publication_dir / "current.json").exists()


def test_raw_archive_audit_process_lock_prevents_an_expired_lease_from_starting_a_second_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The process lock outlives the bounded Git-writer lease."""

    import daily_funds.runtime as runtime_module

    config = _config(tmp_path)
    first_runtime = DailyFundsRuntime(config)
    second_runtime = DailyFundsRuntime(config)
    writer_calls: list[str] = []

    class ArchiveWriter:
        def __init__(self, _config):
            writer_calls.append("init")

        def audit_raw_archive(self, *, on_attachment=None):
            pytest.fail("a competing audit must not begin a second raw readback")

    monkeypatch.setattr(runtime_module, "GitSparseWriter", ArchiveWriter)

    with first_runtime._raw_archive_audit_process_lock():
        result = second_runtime.raw_archive_audit()

    assert result["human_status"] == "处理中"
    assert result["machine_code"] == "RAW_ARCHIVE_AUDIT_LOCK_HELD"

    assert writer_calls == []


def test_raw_archive_audit_marks_unparseable_readback_needs_review_without_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A real readback that lacks a deterministic parser is not a money pass."""

    import daily_funds.runtime as runtime_module

    config = _config(tmp_path)
    payload = b"synthetic-unparseable-raw-attachment"
    message_id = "raw-archive-needs-review"
    attachment = DownloadedAttachment(
        message={
            "openConversationId": "group-fixture",
            "senderOpenDingTalkId": "sender-fixture",
            "openMessageId": message_id,
            "createTime": "2026-07-30T08:00:00+00:00",
            "content": "fixture",
        },
        message_id=message_id,
        message_id_hash=sha256(message_id.encode()).hexdigest(),
        message_at=datetime(2026, 7, 30, 8, tzinfo=UTC),
        index=0,
        filename="fixture.bin",
        family=ACCOUNT_FAMILY,
        payload=payload,
        sha256=sha256(payload).hexdigest(),
        mime="application/octet-stream",
    )

    class ArchiveWriter:
        def __init__(self, _config):
            pass

        def audit_raw_archive(self, *, on_attachment=None):
            result = RawArchiveAudit(
                commit_sha="a" * 40,
                verified_attachments=(attachment,),
                occurrence_count=1,
                batch_count=1,
                batch_occurrence_references=1,
            )
            if on_attachment is not None:
                on_attachment(attachment)
            return result

    runtime = DailyFundsRuntime(config)
    monkeypatch.setattr(runtime_module, "GitSparseWriter", ArchiveWriter)

    assert runtime.raw_archive_audit() == {
        "ok": True,
        "code": "RAW_ARCHIVE_AUDIT_NEEDS_REVIEW",
        "capability_supported": 0,
        "capability_needs_review": 1,
    }
    assert not (config.publication_dir / "current.json").exists()
    with runtime.state.connection() as connection:
        assert connection.execute("SELECT count(*) FROM parser_evidence").fetchone()[0] == 0
        assert tuple(connection.execute("SELECT outcome,code FROM capability_evidence").fetchone()) == (
            "NEEDS_REVIEW",
            "UNSUPPORTED_ATTACHMENT",
        )
    flow = json.loads((config.publication_dir / "flow_state.json").read_text(encoding="utf-8"))
    assert flow["business_flow"]["stage"] == "RAW_ARCHIVE_AUDIT_NEEDS_REVIEW"


def test_raw_archive_audit_rejects_readback_payload_hash_mismatch_without_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A tampered raw object cannot be downgraded to a capability review."""

    import daily_funds.runtime as runtime_module

    config = _config(tmp_path)
    payload = (
        "业务日期,公司,开户行,账号,期初余额,期末余额,币种\n"
        "2026-07-30,甲公司,甲银行,001,1500000.00,1570000.00,CNY\n"
    ).encode()
    message_id = "raw-archive-integrity-failure"
    attachment = DownloadedAttachment(
        message={
            "openConversationId": "group-fixture",
            "senderOpenDingTalkId": "sender-fixture",
            "openMessageId": message_id,
            "createTime": "2026-07-30T08:00:00+00:00",
            "content": "fixture",
        },
        message_id=message_id,
        message_id_hash=sha256(message_id.encode()).hexdigest(),
        message_at=datetime(2026, 7, 30, 8, tzinfo=UTC),
        index=0,
        filename="资金账户明细表_20260730.csv",
        family=ACCOUNT_FAMILY,
        payload=payload,
        sha256="a" * 64,
        mime="text/csv",
    )

    class ArchiveWriter:
        def __init__(self, _config):
            pass

        def audit_raw_archive(self, *, on_attachment=None):
            result = RawArchiveAudit(
                commit_sha="a" * 40,
                verified_attachments=(attachment,),
                occurrence_count=1,
                batch_count=1,
                batch_occurrence_references=1,
            )
            if on_attachment is not None:
                on_attachment(attachment)
            return result

    runtime = DailyFundsRuntime(config)
    monkeypatch.setattr(runtime_module, "GitSparseWriter", ArchiveWriter)

    assert runtime.raw_archive_audit() == {
        "ok": False,
        "code": "RAW_ARCHIVE_AUDIT_INTEGRITY_NEEDS_REVIEW",
    }
    assert not (config.publication_dir / "current.json").exists()
    with runtime.state.connection() as connection:
        assert connection.execute("SELECT count(*) FROM parser_evidence").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM capability_evidence").fetchone()[0] == 0
    flow = json.loads((config.publication_dir / "flow_state.json").read_text(encoding="utf-8"))
    assert flow["business_flow"]["stage"] == "RAW_ARCHIVE_AUDIT_NEEDS_REVIEW"


def test_runtime_state_reuses_only_one_terminal_raw_receipt(tmp_path: Path) -> None:
    state = RuntimeState(tmp_path / "state")
    message_id_hash = "a" * 64
    attachment_sha256 = "b" * 64
    occurrence_key = f"{message_id_hash}:0:{attachment_sha256}"

    assert state.reusable_raw_attachment_sha(message_id_hash, 0) is None
    assert state.note_inbox(occurrence_key, message_id_hash, attachment_sha256, "PENDING")
    assert state.reusable_raw_attachment_sha(message_id_hash, 0) is None
    state.mark_inbox(occurrence_key, "GIT_PERSISTED")
    assert state.reusable_raw_attachment_sha(message_id_hash, 0) == attachment_sha256
    assert state.reusable_raw_attachment_sha(message_id_hash, True) is None

    conflicting_sha256 = "c" * 64
    assert state.note_inbox(
        f"{message_id_hash}:0:{conflicting_sha256}",
        message_id_hash,
        conflicting_sha256,
        "VALID_PUBLISHED",
    )
    assert state.reusable_raw_attachment_sha(message_id_hash, 0) is None


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

        @staticmethod
        def quarantine_messages(_page):
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

        @staticmethod
        def quarantine_messages(_page):
            return ()

    runtime = DailyFundsRuntime(_config(tmp_path))
    monkeypatch.setattr(runtime, "_dws_client", lambda: NonTargetClient())

    assert runtime.poll(now=datetime(2026, 8, 1, tzinfo=UTC))["code"] == "SOURCE_MATCH_ZERO"
    flow_text = (runtime.config.publication_dir / "flow_state.json").read_text(encoding="utf-8")
    assert json.loads(flow_text)["source_discovery"] == {"state": "TARGET_DOCUMENT_NOT_FOUND"}
    assert "message-fixture" not in flow_text


def test_live_poll_dws_auth_failure_retains_prior_publication(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """F-001: source authentication failure must never replace a valid pointer."""

    class AuthDeniedClient:
        @staticmethod
        def search(_start, _end, _cursor):
            raise IngestionError("DWS_AUTH_REQUIRED")

    runtime = DailyFundsRuntime(_config(tmp_path))
    pointer = runtime.config.publication_dir / "current.json"
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(json.dumps({
        "publication": {
            "status": "VALID",
            "publication_id": "a" * 64,
            "business_date": "2026-07-30",
            "created_at": "2026-07-30T12:00:00Z",
            "oci_backup_state": "OK",
        },
    }, sort_keys=True) + "\n", encoding="utf-8")
    before = pointer.read_bytes()
    monkeypatch.setattr(runtime, "_dws_client", lambda: AuthDeniedClient())

    assert runtime.poll(now=datetime(2026, 8, 1, tzinfo=UTC)) == {
        "ok": False,
        "code": "DWS_AUTH_REQUIRED",
    }
    assert pointer.read_bytes() == before
    status = json.loads((runtime.config.publication_dir / "status.json").read_text(encoding="utf-8"))
    assert status["human_status"] == "需处理"
    assert status["machine_code"] == "DWS_AUTH_REQUIRED"


def test_live_poll_raw_readback_failure_retains_prior_publication(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """F-005/F-008: a corrupt raw readback stops before a pointer swap."""

    import daily_funds.runtime as runtime_module

    class OneAttachmentClient:
        @staticmethod
        def search(_start, _end, _cursor):
            return DwsPage(messages=({"opaque": "message-fixture"},), next_cursor=None, has_more=False)

        @staticmethod
        def selected_messages(page):
            return page.messages

        @staticmethod
        def quarantine_messages(_page):
            return ()

        @staticmethod
        def attachment_count(_message):
            return 1

        @staticmethod
        def message_id_hash(_message):
            return "b" * 64

        @staticmethod
        def download(_message, _index):
            payload = b"fixture-attachment"
            return DownloadedAttachment(
                message={},
                message_id="fixture-message",
                message_id_hash="b" * 64,
                message_at=datetime(2026, 7, 30, tzinfo=UTC),
                index=0,
                filename="资金账户明细表_20260730.csv",
                family=ACCOUNT_FAMILY,
                payload=payload,
                sha256=sha256(payload).hexdigest(),
                mime="text/csv",
            )

    class ReadbackFailureWriter:
        def __init__(self, _config):
            pass

        @staticmethod
        def persist(_attachments):
            raise IngestionError("GIT_READBACK_FAILED")

    runtime = DailyFundsRuntime(_config(tmp_path))
    pointer = runtime.config.publication_dir / "current.json"
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(json.dumps({
        "publication": {
            "status": "VALID",
            "publication_id": "c" * 64,
            "business_date": "2026-07-30",
            "created_at": "2026-07-30T12:00:00Z",
            "oci_backup_state": "OK",
        },
    }, sort_keys=True) + "\n", encoding="utf-8")
    before = pointer.read_bytes()
    monkeypatch.setattr(runtime, "_dws_client", lambda: OneAttachmentClient())
    monkeypatch.setattr(runtime_module, "GitSparseWriter", ReadbackFailureWriter)

    assert runtime.poll(now=datetime(2026, 8, 1, tzinfo=UTC)) == {
        "ok": False,
        "code": "GIT_READBACK_FAILED",
    }
    assert pointer.read_bytes() == before
    flow_text = (runtime.config.publication_dir / "flow_state.json").read_text(encoding="utf-8")
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


def test_raw_coverage_and_fact_replay_expose_git_writer_contention_as_processing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A live raw writer is not a false source or reconciliation failure."""

    coverage = DailyFundsRuntime(_config(tmp_path / "coverage"))
    monkeypatch.setattr(
        coverage,
        "_raw_coverage_repair_locked",
        lambda **_kwargs: (_ for _ in ()).throw(IngestionError("GIT_WRITER_LOCK_HELD")),
    )
    coverage_status = coverage.raw_coverage_repair(now=datetime(2026, 8, 1, tzinfo=UTC))
    assert coverage_status["human_status"] == "处理中"
    assert coverage_status["machine_code"] == "RAW_COVERAGE_REPAIR_GIT_WRITER_LOCK_HELD"

    replay = DailyFundsRuntime(_config(tmp_path / "replay"))
    monkeypatch.setattr(
        replay,
        "_raw_fact_replay_locked",
        lambda **_kwargs: (_ for _ in ()).throw(IngestionError("GIT_WRITER_LOCK_HELD")),
    )
    replay_status = replay.raw_fact_replay(now=datetime(2026, 8, 1, tzinfo=UTC))
    assert replay_status["human_status"] == "处理中"
    assert replay_status["machine_code"] == "RAW_FACT_REPLAY_GIT_WRITER_LOCK_HELD"


def test_auth_incident_dedup_honors_the_frozen_six_hour_cooldown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import daily_funds.state as state_module

    state = RuntimeState(_config(tmp_path).state_dir)
    first = datetime(2026, 8, 1, tzinfo=UTC)
    monkeypatch.setattr(state_module, "utc_now", lambda: first)
    assert state.queue_incident("DWS_AUTH_REQUIRED") is True
    assert state.queue_incident("DWS_AUTH_REQUIRED") is False
    monkeypatch.setattr(state_module, "utc_now", lambda: first + timedelta(minutes=361))
    assert state.queue_incident("DWS_AUTH_REQUIRED") is True


def test_cloud_scheduler_uses_the_bundled_entrypoint_and_nonblocking_backfill_cadence() -> None:
    """Cron must use the isolated, owner-only Coolify env snapshot."""

    command = "/opt/daily-funds/scripts/run_daily_funds.py"
    wrapper = "/opt/daily-funds/scripts/run_cron_job.sh"
    cron = (ROOT / "crontab.txt").read_text(encoding="utf-8")
    assert f"*/15 * * * * root {wrapper} poll" in cron
    assert f"2,17,32,47 * * * * root {wrapper} payment-request-refresh" in cron
    assert f"* * * * * root {wrapper} auth-probe" in cron
    assert f"0 * * * * root {wrapper} keepalive" in cron
    assert f"5,20,35,50 * * * * root {wrapper} backfill --max-days 7" in cron
    assert "15 2 * * * root" not in cron
    assert f"30 3 * * * root {wrapper} observer" in cron
    assert f"0 */6 * * * root {wrapper} r2-guard" in cron
    assert f"10 4 * * * root {wrapper} cold-backup" in cron
    assert f"20 5 * * * root {wrapper} raw-archive-audit" in cron
    assert f"45 5 * * * root {wrapper} runtime-audit" in cron
    assert f"0 5 1 * * root {wrapper} restore-drill" in cron
    entrypoint = (ROOT / "entrypoint.sh").read_text(encoding="utf-8")
    assert '[ "$(date +%z)" != "+0800" ]' in entrypoint
    assert 'keys = ["TZ"]' in entrypoint
    assert "CRON_ENV_FILE=\"$STATE_DIR/cron.env\"" in entrypoint
    assert "chmod 0600 \"$CRON_ENV_FILE\"" in entrypoint
    assert "run_auth_broker.py >/dev/null 2>&1" in entrypoint
    assert "AUTH_BROKER_PID" in entrypoint
    assert "run_history_probe_broker.py >/dev/null 2>&1" in entrypoint
    assert "HISTORY_PROBE_BROKER_PID" in entrypoint
    assert 'CRON_LOG="/var/log/daily-funds/cron.log"' in entrypoint
    assert 'tail -n 0 -F "$CRON_LOG" &' in entrypoint
    assert "run_daily_funds.py payment-request-refresh >> \"$CRON_LOG\" 2>&1" in entrypoint
    assert "PAYMENT_REQUEST_REFRESH_PID" in entrypoint
    assert "STARTUP_RAW_ARCHIVE_RETRY_DELAY_SECONDS=800" in entrypoint
    assert "startup_raw_archive_audit_required.py >/dev/null 2>&1" in entrypoint
    assert "run_daily_funds.py raw-archive-audit >> \"$CRON_LOG\" 2>&1" in entrypoint
    assert 'if [ "$RAW_ARCHIVE_AUDIT_RC" -eq 75 ]; then' in entrypoint
    assert 'sleep "$STARTUP_RAW_ARCHIVE_RETRY_DELAY_SECONDS"' in entrypoint
    assert "RAW_ARCHIVE_AUDIT_PID" in entrypoint
    assert "RAW_ARCHIVE_AUDIT_CHILD_PID" in entrypoint
    assert "run_startup_raw_archive_audit()" in entrypoint
    assert "stop_startup_raw_archive_audit_child()" in entrypoint
    assert 'trap stop_startup_raw_archive_audit_child INT TERM' in entrypoint
    assert 'kill -TERM "$RAW_ARCHIVE_AUDIT_CHILD_PID"' in entrypoint
    assert "stop_startup_raw_archive_audit()" in entrypoint
    assert 'if [ -n "$RAW_ARCHIVE_AUDIT_PID" ]; then' in entrypoint
    assert "run_auth_broker.py" not in cron
    assert "run_history_probe_broker.py" not in cron
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
    ("raw-archive-audit", "raw_archive_audit", "RAW_ARCHIVE_AUDIT_LOCK_HELD"),
    ("raw-coverage-repair", "raw_coverage_repair", "RAW_COVERAGE_REPAIR_LOCK_HELD"),
    ("raw-coverage-repair", "raw_coverage_repair", "RAW_COVERAGE_REPAIR_GIT_WRITER_LOCK_HELD"),
    ("raw-fact-replay", "raw_fact_replay", "RAW_FACT_REPLAY_LOCK_HELD"),
    ("raw-fact-replay", "raw_fact_replay", "RAW_FACT_REPLAY_GIT_WRITER_LOCK_HELD"),
    ("payment-request-refresh", "payment_request_refresh", "PAYMENT_REQUEST_REFRESH_LOCK_HELD"),
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


def test_flow_state_write_lock_prevents_stale_operation_receipt_overwrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Concurrent cron jobs must not resurrect a completed poll as RUNNING."""

    config = _config(tmp_path)
    poll_runtime = DailyFundsRuntime(config)
    auth_runtime = DailyFundsRuntime(config)
    status = poll_runtime.status.write("需处理", "SOURCE_MATCH_ZERO")
    poll_runtime._write_flow_state(stage="POLL_NEEDS_ATTENTION", status=status)
    poll_runtime.record_operation_start(job="poll", code="POLL_RUNNING")

    poll_read_entered = threading.Event()
    release_poll_read = threading.Event()
    auth_read_entered = threading.Event()
    original_poll_read = poll_runtime._read_json_object
    original_auth_read = auth_runtime._read_json_object

    def block_poll_read(path: Path) -> dict[str, object] | None:
        if path.name == "flow_state.json" and not poll_read_entered.is_set():
            poll_read_entered.set()
            assert release_poll_read.wait(timeout=2)
        return original_poll_read(path)

    def track_auth_read(path: Path) -> dict[str, object] | None:
        if path.name == "flow_state.json":
            auth_read_entered.set()
        return original_auth_read(path)

    monkeypatch.setattr(poll_runtime, "_read_json_object", block_poll_read)
    monkeypatch.setattr(auth_runtime, "_read_json_object", track_auth_read)

    poll_thread = threading.Thread(
        target=lambda: poll_runtime.record_operation_receipt(
            job="poll", succeeded=False, code="SOURCE_MATCH_ZERO",
        ),
    )
    auth_thread = threading.Thread(
        target=lambda: auth_runtime.record_operation_receipt(
            job="auth-probe", succeeded=True, code="AUTH_OK",
        ),
    )
    poll_thread.start()
    assert poll_read_entered.wait(timeout=2)
    auth_thread.start()
    assert not auth_read_entered.wait(timeout=0.2)
    release_poll_read.set()
    poll_thread.join(timeout=2)
    auth_thread.join(timeout=2)
    assert not poll_thread.is_alive()
    assert not auth_thread.is_alive()

    flow = json.loads((config.publication_dir / "flow_state.json").read_text(encoding="utf-8"))
    assert flow["operations"]["poll"]["state"] == "FAILED"
    assert flow["operations"]["poll"]["code"] == "SOURCE_MATCH_ZERO"
    assert flow["operations"]["auth-probe"]["state"] == "SUCCEEDED"
    assert flow["operations"]["auth-probe"]["code"] == "AUTH_OK"


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


def test_raw_materializer_reuses_only_a_verified_historic_filename(tmp_path: Path) -> None:
    moment = datetime(2026, 7, 30, 8, tzinfo=UTC)
    message = {"openMessageId": "msg-filename-drift", "createTime": moment.isoformat()}
    payload = b"same-media-bytes"
    original = DownloadedAttachment(
        message, "msg-filename-drift", "d" * 64, moment,
        0, "historic.bin", ACCOUNT_FAMILY, payload,
        __import__("hashlib").sha256(payload).hexdigest(), "image/png",
    )
    staged = RawMaterializer().stage(tmp_path, (original,))
    replay = replace(original, filename="current.png")

    canonical = RawMaterializer.canonicalize_existing_occurrences(tmp_path, (replay,))
    assert canonical == (original,)
    assert RawMaterializer().stage(tmp_path, canonical).batch_id == staged.batch_id

    # A filename is delivery metadata.  Every other occurrence field remains
    # immutable and must still reject a replay that differs from the existing
    # raw authority.
    with pytest.raises(IngestionError, match="RAW_PATH_HASH_COLLISION"):
        RawMaterializer.canonicalize_existing_occurrences(
            tmp_path,
            (replace(replay, mime="image/jpeg"),),
        )
    changed_payload = b"different-media-bytes"
    with pytest.raises(IngestionError, match="RAW_PATH_HASH_COLLISION"):
        RawMaterializer.canonicalize_existing_occurrences(
            tmp_path,
            (replace(
                replay,
                payload=changed_payload,
                sha256=__import__("hashlib").sha256(changed_payload).hexdigest(),
            ),),
        )


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
    assert RawMaterializer.hydrate_readback_attachment(first_root, replace(direct, payload=b"")).payload == direct_payload
    assert RawMaterializer.readback_attachment(first_root, same_name_different_bytes).payload == changed_payload
    assert RawMaterializer.readback_attachment(first_root, oversize).payload == oversize_payload
    RawMaterializer.readback_batch(first_root, (oversize, direct, same_name_different_bytes), first)
    message_path = second_root / "raw/messages/2026/07/30" / f"{direct.message_id_hash}.json"
    message_path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(IngestionError, match="GIT_READBACK_FAILED"):
        RawMaterializer.readback_attachment(second_root, direct)
    with pytest.raises(IngestionError, match="GIT_READBACK_FAILED"):
        RawMaterializer.hydrate_readback_attachment(second_root, replace(direct, payload=b""))
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

    origin_url = origin.as_uri()
    monkeypatch.setattr(config_module, "ALLOWED_PRIVATE_REPOSITORIES", frozenset({origin_url}))
    monkeypatch.setattr(ingestion, "DIRECT_BLOB_MAX_BYTES", 10)
    monkeypatch.setattr(ingestion, "CHUNK_BYTES", 4)
    config = replace(_config(tmp_path), private_repo=origin_url)
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
    assert "Hostname=ssh.github.com" in env["GIT_SSH_COMMAND"]
    assert "Port=443" in env["GIT_SSH_COMMAND"]
    assert "ConnectTimeout=20" in env["GIT_SSH_COMMAND"]
    assert "ServerAliveInterval=15" in env["GIT_SSH_COMMAND"]

    moment = datetime(2026, 7, 30, 8, tzinfo=UTC)
    direct_payload = b"abc"
    direct_message_hash = sha256(b"msg-direct").hexdigest()
    direct = DownloadedAttachment(
        {
            "openConversationId": "group-fixture",
            "senderOpenDingTalkId": "sender-fixture",
            "openMessageId": "msg-direct",
            "createTime": moment.isoformat(),
            "content": "资金账户明细表 mediaId=fixture-direct",
        }, "msg-direct", direct_message_hash, moment,
        0, "same.csv", ACCOUNT_FAMILY, direct_payload, __import__("hashlib").sha256(direct_payload).hexdigest(), "text/csv",
    )
    changed_payload = b"def"
    changed_message_hash = sha256(b"msg-different").hexdigest()
    same_name_different_bytes = DownloadedAttachment(
        {
            "openConversationId": "group-fixture",
            "senderOpenDingTalkId": "sender-fixture",
            "openMessageId": "msg-different",
            "createTime": moment.isoformat(),
            "content": "资金账户明细表 mediaId=fixture-different",
        }, "msg-different", changed_message_hash, moment,
        0, "same.csv", ACCOUNT_FAMILY, changed_payload, __import__("hashlib").sha256(changed_payload).hexdigest(), "text/csv",
    )
    oversize_payload = b"0123456789abcdef"
    oversize_message_hash = sha256(b"msg-oversize").hexdigest()
    oversize = DownloadedAttachment(
        {
            "openConversationId": "group-fixture",
            "senderOpenDingTalkId": "sender-fixture",
            "openMessageId": "msg-oversize",
            "createTime": moment.isoformat(),
            "content": "资金流水明细 mediaId=fixture-unused mediaId=fixture-oversize",
        }, "msg-oversize", oversize_message_hash, moment,
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
    persisted_references = tuple(
        PersistedRawAttachment(
            message=attachment.message,
            message_id=attachment.message_id,
            message_id_hash=attachment.message_id_hash,
            message_at=attachment.message_at,
            index=attachment.index,
            sha256=attachment.sha256,
        )
        for attachment in (oversize, direct, same_name_different_bytes)
    )
    persisted_patterns = writer._persisted_raw_sparse_patterns(persisted_references)
    assert f"{(SPARSE_PATH / 'raw/blobs/sha256' / direct.sha256[:2] / direct.sha256).as_posix()}*" in persisted_patterns
    assert f"{(SPARSE_PATH / 'raw/chunks/sha256' / oversize.sha256).as_posix()}/" in persisted_patterns
    raw_writer_commands.clear()
    reopened = writer.reopen_persisted(persisted_references)
    assert reopened.commit_sha == commit.commit_sha
    assert {attachment.sha256 for attachment in reopened.verified_attachments} == {
        direct.sha256, same_name_different_bytes.sha256, oversize.sha256,
    }
    assert not any(command and command[0] in {"add", "commit", "push"} for command in raw_writer_commands)
    raw_writer_commands.clear()
    archive_audit = writer.audit_raw_archive()
    assert archive_audit.commit_sha == commit.commit_sha
    assert archive_audit.occurrence_count == 3
    assert archive_audit.batch_count == 1
    assert archive_audit.batch_occurrence_references == 3
    assert {attachment.sha256 for attachment in archive_audit.verified_attachments} == {
        direct.sha256, same_name_different_bytes.sha256, oversize.sha256,
    }
    assert not any(command and command[0] in {"add", "commit", "push"} for command in raw_writer_commands)
    raw_writer_commands.clear()
    streamed: list[DownloadedAttachment] = []
    streamed_audit = writer.audit_raw_archive(on_attachment=streamed.append)
    assert streamed_audit.commit_sha == commit.commit_sha
    assert streamed_audit.verified_attachments == ()
    assert streamed_audit.occurrence_count == 3
    assert {attachment.sha256 for attachment in streamed} == {
        direct.sha256, same_name_different_bytes.sha256, oversize.sha256,
    }
    assert not any(command and command[0] in {"add", "commit", "push"} for command in raw_writer_commands)
    raw_writer_commands.clear()
    metadata_streamed: list[PersistedRawAttachment] = []
    metadata_audit = writer.audit_raw_archive_metadata(on_attachment=metadata_streamed.append)
    assert metadata_audit.commit_sha == commit.commit_sha
    assert metadata_audit.verified_attachments == ()
    assert metadata_audit.occurrence_count == 3
    assert {attachment.sha256 for attachment in metadata_streamed} == {
        direct.sha256, same_name_different_bytes.sha256, oversize.sha256,
    }
    # Metadata recovery reuses its already-pinned sparse tree checkout.  A
    # second clone/fetch of the identical commit turns ordinary cloud latency
    # into a prolonged recovery window without strengthening the proof.
    assert len([command for command in raw_writer_commands if command and command[0] == "clone"]) == 1
    assert ("checkout", "main") not in raw_writer_commands
    assert ("checkout", "--detach", commit.commit_sha) in raw_writer_commands
    assert not any(command and command[0] in {"add", "commit", "push"} for command in raw_writer_commands)
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

    publication = _t06_publication()
    publication["git_commit_sha"] = commit.commit_sha
    publication_commit = writer.persist_publication(publication)
    # The publication commit advances the branch after the raw batch.  A
    # later audit must still reopen the immutable raw-batch commit rather than
    # silently reading whichever branch tip happened to arrive next.
    pinned = tmp_path / "pinned-raw-audit-sparse"
    writer._clone_sparse(
        pinned,
        env=env,
        ref="main",
        patterns=narrow_patterns,
        commit_sha=commit.commit_sha,
    )
    assert RawMaterializer.readback_attachment(pinned / SPARSE_PATH, direct).payload == direct_payload
    assert not (pinned / SPARSE_PATH / "baseline.txt").exists()
    pinned_metadata = writer.audit_raw_archive_metadata(commit_sha=commit.commit_sha)
    assert pinned_metadata.commit_sha == commit.commit_sha
    assert pinned_metadata.occurrence_count == 3
    recovery_bundle = writer.bundle_head()
    RestoreOracle.verify_private_publication_bundle(
        recovery_bundle,
        expected_raw_commit_sha=commit.commit_sha,
        expected_publication_commit_sha=publication_commit,
        publication=publication,
    )

    # A later DWS replay can retain the same source identity and bytes while
    # changing only the downloader-supplied filename.  It must create a fresh
    # batch receipt if needed, never collide with or overwrite the first raw
    # occurrence, and the readback must use the historic canonical filename.
    filename_drift = replace(direct, filename="same.png")
    replayed = writer.persist((filename_drift,))
    assert replayed.commit_sha != commit.commit_sha
    assert replayed.verified_attachments == (direct,)

    # A later overlap can combine occurrences that were originally written in
    # separate immutable raw batches.  Reopening must prove each original
    # batch membership, not invent a page-level batch manifest that never
    # existed in the private authority.
    separate_payload = b"separate-batch"
    separate_message_hash = sha256(b"msg-separate-batch").hexdigest()
    separate = DownloadedAttachment(
        {
            "openConversationId": "group-fixture",
            "senderOpenDingTalkId": "sender-fixture",
            "openMessageId": "msg-separate-batch",
            "createTime": moment.isoformat(),
            "content": "资金流水明细 mediaId=fixture-separate",
        },
        "msg-separate-batch",
        separate_message_hash,
        moment,
        0,
        "separate.csv",
        "资金流水明细",
        separate_payload,
        __import__("hashlib").sha256(separate_payload).hexdigest(),
        "text/csv",
    )
    writer.persist((separate,))
    cross_batch_reopen = writer.reopen_persisted((
        PersistedRawAttachment(
            message=direct.message,
            message_id=direct.message_id,
            message_id_hash=direct.message_id_hash,
            message_at=direct.message_at,
            index=direct.index,
            sha256=direct.sha256,
        ),
        PersistedRawAttachment(
            message=separate.message,
            message_id=separate.message_id,
            message_id_hash=separate.message_id_hash,
            message_at=separate.message_at,
            index=separate.index,
            sha256=separate.sha256,
        ),
    ))
    assert {attachment.sha256 for attachment in cross_batch_reopen.verified_attachments} == {
        direct.sha256,
        separate.sha256,
    }
    assert isinstance(cross_batch_reopen.staged, ReopenedRawEvidence)
    assert len(cross_batch_reopen.staged.source_batch_paths) == 2

    def reject_occurrence_metadata(*_args):
        raise IngestionError("GIT_READBACK_FAILED")

    monkeypatch.setattr(writer, "_archive_occurrence_metadata", reject_occurrence_metadata)
    with pytest.raises(IngestionError, match="RAW_ARCHIVE_METADATA_OCCURRENCE_METADATA_NEEDS_REVIEW"):
        writer.audit_raw_archive_metadata()


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
    sparse_repo = tmp_path / "narrow-sparse"
    sparse_repo.mkdir()
    writer._clone_sparse(sparse_repo, env={}, ref="main", patterns=patterns)

    assert commands[0][:7] == [
        "clone", "--branch", "main", "--depth=1", "--filter=blob:none", "--sparse", "--no-checkout",
    ]
    assert commands[1] == ["sparse-checkout", "set", "--no-cone", *patterns]
    assert commands[2] == ["checkout", "main"]
    assert f"{SPARSE_PATH.as_posix()}/" not in patterns
    assert all(pattern.startswith(f"{SPARSE_PATH.as_posix()}/raw/") for pattern in patterns)
    expected_batch_pattern = (SPARSE_PATH / "raw/batches" / f"{RawMaterializer._batch_details((attachment,))[0]}.json").as_posix()
    assert expected_batch_pattern in patterns
    assert writer._publication_sparse_patterns("2026-07-31") == (
        f"{(SPARSE_PATH / 'publications/2026-07-31').as_posix()}/",
    )


def test_sparse_scope_validation_prunes_git_metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import daily_funds.ingestion as ingestion

    repo = tmp_path / "sparse-clone"
    metadata = repo / ".git" / "objects" / "pack"
    metadata.mkdir(parents=True)
    (metadata / "large-pack-placeholder").write_bytes(b"metadata")
    allowed = repo / SPARSE_PATH / "raw" / "allowed.json"
    allowed.parent.mkdir(parents=True)
    allowed.write_text("{}\n", encoding="utf-8")

    observed_roots: list[Path] = []
    original_walk = ingestion.os.walk

    def observe_walk(*args, **kwargs):
        assert kwargs["topdown"] is True
        assert kwargs["followlinks"] is False
        for current, directories, files in original_walk(*args, **kwargs):
            observed_roots.append(Path(current).relative_to(repo))
            yield current, directories, files

    monkeypatch.setattr(ingestion.os, "walk", observe_walk)
    GitSparseWriter._assert_sparse_checkout_scope(repo)

    assert Path(".") in observed_roots
    assert all(".git" not in root.parts for root in observed_roots)


def test_kmfile_metadata_selects_only_exact_group_message_file_links(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """KMFile registration narrows a title-less candidate without naming a family."""

    writer = GitSparseWriter(_config(tmp_path))
    commit_sha = "c" * 40
    manifest = KMFILE_METADATA_PATH / "fixture-group" / ".manifest.jsonl"
    clone_calls: list[dict[str, object]] = []

    def fake_git(args, **_kwargs):
        if args[:2] == ["rev-parse", "HEAD"]:
            return commit_sha
        if args[:3] == ["ls-tree", "-r", "--name-only"]:
            return manifest.as_posix()
        return ""

    def fake_clone(repo: Path, **kwargs) -> None:
        clone_calls.append(dict(kwargs))
        repo.mkdir(parents=True, exist_ok=True)
        if repo.name == "private-kmfile-metadata":
            target = repo / manifest
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                "\n".join((
                    json.dumps({
                        "conversation_id": writer.config.group_id,
                        "message_id": "registered-message",
                        "file_id": "registered-file",
                    }),
                    json.dumps({
                        "conversation_id": "other-group",
                        "message_id": "registered-message",
                        "file_id": "other-file",
                    }),
                    json.dumps({
                        "conversation_id": writer.config.group_id,
                        "message_id": "missing-file",
                    }),
                )) + "\n",
                encoding="utf-8",
            )

    monkeypatch.setattr(writer, "_git", fake_git)
    monkeypatch.setattr(writer, "_clone_sparse", fake_clone)

    assert writer.kmfile_registered_attachment_keys() == frozenset({
        ("registered-message", "registered-file"),
    })
    assert len(clone_calls) == 2
    assert all(call["allowed_roots"] == (KMFILE_METADATA_PATH,) for call in clone_calls)
    assert clone_calls[1]["patterns"] == (manifest.as_posix(),)


def test_sparse_writer_pins_a_sparse_checkout_to_an_exact_audited_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writer = GitSparseWriter(_config(tmp_path))
    commands: list[list[str]] = []

    def fake_git(args, **_kwargs):
        commands.append(list(args))
        return ""

    monkeypatch.setattr(writer, "_git", fake_git)
    commit_sha = "a" * 40
    patterns = (f"{SPARSE_PATH.as_posix()}/raw/",)
    sparse_repo = tmp_path / "pinned-sparse"
    sparse_repo.mkdir()

    writer._clone_sparse(
        sparse_repo,
        env={},
        ref="main",
        patterns=patterns,
        audit_read=True,
        commit_sha=commit_sha,
    )

    assert commands[0][:7] == [
        "clone", "--branch", "main", "--depth=1", "--filter=blob:none", "--sparse", "--no-checkout",
    ]
    assert commands[1] == ["sparse-checkout", "set", "--no-cone", *patterns]
    assert commands[2] == ["fetch", "--depth=1", "origin", commit_sha]
    assert commands[3] == ["checkout", "--detach", commit_sha]


def test_sparse_writer_retries_only_the_pre_mutation_prepare_phase_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A transient pre-write clone failure gets one fresh isolated retry."""

    writer = GitSparseWriter(_config(tmp_path))
    attempts: list[str] = []

    def transient_clone(repo: Path, **_kwargs) -> None:
        attempts.append(repo.name)
        if len(attempts) == 1:
            raise IngestionError("GIT_ARCHIVE_PREPARE_FAILED")

    monkeypatch.setattr(writer, "_clone_sparse", transient_clone)

    prepared = writer._prepare_sparse_clone_with_single_retry(
        tmp_path / "private-db",
        env={},
        ref="main",
        patterns=(f"{SPARSE_PATH.as_posix()}/raw/",),
    )

    assert prepared == tmp_path / "private-db-retry"
    assert attempts == ["private-db", "private-db-retry"]


def test_sparse_writer_does_not_retry_scope_or_second_prepare_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only the fixed prepare-stage failure may retry, and only once."""

    writer = GitSparseWriter(_config(tmp_path))
    attempts: list[str] = []

    def scope_failure(repo: Path, **_kwargs) -> None:
        attempts.append(repo.name)
        raise IngestionError("GIT_SPARSE_SCOPE_VIOLATION")

    monkeypatch.setattr(writer, "_clone_sparse", scope_failure)
    with pytest.raises(IngestionError, match="^GIT_SPARSE_SCOPE_VIOLATION$"):
        writer._prepare_sparse_clone_with_single_retry(
            tmp_path / "private-db",
            env={},
            ref="main",
            patterns=(f"{SPARSE_PATH.as_posix()}/raw/",),
        )
    assert attempts == ["private-db"]

    attempts.clear()

    def repeated_prepare_failure(repo: Path, **_kwargs) -> None:
        attempts.append(repo.name)
        raise IngestionError("GIT_ARCHIVE_PREPARE_FAILED")

    monkeypatch.setattr(writer, "_clone_sparse", repeated_prepare_failure)
    with pytest.raises(IngestionError, match="^GIT_ARCHIVE_PREPARE_FAILED$"):
        writer._prepare_sparse_clone_with_single_retry(
            tmp_path / "private-db",
            env={},
            ref="main",
            patterns=(f"{SPARSE_PATH.as_posix()}/raw/",),
        )
    assert attempts == ["private-db", "private-db-retry"]


def test_sparse_writer_retries_only_pre_validation_readback_preparation_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fresh sparse readback setup may retry once before any bytes are read."""

    writer = GitSparseWriter(_config(tmp_path))
    attempts: list[str] = []

    def transient_clone(repo: Path, **_kwargs) -> None:
        attempts.append(repo.name)
        if len(attempts) == 1:
            raise IngestionError("GIT_ARCHIVE_READBACK_FAILED")

    monkeypatch.setattr(writer, "_clone_sparse", transient_clone)
    monkeypatch.setattr(writer, "_git", lambda *_args, **_kwargs: "")

    root = writer._readback_sparse_root(
        tmp_path,
        env={},
        commit_sha="a" * 40,
        patterns=(f"{SPARSE_PATH.as_posix()}/raw/",),
        failure_code="GIT_ARCHIVE_READBACK_FAILED",
    )

    assert root == tmp_path / "private-db-readback-retry" / SPARSE_PATH
    assert attempts == ["private-db-readback", "private-db-readback-retry"]


def test_sparse_writer_does_not_retry_readback_scope_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scope errors remain fail-closed before any readback bytes are opened."""

    writer = GitSparseWriter(_config(tmp_path))
    attempts: list[str] = []

    def scope_failure(repo: Path, **_kwargs) -> None:
        attempts.append(repo.name)
        raise IngestionError("GIT_SPARSE_SCOPE_VIOLATION")

    monkeypatch.setattr(writer, "_clone_sparse", scope_failure)
    with pytest.raises(IngestionError, match="^GIT_SPARSE_SCOPE_VIOLATION$"):
        writer._readback_sparse_root(
            tmp_path,
            env={},
            commit_sha="a" * 40,
            patterns=(f"{SPARSE_PATH.as_posix()}/raw/",),
            failure_code="GIT_ARCHIVE_READBACK_FAILED",
        )
    assert attempts == ["private-db-readback"]


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


def test_sparse_writer_exposes_only_fixed_archive_stage_code_on_write_failure(tmp_path: Path) -> None:
    """Write diagnostics name the pipeline stage, never Git stderr content."""

    def runner(command, **_kwargs):
        return subprocess.CompletedProcess(command, 1, "", "private remote diagnostic")

    writer = GitSparseWriter(_config(tmp_path), runner=runner)
    with pytest.raises(IngestionError, match="^GIT_ARCHIVE_STAGE_FAILED$") as error:
        writer._git(
            ["add", "--sparse", "--", str(SPARSE_PATH)],
            failure_code="GIT_ARCHIVE_STAGE_FAILED",
        )
    assert "private" not in str(error.value)


def test_raw_archive_audit_retries_one_fresh_read_only_transport_attempt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A transient sparse-read transport failure gets one retry, nothing more."""

    writer = GitSparseWriter(_config(tmp_path))
    expected = RawArchiveAudit(
        commit_sha="a" * 40,
        verified_attachments=(),
        occurrence_count=0,
        batch_count=0,
        batch_occurrence_references=0,
    )
    attempts: list[str] = []

    def transient_then_success() -> RawArchiveAudit:
        attempts.append("attempt")
        if len(attempts) == 1:
            raise IngestionError("GIT_AUDIT_TRANSPORT_RETRYABLE")
        return expected

    monkeypatch.setattr(writer, "_audit_raw_archive_once", transient_then_success)

    assert writer.audit_raw_archive() is expected
    assert attempts == ["attempt", "attempt"]


def test_raw_archive_audit_does_not_retry_integrity_readback_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A malformed/mismatched raw readback stays fail-closed on first sight."""

    writer = GitSparseWriter(_config(tmp_path))
    attempts: list[str] = []

    def integrity_failure() -> RawArchiveAudit:
        attempts.append("attempt")
        raise IngestionError("GIT_READBACK_FAILED")

    monkeypatch.setattr(writer, "_audit_raw_archive_once", integrity_failure)

    with pytest.raises(IngestionError, match="GIT_READBACK_FAILED"):
        writer.audit_raw_archive()
    assert attempts == ["attempt"]


def test_raw_archive_audit_capacity_covers_the_current_private_history_census(tmp_path: Path) -> None:
    """The bounded auditor must accept the verified 526-record source census."""

    writer = GitSparseWriter(_config(tmp_path))

    assert writer._RAW_ARCHIVE_MAX_OCCURRENCES == 1024
    assert 526 <= writer._RAW_ARCHIVE_MAX_OCCURRENCES
    assert writer._RAW_ARCHIVE_MAX_BATCHES == 512


def test_sparse_writer_marks_only_transport_stderr_retryable_for_audit_reads(tmp_path: Path) -> None:
    command: list[str] = []

    def runner(args, **_kwargs):
        command.extend(args)
        return subprocess.CompletedProcess(args, 1, "", "Connection reset by peer")

    writer = GitSparseWriter(_config(tmp_path), runner=runner)

    with pytest.raises(IngestionError, match="GIT_AUDIT_TRANSPORT_RETRYABLE"):
        writer._git(["clone", "fixture"], audit_read=True)
    assert command[:2] == ["git", "clone"]


def test_source_gate_uses_one_group_and_a_bounded_static_sender_allowlist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _config(tmp_path)
    assert config.validate() is None
    from dataclasses import replace
    from daily_funds.config import ConfigError

    with pytest.raises(ConfigError, match="SOURCE_ID_NOT_UNIQUE"):
        replace(config, group_id="group-a,group-b").validate()
    with pytest.raises(ConfigError, match="CONFIG_INVALID"):
        replace(config, sender_id="").validate()
    allowlisted = replace(config, sender_ids=(config.sender_id, "sender-fixture-2"))
    assert allowlisted.validate() is None
    with pytest.raises(ConfigError, match="SOURCE_ID_LIST_INVALID"):
        replace(config, sender_ids=(config.sender_id, config.sender_id)).validate()
    with pytest.raises(ConfigError, match="SOURCE_ID_LIST_INVALID"):
        replace(config, sender_ids=tuple(f"sender-{index}" for index in range(13))).validate()
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


def test_embedded_build_source_identity_is_hashed_and_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import daily_funds.runtime as runtime_module

    runtime = DailyFundsRuntime(_config(tmp_path))
    marker = tmp_path / "embedded-source-commit"
    source_commit = "a" * 40
    marker.write_text(source_commit + "\n", encoding="ascii")
    monkeypatch.setattr(runtime_module, "_BUILD_SOURCE_COMMIT_FILE", marker)

    runtime._write_flow_state(stage="RUNTIME_AUDITED")
    flow_text = (runtime.config.publication_dir / "flow_state.json").read_text(encoding="utf-8")
    flow = json.loads(flow_text)
    deployment = flow["deployment"]
    assert deployment["identity_state"] == "BUILD_SOURCE_COMMIT_EMBEDDED"
    assert deployment["source_commit_fingerprint"] == sha256(source_commit.encode("ascii")).hexdigest()
    assert source_commit not in flow_text

    marker.write_text("UNKNOWN\n", encoding="ascii")
    runtime._write_flow_state(stage="RUNTIME_AUDITED")
    flow = json.loads((runtime.config.publication_dir / "flow_state.json").read_text(encoding="utf-8"))
    assert flow["deployment"]["identity_state"] == "UNKNOWN"
    assert flow["deployment"]["source_commit_fingerprint"] is None


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


def test_dws_history_rejects_recordless_terminal_v1_envelope(tmp_path: Path) -> None:
    config = _config(tmp_path)
    events: list[tuple[str, str, str]] = []

    def runner(command, **kwargs):
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": True, "refresh_token_valid": True}), "")
        if command[1:4] == ["chat", "message", "search-advanced"]:
            assert command[command.index("--conversation-ids") + 1] == config.group_id
            return subprocess.CompletedProcess(command, 0, json.dumps({
                "success": True,
                "result": {"hasMore": False},
            }), "")
        raise AssertionError(f"unexpected DWS command: {command}")

    client = DwsHistoryClient(config, runner=runner, event_sink=lambda *event: events.append(event))
    with pytest.raises(IngestionError, match="DWS_PAGE_RECORDS_MISSING") as exc_info:
        client.search(datetime(2026, 8, 1, tzinfo=UTC), datetime(2026, 8, 1, 0, 1, tzinfo=UTC), None)
    assert exc_info.value.record_list_shape == "NO_DIRECT_LIST"
    assert events == [
        ("DWS", "AUTH_STATUS", "OK"),
        ("DWS", "HISTORY_SEARCH_ADVANCED", "DWS_PAGE_RECORDS_MISSING"),
    ]


def test_dws_history_accepts_explicit_empty_terminal_v1_envelope_and_stable_sender_id(tmp_path: Path) -> None:
    config = _config(tmp_path)

    def runner(command, **kwargs):
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": True, "refresh_token_valid": True}), "")
        if command[1:4] == ["chat", "message", "search-advanced"]:
            assert command[command.index("--conversation-ids") + 1] == config.group_id
            return subprocess.CompletedProcess(command, 0, json.dumps({
                "success": True,
                "result": {"hasMore": False, "messages": []},
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


def test_dws_quarantine_messages_keeps_exact_source_attachment_without_declared_family(tmp_path: Path) -> None:
    config = _config(tmp_path)
    client = DwsHistoryClient(config)
    message = {
        "openConversationId": config.group_id,
        "senderOpenDingTalkId": config.sender_id,
        "openMessageId": "unclassified-fixture-message",
        "createTime": datetime(2026, 8, 1, tzinfo=UTC).isoformat(),
        "content": "opaque attachment notice",
        "attachments": [{"mediaId": "unclassified-fixture-media"}],
    }
    page = DwsPage(messages=(message,), next_cursor=None, has_more=False)
    assert client.selected_messages(page) == ()
    assert client.quarantine_messages(page) == (message,)

    other_sender = dict(message, senderOpenDingTalkId="other-sender")
    assert client.quarantine_messages(DwsPage(messages=(other_sender,), next_cursor=None, has_more=False)) == ()

    wrong_group = dict(message, openConversationId="other-group")
    with pytest.raises(IngestionError, match="AMBIGUOUS_SOURCE"):
        client.quarantine_messages(DwsPage(messages=(wrong_group,), next_cursor=None, has_more=False))


def test_dws_history_accepts_official_message_list_terminal_envelope(tmp_path: Path) -> None:
    """The official ``im/search_messages`` adapter also emits ``messageList``."""

    config = _config(tmp_path)

    def runner(command, **kwargs):
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": True, "refresh_token_valid": True}), "")
        if command[1:4] == ["chat", "message", "search-advanced"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({
                "success": True,
                "result": {"hasMore": False, "messageList": []},
            }), "")
        raise AssertionError(f"unexpected DWS command: {command}")

    client = DwsHistoryClient(config, runner=runner)
    assert client.search(
        datetime(2026, 8, 1, tzinfo=UTC),
        datetime(2026, 8, 1, 0, 1, tzinfo=UTC),
        None,
    ) == DwsPage(messages=(), next_cursor=None, has_more=False)


def test_dws_history_accepts_official_raw_result_array_terminal_envelope(tmp_path: Path) -> None:
    """The official adapter also permits a direct raw ``result`` list."""

    config = _config(tmp_path)

    def runner(command, **kwargs):
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": True, "refresh_token_valid": True}), "")
        if command[1:4] == ["chat", "message", "search-advanced"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({
                "hasMore": False,
                "result": [],
            }), "")
        raise AssertionError(f"unexpected DWS command: {command}")

    client = DwsHistoryClient(config, runner=runner)
    assert client.search(
        datetime(2026, 8, 1, tzinfo=UTC),
        datetime(2026, 8, 1, 0, 1, tzinfo=UTC),
        None,
    ) == DwsPage(messages=(), next_cursor=None, has_more=False)


def test_dws_history_accepts_official_grouped_search_messages_shape(tmp_path: Path) -> None:
    """A grouped official search result supplies its parent conversation ID."""

    config = _config(tmp_path)

    def runner(command, **kwargs):
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": True, "refresh_token_valid": True}), "")
        if command[1:4] == ["chat", "message", "search-advanced"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({
                "success": True,
                "result": {
                    "hasMore": False,
                    "conversationMessagesList": [{
                        "openConversationId": config.group_id,
                        "messages": [{
                            "openMessageId": "message-1",
                            "senderOpenDingTalkId": config.sender_id,
                            "createTime": "2026-08-01T00:00:00Z",
                            "content": "资金明细",
                        }],
                    }],
                },
            }), "")
        raise AssertionError(f"unexpected DWS command: {command}")

    client = DwsHistoryClient(config, runner=runner)
    page = client.search(
        datetime(2026, 8, 1, tzinfo=UTC),
        datetime(2026, 8, 1, 0, 1, tzinfo=UTC),
        None,
    )
    assert len(page.messages) == 1
    assert page.messages[0]["openConversationId"] == config.group_id
    client.assert_exact_source(page.messages[0])


def test_dws_history_accepts_explicit_list_with_nested_pagination_wrapper(tmp_path: Path) -> None:
    """Cursor metadata may be nested while the official list stays at result level."""

    config = _config(tmp_path)

    def runner(command, **kwargs):
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": True, "refresh_token_valid": True}), "")
        if command[1:4] == ["chat", "message", "search-advanced"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({
                "success": True,
                "result": {
                    "messageList": [],
                    "pagination": {"hasMore": False},
                },
            }), "")
        raise AssertionError(f"unexpected DWS command: {command}")

    client = DwsHistoryClient(config, runner=runner)
    assert client.search(
        datetime(2026, 8, 1, tzinfo=UTC),
        datetime(2026, 8, 1, 0, 1, tzinfo=UTC),
        None,
    ) == DwsPage(messages=(), next_cursor=None, has_more=False)


def test_dws_history_rejects_list_outside_named_pagination_wrapper(tmp_path: Path) -> None:
    """An arbitrary nested ``hasMore`` must not borrow its parent list."""

    config = _config(tmp_path)

    def runner(command, **kwargs):
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": True, "refresh_token_valid": True}), "")
        if command[1:4] == ["chat", "message", "search-advanced"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({
                "success": True,
                "result": {
                    "messageList": [],
                    "unrelated": {"hasMore": False},
                },
            }), "")
        raise AssertionError(f"unexpected DWS command: {command}")

    client = DwsHistoryClient(config, runner=runner)
    with pytest.raises(IngestionError, match="DWS_PAGE_RECORDS_MISSING"):
        client.search(
            datetime(2026, 8, 1, tzinfo=UTC),
            datetime(2026, 8, 1, 0, 1, tzinfo=UTC),
            None,
        )


def test_recordless_terminal_dws_page_never_becomes_source_match_zero_without_a_complete_group_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _config(tmp_path)

    def runner(command, **kwargs):
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": True, "refresh_token_valid": True}), "")
        if command[1:4] == ["chat", "message", "search-advanced"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({
                "success": True,
                "result": {"hasMore": False},
            }), "")
        if command[1:3] == ["chat", "+chat-messages"]:
            # A page limit is a partial ledger, not a valid empty source.
            return subprocess.CompletedProcess(command, 0, json.dumps({
                "messages": [],
                "count": 0,
                "pagesFetched": 500,
                "paginationKnown": True,
                "complete": False,
                "hasMore": True,
                "stopReason": "page_limit",
                "truncatedByPageLimit": True,
                "truncatedByResultLimit": False,
                "failedCount": 0,
                "failures": [],
                "partial": False,
            }), "")
        raise AssertionError(f"unexpected DWS command: {command}")

    runtime = DailyFundsRuntime(config)
    client = DwsHistoryClient(config, runner=runner)
    monkeypatch.setattr(runtime, "_dws_client", lambda: client)

    assert runtime.poll(now=datetime(2026, 8, 1, tzinfo=UTC)) == {
        "ok": False,
        "code": "DWS_GROUP_HISTORY_COLLECT_INCOMPLETE",
    }


def test_dws_reopen_candidate_requires_exact_source_but_allows_embedded_media(tmp_path: Path) -> None:
    config = _config(tmp_path)
    client = DwsHistoryClient(config)
    message = {
        "openConversationId": config.group_id,
        "senderOpenDingTalkId": config.sender_id,
        "openMessageId": "cached-message",
        "createTime": "2026-08-01 08:00:00",
        # DWS may expose the media ID only in text, without a filename.  The
        # immutable raw occurrence supplies the original filename later.
        "content": "资金账户明细表 mediaId=opaque-media-id",
    }
    attachment_sha256 = "d" * 64
    candidate = client.reopen_candidate(message, 0, attachment_sha256)
    assert candidate is not None
    assert candidate.sha256 == attachment_sha256
    assert candidate.message_id_hash == client.message_id_hash(message)
    assert client.reopen_candidate(message, 0, "not-a-sha") is None
    unclassified = dict(message, content="opaque mediaId=unclassified-media")
    assert client.reopen_candidate(unclassified, 0, attachment_sha256) is not None
    ambiguous = dict(message)
    ambiguous["senderOpenDingTalkId"] = "other-sender"
    with pytest.raises(IngestionError, match="AMBIGUOUS_SOURCE"):
        client.reopen_candidate(ambiguous, 0, attachment_sha256)


def test_dws_search_advanced_uses_opaque_cursor_and_embedded_media_source(tmp_path: Path) -> None:
    config = _config(tmp_path)
    calls: list[list[str]] = []
    responses = [
        {
            "success": True,
            "result": {
                "hasMore": True,
                "nextCursor": "opaque-page-2",
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
        if command[1:4] == ["chat", "message", "search-advanced"]:
            return subprocess.CompletedProcess(command, 0, json.dumps(responses.pop(0)), "")
        raise AssertionError(f"unexpected DWS command: {command}")

    client = DwsHistoryClient(config, runner=runner)
    start = datetime(2026, 8, 1, tzinfo=UTC)
    first = client.search(start, datetime(2026, 8, 1, 0, 10, tzinfo=UTC), None)
    assert first.next_cursor == "opaque-page-2"
    assert first.has_more is True
    assert client.attachment_count(first.messages[0]) == 1
    assert client.selected_messages(first) == first.messages
    second = client.search(start, datetime(2026, 8, 1, 0, 10, tzinfo=UTC), first.next_cursor)
    assert second == DwsPage(messages=(), next_cursor=None, has_more=False)
    history_calls = [call for call in calls if call[1:4] == ["chat", "message", "search-advanced"]]
    assert [call[call.index("--cursor") + 1] for call in history_calls] == ["0", "opaque-page-2"]
    assert all(call[call.index("--conversation-ids") + 1] == config.group_id for call in history_calls)
    assert all(call[call.index("--start") + 1] == "2026-08-01T00:00:00+00:00" for call in history_calls)
    assert all(call[call.index("--end") + 1] == "2026-08-01T00:10:00+00:00" for call in history_calls)
    # The remote selector is the exact group/sender intersection, while the
    # local triple gate remains mandatory before any raw write.
    assert all(call[call.index("--conversation-type") + 1] == "group" for call in history_calls)
    assert all(call[call.index("--sender-ids") + 1] == config.sender_id for call in history_calls)
    assert all("--group" not in call and "--user" not in call and "--open-dingtalk-id" not in call for call in history_calls)


def test_dws_exact_source_history_fallback_omits_time_bounds_but_keeps_group_and_sender(tmp_path: Path) -> None:
    """The diagnostic fallback stays on search-advanced and exposes no broad selector."""

    config = _config(tmp_path)
    calls: list[list[str]] = []

    def runner(command, **kwargs):
        calls.append(command)
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": True, "refresh_token_valid": True}), "")
        if command[1:4] == ["chat", "message", "search-advanced"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({
                "success": True,
                "result": {
                    "hasMore": False,
                    "messages": [{
                        "openMessageId": "history-message",
                        "openConversationId": config.group_id,
                        "senderOpenDingTalkId": config.sender_id,
                        "createTime": "2026-07-01T00:00:00Z",
                    }],
                },
            }), "")
        raise AssertionError(f"unexpected DWS command: {command}")

    page = DwsHistoryClient(config, runner=runner).search(None, None, None)
    assert len(page.messages) == 1
    history_call = next(call for call in calls if call[1:4] == ["chat", "message", "search-advanced"])
    assert history_call[history_call.index("--conversation-ids") + 1] == config.group_id
    assert history_call[history_call.index("--conversation-type") + 1] == "group"
    assert "--start" not in history_call and "--end" not in history_call
    assert history_call[history_call.index("--sender-ids") + 1] == config.sender_id


def test_dws_history_rejects_a_half_bounded_window_before_authentication(tmp_path: Path) -> None:
    client = DwsHistoryClient(_config(tmp_path))
    with pytest.raises(IngestionError, match="DWS_HISTORY_WINDOW_INVALID"):
        client.search(None, datetime(2026, 8, 1, tzinfo=UTC), None)


def test_dws_search_advanced_rejects_a_stalled_opaque_cursor(tmp_path: Path) -> None:
    config = _config(tmp_path)
    events: list[tuple[str, str, str]] = []

    def runner(command, **kwargs):
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": True, "refresh_token_valid": True}), "")
        if command[1:4] == ["chat", "message", "search-advanced"]:
            assert command[command.index("--cursor") + 1] == "opaque-stalled"
            return subprocess.CompletedProcess(command, 0, json.dumps({
                "success": True,
                "result": {
                    "hasMore": True,
                    "nextCursor": "opaque-stalled",
                    "messages": [{
                        "openMessageId": "message-1",
                        "openConversationId": config.group_id,
                        "senderOpenDingTalkId": config.sender_id,
                        "createTime": "2026-08-01 08:01:00",
                    }],
                },
            }), "")
        raise AssertionError(f"unexpected DWS command: {command}")

    with pytest.raises(IngestionError, match="DWS_HISTORY_CURSOR_STALLED"):
        DwsHistoryClient(config, runner=runner, event_sink=lambda *event: events.append(event)).search(
            datetime(2026, 8, 1, tzinfo=UTC),
            datetime(2026, 8, 1, 0, 10, tzinfo=UTC),
            "opaque-stalled",
        )
    assert events == [
        ("DWS", "AUTH_STATUS", "OK"),
        ("DWS", "HISTORY_SEARCH_ADVANCED", "INVALID"),
    ]


def test_dws_history_permission_denial_is_not_misreported_as_auth_loss(tmp_path: Path) -> None:
    config = _config(tmp_path)
    events: list[tuple[str, str, str]] = []

    def runner(command, **kwargs):
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": True, "refresh_token_valid": True}), "")
        if command[1:4] == ["chat", "message", "search-advanced"]:
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
        ("DWS", "HISTORY_SEARCH_ADVANCED", "DWS_HISTORY_PERMISSION_DENIED"),
    ]


def test_dws_attachment_permission_denial_is_not_misreported_as_auth_loss(tmp_path: Path) -> None:
    """DWS exit 1 can be a media permission denial, not an expired login."""

    config = _config(tmp_path)
    events: list[tuple[str, str, str]] = []

    def runner(command, **_kwargs):
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps({"authenticated": True, "refresh_token_valid": True}),
                "",
            )
        if command[1:3] == ["chat", "+messages-resource-download"]:
            assert command[command.index("--timeout") + 1] == "150"
            return subprocess.CompletedProcess(command, 1, "", "PermissionDenied attachment-private-detail")
        raise AssertionError(f"unexpected DWS command: {command}")

    message = {
        "openConversationId": config.group_id,
        "senderOpenDingTalkId": config.sender_id,
        "openMessageId": "attachment-permission-fixture",
        "createTime": "2026-08-01T00:00:00Z",
        "attachments": [{"mediaId": "attachment-permission-media"}],
    }
    with pytest.raises(IngestionError, match="^DWS_ATTACHMENT_PERMISSION_DENIED$") as exc_info:
        DwsHistoryClient(
            config,
            runner=runner,
            event_sink=lambda *event: events.append(event),
        ).download(message, 0)
    assert "attachment-private-detail" not in str(exc_info.value)
    assert events == [
        ("DWS", "AUTH_STATUS", "OK"),
        ("DWS", "ATTACHMENT_DOWNLOAD", "DWS_ATTACHMENT_PERMISSION_DENIED"),
    ]


@pytest.mark.parametrize(
    ("attachment", "expected_output_name", "expected_filename", "expected_resource_type"),
    (
        (
            {
                "mediaId": "attachment-workbook-media",
                "fileName": "daily-balance.xlsx",
                "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            },
            "attachment-0.xlsx",
            "daily-balance.xlsx",
            "mediaId",
        ),
        (
            {
                "mediaId": "attachment-image-media",
                "mimeType": "image/jpeg",
            },
            "attachment-0.jpg",
            "attachment-0.jpg",
            "mediaId",
        ),
        (
            {"mediaId": "attachment-unknown-media"},
            "attachment-0.download",
            "attachment-0.download",
            "mediaId",
        ),
        (
            {
                "type": "fileId",
                "resourceId": "attachment-native-workbook",
                "fileName": "daily-balance.xls",
            },
            "attachment-0.xls",
            "daily-balance.xls",
            "fileId",
        ),
    ),
)
def test_dws_attachment_download_uses_an_isolated_relative_output_directory(
    tmp_path: Path,
    attachment: dict[str, str],
    expected_output_name: str,
    expected_filename: str,
    expected_resource_type: str,
) -> None:
    """The current DWS downloader supports both native files and media."""

    config = _config(tmp_path)

    def runner(command, **kwargs):
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps({"authenticated": True, "refresh_token_valid": True}),
                "",
            )
        if command[1:3] == ["chat", "+messages-resource-download"]:
            assert command[command.index("--type") + 1] == expected_resource_type
            assert command[command.index("--output") + 1] == expected_output_name
            output_dir = Path(kwargs["cwd"])
            assert output_dir.name == "download"
            if expected_resource_type == "mediaId":
                assert command[command.index("--message-id") + 1] == "attachment-output-fixture"
                assert command[command.index("--open-conversation-id") + 1] == config.group_id
            else:
                assert "--message-id" not in command
                assert "--open-conversation-id" not in command
            (output_dir / expected_output_name).write_bytes(b"fixture-media")
            return subprocess.CompletedProcess(command, 0, "", "")
        raise AssertionError(f"unexpected DWS command: {command}")

    message = {
        "openConversationId": config.group_id,
        "senderOpenDingTalkId": config.sender_id,
        "openMessageId": "attachment-output-fixture",
        "createTime": "2026-08-01T00:00:00Z",
        "attachments": [attachment],
    }

    downloaded = DwsHistoryClient(config, runner=runner).download(message, 0)

    assert downloaded.filename == expected_filename
    assert downloaded.payload == b"fixture-media"


def test_dws_attachment_download_uses_resource_owned_media_context(tmp_path: Path) -> None:
    """A nested DWS resource resolves with its own message ID, not its parent."""

    config = _config(tmp_path)

    def runner(command, **kwargs):
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps({"authenticated": True, "refresh_token_valid": True}),
                "",
            )
        if command[1:3] == ["chat", "+messages-resource-download"]:
            assert command[command.index("--message-id") + 1] == "resource-message-1"
            assert command[command.index("--open-conversation-id") + 1] == config.group_id
            output_dir = Path(kwargs["cwd"])
            (output_dir / "attachment-0.png").write_bytes(b"fixture-media")
            return subprocess.CompletedProcess(command, 0, "", "")
        raise AssertionError(f"unexpected DWS command: {command}")

    message = {
        "openConversationId": config.group_id,
        "senderOpenDingTalkId": config.sender_id,
        "openMessageId": "outer-message-1",
        "createTime": "2026-08-01T00:00:00Z",
        "attachments": [{
            "type": "mediaId",
            "resourceId": "resource-media-1",
            "_dws_message_id": "resource-message-1",
            "_dws_open_conversation_id": config.group_id,
            "mimeType": "image/png",
        }],
    }

    downloaded = DwsHistoryClient(config, runner=runner).download(message, 0)

    assert downloaded.payload == b"fixture-media"


def test_dws_attachment_transport_timeout_has_a_fixed_safe_stage_code(tmp_path: Path) -> None:
    config = _config(tmp_path)
    events: list[tuple[str, str, str]] = []

    def runner(command, **_kwargs):
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps({"authenticated": True, "refresh_token_valid": True}),
                "",
            )
        if command[1:3] == ["chat", "+messages-resource-download"]:
            raise subprocess.TimeoutExpired(command, timeout=180)
        raise AssertionError(f"unexpected DWS command: {command}")

    message = {
        "openConversationId": config.group_id,
        "senderOpenDingTalkId": config.sender_id,
        "openMessageId": "attachment-timeout-fixture",
        "createTime": "2026-08-01T00:00:00Z",
        "attachments": [{"mediaId": "attachment-timeout-media"}],
    }
    with pytest.raises(IngestionError, match="^ATTACHMENT_DOWNLOAD_TRANSPORT_FAILED$"):
        DwsHistoryClient(
            config,
            runner=runner,
            event_sink=lambda *event: events.append(event),
        ).download(message, 0)
    assert events == [
        ("DWS", "AUTH_STATUS", "OK"),
        ("DWS", "ATTACHMENT_DOWNLOAD", "UNAVAILABLE"),
        ("DWS", "ATTACHMENT_DOWNLOAD", "TRANSPORT_FAILED"),
    ]


def test_dws_history_group_scope_preflight_is_exact_and_discards_its_response(tmp_path: Path) -> None:
    config = _config(tmp_path)
    events: list[tuple[str, str, str]] = []
    commands: list[list[str]] = []

    def runner(command, **_kwargs):
        commands.append(command)
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": True, "refresh_token_valid": True}), "")
        assert command == [
            config.dws_bin,
            "chat",
            "conversation-info",
            "--group",
            config.group_id,
            "--format",
            "json",
        ]
        return subprocess.CompletedProcess(command, 0, json.dumps({"result": {"opaque": "discarded"}}), "")

    DwsHistoryClient(config, runner=runner, event_sink=lambda *event: events.append(event)).verify_exact_group_scope()

    assert len(commands) == 2
    assert events == [
        ("DWS", "AUTH_STATUS", "OK"),
        ("DWS", "HISTORY_GROUP_SCOPE", "OK"),
    ]


def test_dws_group_history_v2_probe_uses_only_the_fixed_window_and_discards_messages(tmp_path: Path) -> None:
    config = _config(tmp_path)
    events: list[tuple[str, str, str]] = []
    commands: list[list[str]] = []
    start = datetime(2026, 8, 1, tzinfo=UTC)
    end = datetime(2026, 8, 2, tzinfo=UTC)
    source_sentinel = "group-history-source-value-must-not-persist"

    def runner(command, **_kwargs):
        commands.append(command)
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": True, "refresh_token_valid": True}), "")
        assert command == [
            config.dws_bin,
            "chat",
            "+chat-messages",
            "--group",
            config.group_id,
            "--start",
            start.isoformat(),
            "--end",
            end.isoformat(),
            "--order",
            "asc",
            "--limit",
            "100",
            "--page-all",
            "--page-limit",
            "2",
            "--format",
            "json",
        ]
        assert config.sender_id not in command
        return subprocess.CompletedProcess(command, 0, json.dumps({
            "messages": [{"text": source_sentinel}],
            "pagesFetched": 2,
            "paginationKnown": True,
            "complete": True,
            "hasMore": False,
            "failedCount": 0,
            "failures": [],
        }), "")

    result = DwsHistoryClient(
        config,
        runner=runner,
        event_sink=lambda *event: events.append(event),
    ).probe_group_history_v2(start, end)

    assert result.pages_fetched == 2
    assert result.has_more is False
    assert source_sentinel not in repr(result)
    assert len(commands) == 2
    assert events == [
        ("DWS", "AUTH_STATUS", "OK"),
        ("DWS", "HISTORY_GROUP_V2", "OK"),
    ]


def test_history_poller_falls_back_to_complete_exact_group_ledger_after_recordless_search(tmp_path: Path) -> None:
    """The compatibility path must be complete before it clears any cursor."""

    config = _config(tmp_path)
    state = RuntimeState(config.state_dir)
    state.commit_cursor("opaque-resume-cursor")
    events: list[tuple[str, str, str]] = []
    commands: list[list[str]] = []
    start = datetime(2026, 8, 1, tzinfo=UTC)
    end = datetime(2026, 8, 1, 0, 10, tzinfo=UTC)
    source_sentinel = "exact-group-source-value-stays-in-memory"

    def runner(command, **_kwargs):
        commands.append(command)
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": True, "refresh_token_valid": True}), "")
        if command[1:4] == ["chat", "message", "search-advanced"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({
                "success": True,
                "result": {"hasMore": False},
            }), "")
        assert command == [
            config.dws_bin,
            "chat",
            "+chat-messages",
            "--group",
            config.group_id,
            "--start",
            start.isoformat(),
            "--end",
            end.isoformat(),
            "--order",
            "asc",
            "--limit",
            "100",
            "--page-all",
            "--page-limit",
            "500",
            "--format",
            "json",
        ]
        return subprocess.CompletedProcess(command, 0, json.dumps({
            "messages": [{
                "conversationId": config.group_id,
                "senderId": config.sender_id,
                "messageId": "message-1",
                "createTime": "2026-08-01T00:05:00Z",
                "text": f"资金明细 {source_sentinel}",
                "resourceRefs": [
                    {
                        "type": "mediaId",
                        "resourceId": "media-1",
                        "download": {
                            "arguments": {
                                "message-id": "resource-message-1",
                                "open-conversation-id": config.group_id,
                            },
                        },
                    },
                    {"type": "fileId", "resourceId": "file-1"},
                ],
            }],
            "count": 1,
            "pagesFetched": 2,
            "paginationKnown": True,
            "complete": True,
            "hasMore": False,
            "stopReason": "range_end",
            "truncatedByPageLimit": False,
            "truncatedByResultLimit": False,
            "failedCount": 0,
            "failures": [],
            "partial": False,
        }), "")

    client = DwsHistoryClient(config, runner=runner, event_sink=lambda *event: events.append(event))
    seen: list[DwsPage] = []
    pages = HistoryPoller(state, client).poll(
        now=end,
        persist_page=seen.append,
        holder="fixture",
        start_override=start,
    )

    assert pages == 1
    assert len(seen) == 1
    page = seen[0]
    assert page.has_more is False and page.next_cursor is None
    assert len(page.messages) == 1
    message = page.messages[0]
    assert message["openConversationId"] == config.group_id
    assert message["senderOpenDingTalkId"] == config.sender_id
    assert message["openMessageId"] == "message-1"
    assert message["attachments"] == [
        {
            "type": "mediaId",
            "resourceId": "media-1",
            "_dws_message_id": "resource-message-1",
            "_dws_open_conversation_id": config.group_id,
        },
        {"type": "fileId", "resourceId": "file-1"},
    ]
    assert client.selected_messages(page) == (message,)
    assert state.get_cursor() is None
    assert state.get("history_high_water_at") == end.isoformat().replace("+00:00", "Z")
    assert events == [
        ("DWS", "AUTH_STATUS", "OK"),
        ("DWS", "HISTORY_SEARCH_ADVANCED", "DWS_PAGE_RECORDS_MISSING"),
        ("DWS", "HISTORY_GROUP_V2_COLLECT", "OK"),
    ]
    assert source_sentinel not in json.dumps(events)


def test_incomplete_group_history_fallback_never_advances_durable_cursor(tmp_path: Path) -> None:
    config = _config(tmp_path)
    state = RuntimeState(config.state_dir)
    state.commit_cursor("opaque-resume-cursor")

    def runner(command, **_kwargs):
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": True, "refresh_token_valid": True}), "")
        if command[1:4] == ["chat", "message", "search-advanced"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({
                "success": True,
                "result": {"hasMore": False},
            }), "")
        if command[1:3] == ["chat", "+chat-messages"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({
                "messages": [],
                "count": 0,
                "pagesFetched": 500,
                "paginationKnown": True,
                "complete": False,
                "hasMore": True,
                "stopReason": "page_limit",
                "truncatedByPageLimit": True,
                "truncatedByResultLimit": False,
                "failedCount": 0,
                "failures": [],
                "partial": False,
            }), "")
        raise AssertionError(f"unexpected DWS command: {command}")

    poller = HistoryPoller(state, DwsHistoryClient(config, runner=runner))
    with pytest.raises(IngestionError, match="DWS_GROUP_HISTORY_COLLECT_INCOMPLETE"):
        poller.poll(
            now=datetime(2026, 8, 1, 0, 10, tzinfo=UTC),
            persist_page=lambda _page: None,
            holder="fixture",
            start_override=datetime(2026, 8, 1, tzinfo=UTC),
        )
    assert state.get_cursor() == "opaque-resume-cursor"
    assert state.get("history_high_water_at") is None


def test_dws_group_history_v2_probe_refuses_a_recordless_or_incomplete_page(tmp_path: Path) -> None:
    config = _config(tmp_path)

    def runner(command, **_kwargs):
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": True, "refresh_token_valid": True}), "")
        return subprocess.CompletedProcess(command, 0, json.dumps({
            "pagesFetched": 1,
            "paginationKnown": True,
            "complete": True,
            "hasMore": False,
            "failedCount": 0,
            "failures": [],
        }), "")

    with pytest.raises(IngestionError, match="DWS_GROUP_HISTORY_PROBE_INVALID"):
        DwsHistoryClient(config, runner=runner).probe_group_history_v2(
            datetime(2026, 8, 1, tzinfo=UTC),
            datetime(2026, 8, 2, tzinfo=UTC),
        )


def test_dws_history_group_scope_preflight_keeps_permission_failure_values_free(tmp_path: Path) -> None:
    config = _config(tmp_path)

    def runner(command, **_kwargs):
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": True, "refresh_token_valid": True}), "")
        return subprocess.CompletedProcess(command, 1, "", "PermissionDenied target-group-private-detail")

    with pytest.raises(IngestionError, match="DWS_HISTORY_PERMISSION_DENIED") as exc_info:
        DwsHistoryClient(config, runner=runner).verify_exact_group_scope()
    assert "target-group-private-detail" not in str(exc_info.value)


def test_dws_history_stderr_permission_denial_is_not_misreported_as_auth_loss(tmp_path: Path) -> None:
    config = _config(tmp_path)

    def runner(command, **kwargs):
        if command[1:3] == ["auth", "status"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"authenticated": True, "refresh_token_valid": True}), "")
        if command[1:4] == ["chat", "message", "search-advanced"]:
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


def test_source_gate_preserves_missing_fact_family_and_business_date_diagnostics() -> None:
    account_payload = "业务日期,公司,开户行,账号,期初余额,期末余额\n2026-07-30,甲,乙,001,1.00,1.00\n".encode()
    transaction_payload = "业务日期,公司,开户行,账号,流水号,流入,流出\n2026-07-30,甲,乙,001,t,,\n".encode()
    accounts = parse_attachment(
        family=ACCOUNT_FAMILY,
        filename="资金账户明细表_20260730.csv",
        payload=account_payload,
        source=_source(account_payload, message_id_hash="d" * 64),
    )
    transactions = parse_attachment(
        family="资金流水明细",
        filename="资金流水明细_20260730.csv",
        payload=transaction_payload,
        source=_source(transaction_payload, message_id_hash="e" * 64),
    )
    moment = datetime(2026, 7, 30, tzinfo=UTC)
    with pytest.raises(ReconciliationError, match="ACCOUNT_SNAPSHOT_MISSING"):
        DailyFundsRuntime._latest_complete_pair((TimedFacts(transactions, moment),))
    with pytest.raises(ReconciliationError, match="TRANSACTION_FACT_MISSING"):
        DailyFundsRuntime._latest_complete_pair((TimedFacts(accounts, moment),))
    older_account_payload = account_payload.replace(b"2026-07-30", b"2026-07-29")
    older_accounts = parse_attachment(
        family=ACCOUNT_FAMILY,
        filename="资金账户明细表_20260729.csv",
        payload=older_account_payload,
        source=_source(older_account_payload, message_id_hash="f" * 64),
    )
    with pytest.raises(ReconciliationError, match="SOURCE_FACT_DATE_MISMATCH"):
        DailyFundsRuntime._latest_complete_pair((
            TimedFacts(older_accounts, moment), TimedFacts(transactions, moment),
        ))


def test_flow_state_preserves_values_free_missing_fact_family_gate(tmp_path: Path) -> None:
    runtime = DailyFundsRuntime(_config(tmp_path))
    status = runtime.status.write("需处理", "ACCOUNT_SNAPSHOT_MISSING")
    flow = runtime._write_flow_state(
        stage="POLL_NEEDS_ATTENTION",
        status=status,
        source_discovery_state="ACCOUNT_SNAPSHOT_MISSING",
    )
    assert flow["source_discovery"] == {"state": "ACCOUNT_SNAPSHOT_MISSING"}
    assert "group-fixture" not in json.dumps(flow, ensure_ascii=False)


def _threshold_line_payload(line) -> dict[str, object]:
    return {
        "name": line.name,
        "threshold_fen": line.threshold_fen,
        "start": line.start.isoformat(),
        "end": line.end.isoformat(),
        "days": line.days,
        "direct_observations": line.direct_observations,
        "covered_days": line.covered_days,
        "carried_forward_days": line.carried_forward_days,
        "coverage": str(line.coverage),
        "active": line.active,
        "reason": line.reason,
    }


def _t06_threshold_snapshot(
    *,
    fixed_risk_label: str = "高风险",
    dynamic: str | None = None,
    floating: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    if floating is None:
        floating = [_threshold_line_payload(line) for line in floating_month_lines(date(2026, 7, 31), ())]
    return {
        "currency": "CNY",
        "fixed": {"hard_fen": HARD_THRESHOLD_FEN, "soft_fen": SOFT_THRESHOLD_FEN},
        "floating": floating,
        "fixed_risk": fixed_risk_label,
        "dynamic_flag": dynamic,
    }


def _t06_publication() -> dict[str, object]:
    return {
        "publication_id": "a" * 64,
        "business_date": "2026-07-30",
        "status": "VALID",
        "source_versions": [{"source_version": "c" * 64}, {"source_version": "d" * 64}],
        "reconciliation_difference_fen": 0,
        "threshold_snapshot": _t06_threshold_snapshot(),
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
        "threshold_snapshot": _t06_threshold_snapshot(),
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


def test_post_deploy_observer_does_not_count_weekend_publications(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """DF-024 needs five real working dates, not five calendar dates."""

    import daily_funds.runtime as runtime_module

    runtime = DailyFundsRuntime(_config(tmp_path))
    _observer_d1(runtime_module, monkeypatch)
    monkeypatch.setenv("DAILY_FUNDS_DEPLOYMENT_MARKER", "t08-fixture-deployment")

    friday = date(2026, 8, 7)
    _write_observer_projection(runtime, friday, "a" * 64)
    assert runtime.observer(now=datetime(2026, 8, 7, 12, tzinfo=UTC))["machine_code"] == "VALID_PUBLISHED"

    saturday = date(2026, 8, 8)
    _write_observer_projection(runtime, saturday, "b" * 64)
    status = runtime.observer(now=datetime(2026, 8, 8, 12, tzinfo=UTC))
    assert status["human_status"] == "已更新"
    assert status["machine_code"] == "VALID_PUBLISHED"
    assert runtime.state.observer_days(limit=5) == []
    flow = json.loads((runtime.config.publication_dir / "flow_state.json").read_text(encoding="utf-8"))
    assert flow["post_deploy_observer"]["state"] == "WAITING_FOR_NEXT_BUSINESS_DATE"
    assert flow["post_deploy_observer"]["last_comparison"] == "NON_WORKING_DAY"
    assert flow["post_deploy_observer"]["completed_business_days"] == 0

    monday = date(2026, 8, 10)
    _write_observer_projection(runtime, monday, "c" * 64)
    assert runtime.observer(now=datetime(2026, 8, 10, 12, tzinfo=UTC))["machine_code"] == "VALID_PUBLISHED"
    assert [row["business_date"] for row in runtime.state.observer_days(limit=5)] == [monday.isoformat()]


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


def _t06_report() -> ReconciliationReport:
    return ReconciliationReport(
        date(2026, 7, 30),
        (AccountReconciliation("4" * 64, 100, 10, 3, 0, 0, 0, 107, 0, ("c" * 64, "d" * 64)),),
        100, 10, 3, 0, 107, 0, {"company": 107}, {"bank": 107}, ("c" * 64, "d" * 64),
        {"company": 0}, {"bank": 0},
    )


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
        "threshold_snapshot": _t06_threshold_snapshot(),
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


def test_r2_mirror_reuses_exact_content_addressed_objects_and_refuses_overwrite() -> None:
    class CountingStore:
        def __init__(self):
            self.values: dict[str, bytes] = {}
            self.puts: list[str] = []

        def put_bytes(self, key, payload, *, metadata=None):
            self.puts.append(key)
            self.values[key] = payload

        def get_bytes(self, key):
            return self.values[key]

    attachment = _t06_attachment()
    store = CountingStore()
    mirror = R2Mirror(store)
    mirror.mirror((attachment,), git_commit_sha="e" * 40)
    raw_key = f"daily-funds/sha256/{attachment.sha256}"
    assert store.puts.count(raw_key) == 1

    # A second poll can mint a new publication manifest, but it must not
    # charge a second write or replace bytes at the immutable raw hash key.
    mirror.mirror((attachment,), git_commit_sha="e" * 40)
    assert store.puts.count(raw_key) == 1

    store.values[raw_key] = b"different bytes"
    puts_before = len(store.puts)
    with pytest.raises(PublicationError, match="R2_READBACK_FAILED"):
        mirror.mirror((attachment,), git_commit_sha="e" * 40)
    assert len(store.puts) == puts_before
    assert store.values[raw_key] == b"different bytes"


def test_r2_s3_store_pins_standard_storage_class(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def __init__(self):
            self.puts: list[dict[str, object]] = []

        def put_object(self, **kwargs):
            self.puts.append(kwargs)

        def head_object(self, *, Bucket, Key):
            put = next(row for row in reversed(self.puts) if row["Bucket"] == Bucket and row["Key"] == Key)
            return {"ContentLength": len(put["Body"]), "Metadata": put["Metadata"]}

    class FakeConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    client = FakeClient()
    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(client=lambda *_args, **_kwargs: client))
    monkeypatch.setitem(sys.modules, "botocore.config", SimpleNamespace(Config=FakeConfig))
    digest = sha256(b"payload").hexdigest()

    r2 = S3CompatibleStore(
        endpoint_url="https://r2.invalid",
        bucket="fixture",
        access_key_id="key",
        secret_access_key="secret",
        region="auto",
        storage_class="STANDARD",
    )
    r2.put_bytes("daily-funds/sha256/fixture", b"payload", metadata={"sha256": digest})
    assert client.puts[-1]["StorageClass"] == "STANDARD"

    with pytest.raises(PublicationError, match="OBJECT_STORE_STORAGE_CLASS_INVALID"):
        S3CompatibleStore(
            endpoint_url="https://r2.invalid",
            bucket="fixture",
            access_key_id="key",
            secret_access_key="secret",
            region="auto",
            storage_class="STANDARD_IA",
        )


def test_r2_free_tier_guard_requires_standard_zero_ia_and_fresh_redacted_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)

    class Response:
        status = 200

        def __init__(self, payload):
            self.payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        def read(self):
            return self.payload

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake_urlopen(request, *, timeout):
        assert timeout == 30
        url = request.full_url
        if "/r2/buckets?per_page=1000" in url:
            return Response({
                "success": True,
                "result": {"buckets": [{"name": "fixture", "storage_class": "Standard"}]},
                "result_info": {},
            })
        if "/r2/buckets/fixture/lifecycle" in url:
            return Response({"success": True, "result": {"rules": []}})
        if url.endswith("/r2/metrics"):
            return Response({"success": True, "result": {
                "infrequentAccess": {
                    "published": {"objects": 0, "payloadSize": 0, "metadataSize": 0},
                    "uploaded": {"objects": 0, "payloadSize": 0, "metadataSize": 0},
                },
            }})
        raise AssertionError(url)

    monkeypatch.setattr("daily_funds.r2_guard.urllib.request.urlopen", fake_urlopen)
    guard = R2FreeTierGuard(config)
    receipt = guard.verify_and_write(now=datetime(2026, 8, 9, 0, tzinfo=UTC))
    assert receipt["worst_case_state"] == "UNDER_FREE_TIER_40_PERCENT"
    assert config.r2_bucket not in json.dumps(receipt, ensure_ascii=False)
    assert guard.require_fresh_receipt(now=datetime(2026, 8, 9, 6, tzinfo=UTC)) == receipt
    with pytest.raises(R2GuardError, match="R2_ZERO_CHARGE_GUARD_REQUIRED"):
        guard.require_fresh_receipt(now=datetime(2026, 8, 9, 6, 1, tzinfo=UTC))


def test_r2_free_tier_guard_rejects_any_infrequent_access_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)

    class Response:
        status = 200

        def __init__(self, payload):
            self.payload = json.dumps(payload).encode("utf-8")

        def read(self):
            return self.payload

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake_urlopen(request, *, timeout):
        url = request.full_url
        if "/r2/buckets?per_page=1000" in url:
            return Response({
                "success": True,
                "result": {"buckets": [{"name": "fixture", "storage_class": "Standard"}]},
                "result_info": {},
            })
        if "/r2/buckets/fixture/lifecycle" in url:
            return Response({"success": True, "result": {"rules": []}})
        if url.endswith("/r2/metrics"):
            return Response({"success": True, "result": {
                "infrequentAccess": {"published": {"objects": 1, "payloadSize": 1, "metadataSize": 1}},
            }})
        raise AssertionError(url)

    monkeypatch.setattr("daily_funds.r2_guard.urllib.request.urlopen", fake_urlopen)
    with pytest.raises(R2GuardError, match="R2_ZERO_CHARGE_GUARD_IA_METRICS"):
        R2FreeTierGuard(config).verify(now=datetime(2026, 8, 9, tzinfo=UTC))


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
    with pytest.raises(PublicationError, match="OBJECT_STORE_MISSING"):
        store.get_bytes("daily-funds/missing")
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
                raise PublicationError("OBJECT_STORE_MISSING") from exc

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
        "threshold_snapshot": _t06_threshold_snapshot(),
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
    assert restored.git_publication_commit_sha == publication_commit
    assert restored.oci_restore_manifest_sha == manifest_sha
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


def test_runtime_restore_keeps_verified_backup_bindings_in_new_pointer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import daily_funds.runtime as runtime_module

    runtime = DailyFundsRuntime(_config(tmp_path))
    publication = _t06_publication()
    balances, transactions, accounts = _t06_projection_rows()

    class VerifiedRestoreCoordinator:
        def __init__(self, *, d1, oci):
            self.d1 = d1
            self.oci = oci

        def restore(self, publication_id):
            assert publication_id == publication["publication_id"]
            return SimpleNamespace(
                publication=publication,
                daily_balances=balances,
                transaction_rows=transactions,
                account_rows=accounts,
                git_publication_commit_sha="b" * 40,
                oci_restore_manifest_sha="c" * 64,
            )

    monkeypatch.setattr(runtime_module, "RestoreCoordinator", VerifiedRestoreCoordinator)
    monkeypatch.setattr(runtime, "_oci_store", lambda: object())
    status = runtime.restore(publication_id="a" * 64)
    current = json.loads((runtime.config.publication_dir / "current.json").read_text(encoding="utf-8"))

    assert status["machine_code"] == "RESTORE_OK"
    assert current["runtime"]["oci_backup_state"] == "OK"
    assert current["runtime"]["git_publication_commit_sha"] == "b" * 40
    assert current["runtime"]["oci_restore_manifest_sha"] == "c" * 64


def test_runtime_restore_rejects_missing_backup_binding_without_pointer_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import daily_funds.runtime as runtime_module

    runtime = DailyFundsRuntime(_config(tmp_path))
    runtime.config.publication_dir.mkdir(parents=True, exist_ok=True)
    pointer = runtime.config.publication_dir / "current.json"
    pointer.write_text('{"old":true}\n', encoding="utf-8")
    publication = _t06_publication()
    balances, transactions, accounts = _t06_projection_rows()

    class MissingBindingRestoreCoordinator:
        def __init__(self, *, d1, oci):
            self.d1 = d1
            self.oci = oci

        def restore(self, _publication_id):
            return SimpleNamespace(
                publication=publication,
                daily_balances=balances,
                transaction_rows=transactions,
                account_rows=accounts,
                git_publication_commit_sha="",
                oci_restore_manifest_sha="",
            )

    monkeypatch.setattr(runtime_module, "RestoreCoordinator", MissingBindingRestoreCoordinator)
    monkeypatch.setattr(runtime, "_oci_store", lambda: object())
    status = runtime.restore(publication_id="a" * 64)

    assert status["machine_code"] == "RESTORE_ARTIFACT_BINDING_INVALID"
    assert pointer.read_text(encoding="utf-8") == '{"old":true}\n'


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
        (AccountReconciliation("4" * 64, 100, 10, 3, 0, 0, 0, 107, 0, ("c" * 64, "d" * 64)),),
        100, 10, 3, 0, 107, 0, {"company": 107}, {"bank": 107}, ("c" * 64, "d" * 64),
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
    balances, transactions, accounts = _t06_projection_rows()
    with pytest.raises(PublicationError) as error:
        coordinator.publish(
            report=report,
            git_commit=commit,
            attachments=(),
            daily_balances=balances,
            transaction_rows=transactions,
            account_rows=accounts,
            private_publication_sink=lambda publication: "f" * 40,
            git_bundle_sink=lambda: b"bundle",
        )
    assert error.value.code == "D1_FAILED"
    assert pointer.read_text(encoding="utf-8") == '{"old":true}\n'


def test_d1_projection_rejects_non_replayable_or_inconsistent_threshold_snapshots(tmp_path: Path) -> None:
    publication = _t06_publication()
    balances, transactions, accounts = _t06_projection_rows()
    d1 = D1Projection(_config(tmp_path))
    with pytest.raises(PublicationError, match="PUBLICATION_INVALID"):
        d1.project(
            {**publication, "threshold_snapshot": {"currency": "CNY"}},
            balances,
            transactions,
            accounts,
        )
    with pytest.raises(PublicationError, match="PROJECTION_THRESHOLD_MISMATCH"):
        d1.project(
            {**publication, "threshold_snapshot": _t06_threshold_snapshot(fixed_risk_label="正常")},
            balances,
            transactions,
            accounts,
        )


def test_d1_projection_rebuilds_floating_thresholds_from_balances_before_projecting(tmp_path: Path) -> None:
    """A shape-valid but fabricated monthly line cannot cross the D1 boundary."""

    publication = _t06_publication()
    balances, transactions, accounts = _t06_projection_rows()
    threshold = _t06_threshold_snapshot()
    forged_line = dict(threshold["floating"][0])
    forged_line.update({"active": True, "threshold_fen": 0, "reason": None})
    threshold["floating"] = [forged_line, *threshold["floating"][1:]]
    with pytest.raises(PublicationError, match="PROJECTION_THRESHOLD_MISMATCH"):
        D1Projection(_config(tmp_path)).project(
            {**publication, "threshold_snapshot": threshold},
            balances,
            transactions,
            accounts,
        )


def test_d1_projection_rejects_custom_threshold_lines_that_do_not_match_their_frozen_rule(tmp_path: Path) -> None:
    """Custom numeric/date rules are replayed instead of trusted by label."""

    publication = _t06_publication()
    balances, transactions, accounts = _t06_projection_rows()
    forged_custom_lines = (
        {
            "name": "custom_numeric", "threshold_fen": 99,
            "start": "2026-07-29", "end": "2026-07-29", "days": 1,
            "direct_observations": 1, "covered_days": 1,
            "carried_forward_days": 0, "coverage": "1",
            "active": True, "reason": None,
        },
        {
            "name": "custom_date_range", "threshold_fen": 99,
            "start": "2026-07-01", "end": "2026-07-07", "days": 7,
            "direct_observations": 7, "covered_days": 7,
            "carried_forward_days": 0, "coverage": "1",
            "active": True, "reason": None,
        },
    )
    for custom in forged_custom_lines:
        threshold = _t06_threshold_snapshot()
        threshold["floating"] = [*threshold["floating"], custom]
        with pytest.raises(PublicationError, match="PROJECTION_THRESHOLD_MISMATCH"):
            D1Projection(_config(tmp_path)).project(
                {**publication, "threshold_snapshot": threshold},
                balances,
                transactions,
                accounts,
            )


def test_d1_projection_accepts_rederived_custom_numeric_and_date_range_lines() -> None:
    """The new replay gate blocks forgery without rejecting valid owner rules."""

    class CaptureD1(D1Projection):
        def __init__(self):
            self.schema_calls = 0
            self.batches: list[tuple[tuple[str, list[object]], ...]] = []

        def ensure_schema(self) -> None:
            self.schema_calls += 1

        def _batch(self, statements):
            self.batches.append(tuple(statements))

    publication = _t06_publication()
    base_balances, transactions, accounts = _t06_projection_rows()

    numeric_threshold = _t06_threshold_snapshot()
    numeric_threshold["floating"] = [
        *numeric_threshold["floating"],
        {
            "name": "custom_numeric", "threshold_fen": 99,
            "start": "2026-07-30", "end": "2026-07-30", "days": 1,
            "direct_observations": 1, "covered_days": 1,
            "carried_forward_days": 0, "coverage": "1",
            "active": True, "reason": None,
        },
    ]
    numeric = CaptureD1()
    numeric.project(
        {**publication, "threshold_snapshot": numeric_threshold},
        base_balances,
        transactions,
        accounts,
    )
    assert numeric.schema_calls == 1 and len(numeric.batches) == 1

    start = date(2026, 7, 24)
    date_balances = tuple(DailyBalance(start + timedelta(days=index), 107, True) for index in range(7))
    date_line = custom_date_line(start, date(2026, 7, 30), date_balances)
    date_threshold = _t06_threshold_snapshot(dynamic="动态明显偏低")
    date_threshold["floating"] = [*date_threshold["floating"], _threshold_line_payload(date_line)]
    date_range = CaptureD1()
    date_range.project(
        {**publication, "threshold_snapshot": date_threshold},
        date_balances,
        transactions,
        accounts,
    )
    assert date_range.schema_calls == 1 and len(date_range.batches) == 1


def test_publication_rejects_report_projection_mismatch_before_any_pointer_swap(tmp_path: Path) -> None:
    class D1MustNotRun:
        def project(self, *args, **kwargs):
            raise AssertionError("candidate validation must run before D1")

    publication_dir = tmp_path / "publication"
    publication_dir.mkdir()
    pointer = publication_dir / "current.json"
    pointer.write_text('{"old":true}\n', encoding="utf-8")
    balances, transactions, accounts = _t06_projection_rows()
    report = replace(_t06_report(), by_company_ending_fen={"company": 106})
    coordinator = PublicationCoordinator(
        publication_dir=publication_dir,
        status=StatusWriter(publication_dir),
        d1=D1MustNotRun(),
        r2=_R2Okay(),
        oci=_OciUnused(),
    )
    commit = GitCommit("e" * 40, StagedRawBatch("a" * 64, (), (), 0, ()), b"bundle")
    with pytest.raises(PublicationError, match="PROJECTION_REPORT_MISMATCH"):
        coordinator.publish(
            report=report,
            git_commit=commit,
            attachments=(),
            daily_balances=balances,
            transaction_rows=transactions,
            account_rows=accounts,
            private_publication_sink=lambda publication: "f" * 40,
            git_bundle_sink=lambda: b"bundle",
        )
    assert pointer.read_text(encoding="utf-8") == '{"old":true}\n'


def test_one_fen_difference_cannot_replace_existing_pointer(tmp_path: Path) -> None:
    """F-014: any non-zero integer-fen difference blocks the pointer swap."""

    publication_dir = tmp_path / "publication"
    publication_dir.mkdir()
    pointer = publication_dir / "current.json"
    pointer.write_text('{"old":true}\n', encoding="utf-8")
    balances, transactions, accounts = _t06_projection_rows()
    coordinator = PublicationCoordinator(
        publication_dir=publication_dir,
        status=StatusWriter(publication_dir),
        d1=object(),
        r2=object(),
        oci=object(),
    )
    commit = GitCommit("e" * 40, StagedRawBatch("a" * 64, (), (), 0, ()), b"bundle")

    with pytest.raises(PublicationError, match="RECONCILIATION_FAILED"):
        coordinator.publish(
            report=replace(_t06_report(), difference_fen=1),
            git_commit=commit,
            attachments=(),
            daily_balances=balances,
            transaction_rows=transactions,
            account_rows=accounts,
            private_publication_sink=lambda _publication: pytest.fail("must not write private publication"),
            git_bundle_sink=lambda: pytest.fail("must not create recovery bundle"),
        )
    assert pointer.read_text(encoding="utf-8") == '{"old":true}\n'


def test_git_publication_and_bundle_failures_retain_prior_pointer(tmp_path: Path) -> None:
    class D1Okay:
        def project(self, publication, balances, transactions, accounts):
            self.publication = publication

        def oracle(self, publication_id):
            return {"publication_id": publication_id}

    class OciMustNotRun:
        def __init__(self):
            self.calls = 0

        def backup(self, **kwargs):
            self.calls += 1
            raise AssertionError("invalid Git stages must fail before OCI")

    publication_dir = tmp_path / "publication"
    publication_dir.mkdir()
    pointer = publication_dir / "current.json"
    pointer.write_text('{"old":true}\n', encoding="utf-8")
    balances, transactions, accounts = _t06_projection_rows()
    commit = GitCommit("e" * 40, StagedRawBatch("a" * 64, (), (), 0, ()), b"bundle")

    def coordinator(oci):
        return PublicationCoordinator(
            publication_dir=publication_dir,
            status=StatusWriter(publication_dir),
            d1=D1Okay(),
            r2=_R2Okay(),
            oci=oci,
        )

    write_failure_oci = OciMustNotRun()
    with pytest.raises(PublicationError, match="GIT_WRITE_FAILED"):
        coordinator(write_failure_oci).publish(
            report=_t06_report(),
            git_commit=commit,
            attachments=(),
            daily_balances=balances,
            transaction_rows=transactions,
            account_rows=accounts,
            private_publication_sink=lambda publication: (_ for _ in ()).throw(RuntimeError("fixture")),
            git_bundle_sink=lambda: b"bundle",
        )
    assert write_failure_oci.calls == 0
    assert pointer.read_text(encoding="utf-8") == '{"old":true}\n'

    empty_bundle_oci = OciMustNotRun()
    with pytest.raises(PublicationError, match="GIT_BUNDLE_EMPTY"):
        coordinator(empty_bundle_oci).publish(
            report=_t06_report(),
            git_commit=commit,
            attachments=(),
            daily_balances=balances,
            transaction_rows=transactions,
            account_rows=accounts,
            private_publication_sink=lambda publication: "f" * 40,
            git_bundle_sink=lambda: b"",
        )
    assert empty_bundle_oci.calls == 0
    assert pointer.read_text(encoding="utf-8") == '{"old":true}\n'

    invalid_bundle_oci = OciMustNotRun()
    with pytest.raises(PublicationError, match="GIT_BUNDLE_INVALID"):
        coordinator(invalid_bundle_oci).publish(
            report=_t06_report(),
            git_commit=commit,
            attachments=(),
            daily_balances=balances,
            transaction_rows=transactions,
            account_rows=accounts,
            private_publication_sink=lambda publication: "f" * 40,
            git_bundle_sink=lambda: b"not-a-git-bundle",
        )
    assert invalid_bundle_oci.calls == 0
    assert pointer.read_text(encoding="utf-8") == '{"old":true}\n'


def test_r2_failure_and_oci_lag_have_distinct_pointer_semantics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    verified_bundles: list[tuple[bytes, str, str]] = []

    def verify_bundle(bundle, *, expected_raw_commit_sha, expected_publication_commit_sha, publication):
        verified_bundles.append((bundle, expected_raw_commit_sha, expected_publication_commit_sha))
        assert publication["status"] == "VALID"

    monkeypatch.setattr(
        RestoreOracle,
        "verify_private_publication_bundle",
        staticmethod(verify_bundle),
    )
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
    assert verified_bundles == [(b"bundle", "e" * 40, "f" * 40)]
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
    # A stale legacy AppSecret is never read from GitHub Secrets or re-created.
    # Coolify PATCH updates existing keys but returns 404 for a missing key;
    # this workflow only falls back to POST for that documented case and never
    # needs DELETE permission. Compose does not declare this legacy key, so it
    # cannot reach the worker.
    assert "DAILY_FUNDS_DWS_CLIENT_SECRET: ${{ secrets." not in ops
    assert "每日资金 13 个必填 secret 已通过 Coolify PATCH/POST 覆盖生产运行上下文" in ops
    assert 'DAILY_FUNDS_SENDER_IDS: "${DAILY_FUNDS_SENDER_IDS:-}"' in daily_service
    assert "DAILY_FUNDS_SENDER_IDS=" in env_example
    assert "DAILY_FUNDS_SENDER_IDS: ${{ secrets.DAILY_FUNDS_SENDER_IDS }}" in ops
    assert '"$BASE/api/v1/applications/$APP/envs" || true)' in ops
    sync_block = ops.split("- name: 同步每日资金专用 secrets", 1)[1].split("      - name:", 1)[0]
    assert '[ "$code" = "404" ]' in sync_block
    assert '"$RUNNER_TEMP/daily-funds-post.out"' in sync_block
    assert '"$RUNNER_TEMP/daily-funds-patch-retry.out"' in sync_block
    assert '[ "$code" = "409" ]' in sync_block
    assert 'not bool(item.get("is_preview", False))' in sync_block
    assert "生产运行上下文不是恰好一条" in sync_block
    assert "DAILY_FUNDS_OCI_PAR_URL" in ops
    assert "optional_keys=(DAILY_FUNDS_DWS_CLIENT_ID DAILY_FUNDS_DWS_AUTH_BUNDLE_B64)" in ops
    assert "留空时使用 DWS 官方默认客户端" in env_example
    assert "DAILY_FUNDS_R2_MAX_NEW_OBJECTS_PER_POLL=100" in env_example
    assert 'DAILY_FUNDS_R2_MAX_NEW_OBJECTS_PER_POLL: "${DAILY_FUNDS_R2_MAX_NEW_OBJECTS_PER_POLL:-100}"' in daily_service
    assert 'SOURCE_COMMIT: "${SOURCE_COMMIT:-}"' in daily_service
    assert "enable-source-commit-build" in ops
    assert 'include_source_commit_in_build": True' in ops
    assert "source_commit_build_setting=ENABLED" in ops
    assert "source_commit_build_setting=UNKNOWN" in ops
    assert "source_commit_build_error_fields=INCLUDE_SOURCE_COMMIT_FIELD" in ops
    assert "MAIN_REF_REQUIRED" in ops
    assert 'user: "0:0"' in daily_service
    assert "kmfa-dws-auth" not in daily_service
    assert "sync-daily-funds-secrets" in ops
    assert "|^DAILY_FUNDS_" in ops
    entrypoint = (ROOT / "entrypoint.sh").read_text(encoding="utf-8")
    assert "chmod 0700" in entrypoint
    assert 'chmod 0770 "$CONTROL_DIR"' in entrypoint
    assert "DAILY_FUNDS_DWS_KEYRING_DIR" in entrypoint
    assert "DAILY_FUNDS_RUNTIME_PATH_INVALID" in entrypoint
    assert "runtime-audit" in entrypoint
    runner = (ROOT / "scripts/run_daily_funds.py").read_text(encoding="utf-8")
    crontab = (ROOT / "crontab.txt").read_text(encoding="utf-8")
    assert "bootstrap-dws-auth" in runner
    assert "r2-guard" in runner
    assert "root /opt/daily-funds/scripts/run_daily_funds.py bootstrap-dws-auth" not in crontab
