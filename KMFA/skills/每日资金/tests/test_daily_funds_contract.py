from __future__ import annotations

import base64
import json
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from daily_funds.config import DailyFundsConfig
from daily_funds.control import ThresholdControl
from daily_funds.contracts import (
    DailyBalance,
    HARD_THRESHOLD_FEN,
    HUMAN_STATUSES,
    SOFT_THRESHOLD_FEN,
    complete_calendar_month_window,
    fixed_risk,
    floating_month_lines,
    parse_amount_to_fen,
    custom_date_line,
)
from daily_funds.ingestion import (
    CHUNK_BYTES,
    DIRECT_BLOB_MAX_BYTES,
    DownloadedAttachment,
    DwsHistoryClient,
    HistoryPoller,
    IngestionError,
    RawMaterializer,
)
from daily_funds.models import SourceRef
from daily_funds.parsing import ACCOUNT_FAMILY, parse_attachment
from daily_funds.publication import D1Projection, OciColdBackup, PublicationCoordinator, PublicationError, RestoreCoordinator, RestoreOracle
from daily_funds.reconcile import AccountReconciliation, ReconciliationReport, reconcile
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
        "DAILY_FUNDS_DWS_CLIENT_SECRET": "secret-fixture",
        "DAILY_FUNDS_GIT_SSH_KEY_B64": pem,
        "DAILY_FUNDS_CLOUDFLARE_API_TOKEN": "cf-fixture",
        "DAILY_FUNDS_CF_ACCOUNT_ID": "account-fixture",
        "DAILY_FUNDS_D1_DATABASE_ID": "d1-fixture",
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


def _source(version: str) -> SourceRef:
    return SourceRef(version, "m" * 64, "Private-KMDatabase/KMFA/daily_funds/raw/occurrences/x.json", version)


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
        "revision": "r" * 64,
        "actor": "kmfa_private_owner_ui",
        "reason": "fixture evidence",
    }), encoding="utf-8")
    active = control.apply_pending()
    assert active and active["amount_fen"] == 90_000_000
    audit = json.loads(control.audit_path.read_text(encoding="utf-8").strip())
    assert audit["actor"] == "kmfa_private_owner_ui"
    assert audit["reason"] == "fixture evidence"
    assert set(("old_value", "new_value", "changed_at", "rollback_version")) <= set(audit)


def test_monthly_restore_drill_rejects_missing_or_live_d1_target(tmp_path: Path) -> None:
    config = _config(tmp_path)
    runtime = DailyFundsRuntime(config)
    assert runtime.restore_drill()["machine_code"] == "RESTORE_DRILL_CONFIG_INVALID"
    from dataclasses import replace
    assert DailyFundsRuntime(replace(config, restore_drill_d1_database_id=config.d1_database_id)).restore_drill()["machine_code"] == "RESTORE_DRILL_CONFIG_INVALID"


def test_two_fact_families_never_merge_and_reconcile_to_zero() -> None:
    accounts = parse_attachment(
        family=ACCOUNT_FAMILY,
        filename="资金账户明细表_20260730.csv",
        payload=(
            "业务日期,公司,开户行,账号,期初余额,期末余额,币种\n"
            "2026-07-30,甲公司,甲银行,001,1500000.00,1570000.00,CNY\n"
        ).encode(),
        source=_source("a" * 64),
    )
    transactions = parse_attachment(
        family="资金流水明细",
        filename="资金流水明细_20260730.csv",
        payload=(
            "业务日期,公司,开户行,账号,流水号,流入,流出\n"
            "2026-07-30,甲公司,甲银行,001,in,250000.00,\n"
            "2026-07-30,甲公司,甲银行,001,out,,180000.00\n"
        ).encode(),
        source=_source("b" * 64),
    )
    assert accounts.accounts and not accounts.transactions
    assert transactions.transactions and not transactions.accounts
    report = reconcile((accounts, transactions))
    assert report.valid
    assert report.difference_fen == 0


def test_page_two_failure_never_advances_cursor(tmp_path: Path) -> None:
    config = _config(tmp_path)
    state = RuntimeState(config.state_dir)
    state.commit_cursor("old")
    responses = [
        {"hasMore": True, "nextCursor": "page-2", "messages": []},
        {"hasMore": False, "messages": []},
    ]

    def runner(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, json.dumps(responses.pop(0)), "")

    client = DwsHistoryClient(config, runner=runner)
    poller = HistoryPoller(state, client)
    calls = 0

    def persist(_page):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise IngestionError("PAGE_TWO_INJECTED_FAILURE")

    with pytest.raises(IngestionError):
        poller.poll(now=datetime(2026, 8, 1, tzinfo=UTC), persist_page=persist, holder="fixture")
    assert state.get_cursor() == "old"
    assert state.get("history_high_water_at") is None


def test_cloud_scheduler_uses_the_bundled_entrypoint_and_frozen_cadence() -> None:
    """Prevent a container that looks healthy while every cron row exits 127."""

    command = "/opt/daily-funds/scripts/run_daily_funds.py"
    cron = (ROOT / "crontab.txt").read_text(encoding="utf-8")
    assert f"*/15 * * * * root {command} poll" in cron
    assert f"* * * * * root {command} auth-probe" in cron
    assert f"0 * * * * root {command} keepalive" in cron
    assert f"15 2 * * * root {command} backfill --max-days 7" in cron
    assert f"30 3 * * * root {command} observer" in cron
    assert f"10 4 * * * root {command} cold-backup" in cron
    assert f"0 5 1 * * root {command} restore-drill" in cron
    assert command in (ROOT / "entrypoint.sh").read_text(encoding="utf-8")
    assert command in (ROOT / "healthcheck.sh").read_text(encoding="utf-8")


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
    # The 30-minute overlap must produce neither a collision nor a fresh
    # batch/object version for the same source occurrence.
    repeated = RawMaterializer().stage(tmp_path, (direct, oversized))
    assert repeated.batch_id == staged.batch_id


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
    assert env["XDG_DATA_HOME"] == str(config.dws_keyring_dir)


def test_source_gate_rejects_multiple_candidate_documents() -> None:
    accounts = parse_attachment(
        family=ACCOUNT_FAMILY,
        filename="资金账户明细表_20260730.csv",
        payload=("业务日期,公司,开户行,账号,期初余额,期末余额\n2026-07-30,甲,乙,001,1.00,1.00\n").encode(),
        source=_source("a" * 64),
    )
    transactions = parse_attachment(
        family="资金流水明细",
        filename="资金流水明细_20260730.csv",
        payload=("业务日期,公司,开户行,账号,流水号,流入,流出\n2026-07-30,甲,乙,001,t,,\n").encode(),
        source=_source("b" * 64),
    )
    moment = datetime(2026, 7, 30, tzinfo=UTC)
    assert DailyFundsRuntime._latest_complete_pair((TimedFacts(accounts, moment), TimedFacts(transactions, moment)))
    duplicate_accounts = parse_attachment(
        family=ACCOUNT_FAMILY,
        filename="资金账户明细表_20260730_v2.csv",
        payload=("业务日期,公司,开户行,账号,期初余额,期末余额\n2026-07-30,甲,乙,001,1.00,1.00\n").encode(),
        source=_source("c" * 64),
    )
    with pytest.raises(Exception, match="SOURCE_MATCH_MULTIPLE"):
        DailyFundsRuntime._latest_complete_pair((
            TimedFacts(accounts, moment), TimedFacts(duplicate_accounts, moment), TimedFacts(transactions, moment),
        ))


def test_d1_batch_uses_cloudflare_batch_envelope(tmp_path: Path) -> None:
    class CaptureD1(D1Projection):
        def __init__(self):
            self.payload = None

        def _request(self, payload):
            self.payload = payload
            return {"success": True, "result": [{"success": True}]}

    d1 = CaptureD1()
    d1._batch((("SELECT ?", ["fixture"]),))
    assert d1.payload == {"batch": [{"sql": "SELECT ?", "params": ["fixture"]}]}


def test_d1_query_oracle_requires_both_fact_families_and_matching_ending() -> None:
    publication_id = "p" * 64
    payload_json = json.dumps({"publication_id": publication_id, "business_date": "2026-07-30"})

    class OracleD1(D1Projection):
        def __init__(self, check):
            self.check = check

        def _query(self, sql, params=None):
            if "FROM daily_funds_publications" in sql:
                return [{
                    "publication_id": publication_id,
                    "reconciliation_difference_fen": 0,
                    "status": "VALID",
                    "payload_json": payload_json,
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
            assert publication_id == "p" * 64
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
    bundle_path = tmp_path / "daily-funds.bundle"
    git("bundle", "create", str(bundle_path), "HEAD")

    publication = {
        "publication_id": "p" * 64,
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
    r2_inventory = b'{"schema_version":"kmfa.daily_funds.r2_manifest.v1"}\n'
    publication["r2_manifest_sha256"] = __import__("hashlib").sha256(r2_inventory).hexdigest()
    publication_bytes = (json.dumps(publication, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    d1_export = json.dumps({
        "publication": {"payload_json": publication_bytes.decode()},
        "daily_balances": [{"business_date": "2026-07-30", "ending_available_fen": 107, "direct_observation": 1, "coverage_gap": 0, "carried_forward": 0}],
        "transactions": [{"transaction_key_hash": "t" * 64, "business_date": "2026-07-30", "inflow_fen": 10, "outflow_fen": 3, "adjustment_fen": 0, "internal_transfer": 0, "source_version": "b" * 64, "message_id_hash": "m" * 64}],
        "account_snapshots": [{"account_key_hash": "h" * 64, "business_date": "2026-07-30", "company_id": "company", "bank_id": "bank", "account_alias": "h" * 64, "opening_available_fen": 100, "ending_available_fen": 107, "source_version": "a" * 64, "message_id_hash": "m" * 64}],
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    store = MemoryStore()
    backup = OciColdBackup(store)
    backup.backup(
        publication_id="p" * 64,
        publication_sha256=__import__("hashlib").sha256(publication_bytes).hexdigest(),
        git_bundle=bundle_path.read_bytes(),
        d1_export=d1_export,
        r2_inventory=r2_inventory,
    )
    d1 = RestorableD1()
    restored = RestoreCoordinator(d1=d1, oci=backup).restore("p" * 64)
    assert restored.publication["publication_id"] == "p" * 64
    assert len(d1.calls) == 1
    assert d1.calls[0][1][0].ending_available_fen == 107


def test_restore_rejects_non_git_bundle() -> None:
    with pytest.raises(PublicationError, match="RESTORE_GIT_BUNDLE_INVALID"):
        RestoreOracle.verify_git_bundle(b"not-a-git-bundle", expected_commit_sha="c" * 40)


class _R2Okay:
    def mirror(self, attachments, *, git_commit_sha):
        return "r" * 64, b"r2-inventory"


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
        )
    assert error.value.code == "D1_FAILED"
    assert pointer.read_text(encoding="utf-8") == '{"old":true}\n'


def test_three_statuses_and_no_old_threshold_constants() -> None:
    assert HUMAN_STATUSES == {"已更新", "处理中", "需处理"}
    source = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "daily_funds").rglob("*.py"))
    assert "50_000_000" not in source
    assert "100_000_000" not in source
    assert "KMFA_DINGTALK_ATTENDANCE" not in source
    assert "kmfa-dws-auth" not in source
